#!/usr/bin/env python3
"""Build near-boundary release-value and audit-contamination tables.

This script is intentionally table-only.  It does not mutate any candidate
universe or rerun expensive proposal generation; it recomputes the release
diagnostics from frozen public-safe candidate tables when available and writes
paper-facing closeout tables under the release-story milestone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_materials_discovery_parc_flagship as materials  # noqa: E402


DEFAULT_SEEDS = list(range(20))
EPSILONS = [0.0, 0.01, 0.03, 0.05, 0.10]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def parse_list(value: str, cast):
    return [cast(item) for item in value.split(",") if item.strip()]


def split_video_ids(video_ids: list[int], seed: int, tune_ratio: float, cal_ratio: float) -> dict[int, str]:
    ordered = sorted(set(int(video_id) for video_id in video_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    tune_end = int(round(len(ordered) * tune_ratio))
    cal_end = tune_end + int(round(len(ordered) * cal_ratio))
    mapping: dict[int, str] = {}
    for idx, video_id in enumerate(ordered):
        if idx < tune_end:
            mapping[video_id] = "tune"
        elif idx < cal_end:
            mapping[video_id] = "cal"
        else:
            mapping[video_id] = "test"
    return mapping


def gamma_star_from_p(p_value: float | None) -> float | None:
    if p_value is None or p_value <= 0.0 or p_value >= 1.0:
        return None
    gamma = -1.0 / math.log(p_value)
    return gamma if 0.0 < gamma < 1.0 else None


def emax_from_p(gamma: float | None, p_value: float | None) -> float | None:
    if gamma is None or p_value is None or p_value <= 0.0 or p_value > 1.0:
        return None
    return gamma * (p_value ** (gamma - 1.0))


def scs_release_count(evalues: np.ndarray, alpha: float, budget: int) -> tuple[int, float, float, float]:
    if len(evalues) == 0:
        return 0, math.inf, -math.inf, 0.0
    sorted_e = np.sort(evalues.astype(float))[::-1]
    released = 0
    best_tau = math.inf
    best_margin = -math.inf
    best_ratio = 0.0
    for k, evalue in enumerate(sorted_e, start=1):
        tau = budget / (alpha * k)
        margin = float(evalue - tau)
        ratio = float(alpha * k * evalue / budget)
        best_ratio = max(best_ratio, ratio)
        if margin > best_margin:
            best_margin = margin
            best_tau = tau
        if evalue >= tau:
            released = k
    if released:
        tau = budget / (alpha * released)
        return released, tau, float(sorted_e[released - 1] - tau), best_ratio
    return 0, best_tau, best_margin, best_ratio


def bootstrap_ci(values: np.ndarray, seed: int = 20260515, n_boot: int = 5000) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    boot = [float(values[rng.integers(0, len(values), len(values))].mean()) for _ in range(n_boot)]
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def summarize(values: list[float]) -> tuple[float, float, float]:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return math.nan, math.nan, math.nan
    lo, hi = bootstrap_ci(arr)
    return float(arr.mean()), lo, hi


def e_bh_full_pool(evalues: np.ndarray, alpha: float) -> int:
    """e-BH-style selection over the full test pool, not the fixed-K budget.

    This is deliberately included as a scalar-filter baseline: unlike PARC's
    fixed-budget SCS release, it is not allowed to use the requested release
    budget as a compatibility constraint.
    """
    if len(evalues) == 0:
        return 0
    sorted_e = np.sort(evalues.astype(float))[::-1]
    n = len(sorted_e)
    released = 0
    for k, evalue in enumerate(sorted_e, start=1):
        if evalue >= n / (alpha * k):
            released = k
    return released


def materials_seed_records(args: argparse.Namespace, conditions: list[tuple[float, float, int]]) -> pd.DataFrame:
    frame, _meta = materials.load_materials_inputs(args)
    rows: list[dict] = []
    for rho, alpha, budget in conditions:
        for seed in DEFAULT_SEEDS:
            observed = materials.observed_positive_mask(
                frame, "primary_score", rho=rho, seed=seed, strategy="top_score"
            )
            cal_blocks, test_blocks = materials.split_blocks(
                frame["composition_family_pair"].astype(str).tolist(), seed
            )
            test, diag = materials.compute_evalues(
                frame,
                score_col="primary_score",
                block_col="composition_family_pair",
                observed_positive=observed,
                cal_blocks=cal_blocks,
                test_blocks=test_blocks,
                alpha=alpha,
            )
            test = test.sort_values("primary_score", ascending=False).copy()
            pool = test.head(budget).copy()
            evalues = pool["_evalue"].to_numpy(dtype=float)
            released, _tau, margin, best_ratio = materials.scs_release_count(
                evalues, alpha=alpha, budget=budget
            )
            selected = pool.iloc[np.argsort(evalues)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
            raw_top_r = pool.head(released).copy() if released else pool.iloc[[]].copy()

            observed_scores = frame.loc[observed, "primary_score"].astype(float)
            if len(observed_scores):
                split_threshold = float(np.quantile(observed_scores, alpha))
                split_selected = pool[pool["primary_score"].astype(float) >= split_threshold].copy()
            else:
                split_threshold = math.nan
                split_selected = pool.iloc[[]].copy()

            post_filter_selected = pool[pool["_evalue"].astype(float) >= (1.0 / alpha)].copy()
            full_ebh_k = e_bh_full_pool(test["_evalue"].to_numpy(dtype=float), alpha=alpha)
            full_ebh_selected = test.iloc[np.argsort(test["_evalue"].to_numpy(dtype=float))[::-1][:full_ebh_k]].copy()

            def ftr(df: pd.DataFrame) -> float:
                return float((~df["stable_DFT"].astype(bool)).mean()) if len(df) else math.nan

            rows.append(
                {
                    "domain": "Materials discovery",
                    "dataset": "Matbench Discovery WBM unique prototypes",
                    "proposal_source": "CGCNN ensemble learned materials model",
                    "rho": rho,
                    "alpha": alpha,
                    "K": budget,
                    "seed": seed,
                    "raw_topK_FTR": ftr(pool),
                    "raw_topR_FTR": ftr(raw_top_r),
                    "raw_topR_release_size": int(len(raw_top_r)),
                    "split_conformal_release_size": int(len(split_selected)),
                    "split_conformal_FTR": ftr(split_selected),
                    "split_conformal_threshold": split_threshold,
                    "post_filter_e_threshold_release_size": int(len(post_filter_selected)),
                    "post_filter_e_threshold_FTR": ftr(post_filter_selected),
                    "e_BH_full_pool_release_size": int(len(full_ebh_selected)),
                    "e_BH_full_pool_FTR": ftr(full_ebh_selected),
                    "PARC_release_size": int(released),
                    "PARC_FTR": ftr(selected) if released else 0.0,
                    "best_mass_ratio": best_ratio,
                    "self_consistency_margin": margin,
                    "required_e": float(diag["required_emax"]),
                    "max_observed_e": float(pool["_evalue"].max()) if len(pool) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def build_near_boundary_tables(args: argparse.Namespace, out_dir: Path) -> tuple[Path, Path]:
    conditions = [
        (0.05, 0.05, 300),
        (0.10, 0.10, 300),
        (0.10, 0.10, 500),
    ]
    seed_rows = materials_seed_records(args, conditions)
    seed_path = out_dir / "table_near_boundary_release_value_seed_rows.csv"
    seed_rows.to_csv(seed_path, index=False)

    rows = []
    for (domain, dataset, source, rho, alpha, budget), group in seed_rows.groupby(
        ["domain", "dataset", "proposal_source", "rho", "alpha", "K"], dropna=False
    ):
        row = {
            "domain": domain,
            "dataset": dataset,
            "proposal_source": source,
            "rho": rho,
            "K": budget,
            "alpha": alpha,
            "seeds": int(group["seed"].nunique()),
            "PARC_non_empty_seeds": int((group["PARC_release_size"].astype(int) > 0).sum()),
            "near_boundary_status": "qualifies_nonrandom_near_boundary",
        }
        for col in [
            "raw_topK_FTR",
            "raw_topR_FTR",
            "split_conformal_FTR",
            "post_filter_e_threshold_FTR",
            "e_BH_full_pool_FTR",
            "PARC_FTR",
            "PARC_release_size",
            "split_conformal_release_size",
            "post_filter_e_threshold_release_size",
            "e_BH_full_pool_release_size",
            "best_mass_ratio",
        ]:
            values = group[col].dropna().astype(float).tolist()
            mean, lo, hi = summarize(values)
            row[col] = mean
            row[f"{col}_bootstrap95_low"] = lo
            row[f"{col}_bootstrap95_high"] = hi
        row["practice_benefit_claim"] = (
            "raw_topK_is_near_boundary_or_unsafe_and_PARC_releases_a_smaller_lower_FTR_subset"
        )
        row["paper_use"] = "main_near_boundary_practice_benefit"
        rows.append(row)

    table = pd.DataFrame(rows)

    # Domain-screening rows are intentionally explicit: CTC learned and SpaceNet
    # geometry are useful positive/release-check rows elsewhere, but their raw
    # non-random top slices are too clean to support this particular near-boundary
    # claim.  This prevents silently promoting a random-linker strawman.
    ctc = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_strict_alpha010_smallK.csv")
    ctc_row = ctc[(ctc["alpha"] == 0.10) & (ctc["M"] == 300)].iloc[0]
    spacenet = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_spacenet7/table_spacenet7_geometry_main_alpha020.csv")
    sn_row = spacenet[(spacenet["alpha"] == 0.20) & (spacenet["rho"] == 0.10) & (spacenet["M"] == 100)].iloc[0]
    screen_rows = [
        {
            "domain": "Biomedical cell tracking",
            "dataset": "Cell Tracking Challenge 2D held-out sequence",
            "proposal_source": "learned-hybrid appearance linker",
            "rho": 0.10,
            "K": int(ctc_row["M"]),
            "alpha": float(ctc_row["alpha"]),
            "seeds": int(ctc_row["seeds"]),
            "PARC_non_empty_seeds": int(ctc_row["nonempty_seeds"]),
            "raw_topK_FTR": float(ctc_row["raw_topM_actual_FTR_mean"]),
            "PARC_release_size": float(ctc_row["released_mean"]),
            "PARC_FTR": float(ctc_row["actual_FTR_mean"]),
            "near_boundary_status": "not_near_boundary_clean_raw_slice",
            "practice_benefit_claim": "strict learned-source positive; not used for near-boundary raw-risk claim",
            "paper_use": "domain_screening_not_table2_main",
        },
        {
            "domain": "Earth observation",
            "dataset": "SpaceNet 7 building links",
            "proposal_source": "geometry building-link source",
            "rho": float(sn_row["rho"]),
            "K": int(sn_row["M"]),
            "alpha": float(sn_row["alpha"]),
            "seeds": int(sn_row["seeds"]),
            "PARC_non_empty_seeds": int(sn_row["nonempty_seeds"]),
            "raw_topK_FTR": float(sn_row["raw_topM_actual_FTR"]),
            "PARC_release_size": float(sn_row["released_mean"]),
            "PARC_FTR": float(sn_row["actual_FTR_mean"]),
            "near_boundary_status": "not_near_boundary_clean_raw_slice",
            "practice_benefit_claim": "release/refusal workflow evidence; raw non-random top slice is already clean",
            "paper_use": "domain_screening_not_table2_main",
        },
    ]
    domain_screening = pd.concat([table, pd.DataFrame(screen_rows)], ignore_index=True, sort=False)
    table_path = out_dir / "table_near_boundary_release_value.csv"
    screening_path = out_dir / "table_near_boundary_domain_screening.csv"
    table.to_csv(table_path, index=False)
    domain_screening.to_csv(screening_path, index=False)
    return table_path, screening_path


def observed_true_with_contamination(
    full_true: pd.Series,
    scores: pd.Series,
    rho: float,
    seed: int,
    epsilon: float,
    contam_eligible_false_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, int, int]:
    true_indices = np.flatnonzero(full_true.to_numpy(dtype=bool))
    if contam_eligible_false_mask is None:
        false_indices = np.flatnonzero(~full_true.to_numpy(dtype=bool))
    else:
        false_indices = np.flatnonzero((~full_true.to_numpy(dtype=bool)) & contam_eligible_false_mask)
    observed = np.zeros(len(full_true), dtype=bool)
    if len(true_indices) == 0:
        return observed, 0, 0
    score_values = scores.to_numpy(dtype=float)
    n_true_observed = int(round(len(true_indices) * rho))
    true_order = true_indices[np.argsort(score_values[true_indices])[::-1]]
    chosen_true = true_order[:n_true_observed]
    observed[chosen_true] = True
    n_false_contam = int(round(epsilon * max(1, len(chosen_true))))
    if n_false_contam > 0 and len(false_indices) > 0:
        false_order = false_indices[np.argsort(score_values[false_indices])[::-1]]
        chosen_false = false_order[: min(n_false_contam, len(false_order))]
        observed[chosen_false] = True
        n_false_contam = len(chosen_false)
    else:
        n_false_contam = 0
    return observed, len(chosen_true), n_false_contam


def compute_ctc_evalues(test: pd.DataFrame, cal: pd.DataFrame, cal_video_ids: list[int], alpha: float) -> tuple[np.ndarray, dict]:
    null_cal = cal[cal["_partial_null"].astype(bool)].copy()
    if null_cal.empty:
        maxima = np.asarray([], dtype=float)
    else:
        maxima = null_cal.groupby("video_id")["score"].max().astype(float).to_numpy()
    n_nonempty = int(len(maxima))
    p_min = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    required = 1.0 / alpha if alpha > 0 else None
    diag = {
        "n_cal_blocks": len(cal_video_ids),
        "n_nonempty_null_cal_blocks": n_nonempty,
        "n_empty_cal_blocks": max(0, len(cal_video_ids) - n_nonempty),
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_emax": required,
        "block_coverage": n_nonempty / len(cal_video_ids) if cal_video_ids else 0.0,
    }
    if gamma is None or len(test) == 0 or len(maxima) == 0:
        return np.zeros(len(test), dtype=float), diag
    maxima_sorted = np.sort(maxima)
    scores = test["score"].astype(float).to_numpy()
    exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
    p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
    evalues = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return evalues.astype(float), diag


def ctc_contamination_rows(args: argparse.Namespace) -> pd.DataFrame:
    universe = pd.read_csv(args.ctc_learned_universe)
    universe["video_id"] = universe["video_id"].astype(int)
    universe["_full_false"] = bool_series(universe["is_unmatched"])
    universe["_full_true"] = ~universe["_full_false"]
    universe = universe.sort_values(["candidate_rank", "score"], ascending=[True, False]).reset_index(drop=True)

    rows: list[dict] = []
    for epsilon in EPSILONS:
        for seed in DEFAULT_SEEDS:
            split_map = split_video_ids(
                universe["video_id"].tolist(),
                seed=seed,
                tune_ratio=args.ctc_tune_ratio,
                cal_ratio=args.ctc_cal_ratio,
            )
            split_series = universe["video_id"].map(split_map)
            cal_eligible_false = (split_series == "cal").to_numpy(dtype=bool)
            observed, n_true_observed, n_false_contam = observed_true_with_contamination(
                universe["_full_true"],
                universe["score"],
                rho=args.ctc_rho,
                seed=seed,
                epsilon=epsilon,
                contam_eligible_false_mask=cal_eligible_false,
            )
            work = universe.copy()
            work["_observed_positive"] = observed
            work["_partial_null"] = ~work["_observed_positive"]
            work["_split"] = work["video_id"].map(split_map)
            cal = work[work["_split"] == "cal"].copy()
            test = work[work["_split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
            cal_video_ids = sorted(cal["video_id"].unique().tolist())
            for alpha in args.ctc_alphas:
                evalues, diag = compute_ctc_evalues(test, cal, cal_video_ids, alpha=alpha)
                test = test.copy()
                test["_evalue"] = evalues
                for budget in args.ctc_budgets:
                    pool = test.head(budget).copy()
                    pool_e = pool["_evalue"].to_numpy(dtype=float)
                    released, _tau, margin, best_ratio = scs_release_count(pool_e, alpha=alpha, budget=budget)
                    selected = pool.iloc[np.argsort(pool_e)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
                    actual_ftr = float(selected["_full_false"].mean()) if released else 0.0
                    rows.append(
                        {
                            "domain": "Biomedical cell tracking",
                            "dataset": args.ctc_contamination_dataset_label,
                            "proposal_source": args.ctc_contamination_source_label,
                            "rho": args.ctc_rho,
                            "epsilon_false_verified_positive": epsilon,
                            "alpha": alpha,
                            "K": budget,
                            "seed": seed,
                            "observed_true_positives": n_true_observed,
                            "false_links_injected_as_verified_positive": n_false_contam,
                            "realized_verified_positive_contamination_rate": (
                                n_false_contam / max(1, n_true_observed + n_false_contam)
                            ),
                            "released": int(released),
                            "actual_FTR": actual_ftr,
                            "violates_alpha": bool(actual_ftr > alpha),
                            "raw_topK_actual_FTR": float(pool["_full_false"].mean()) if len(pool) else 0.0,
                            "mass_ratio": best_ratio,
                            "self_consistency_margin": margin,
                            "max_observed_e": float(pool_e.max()) if len(pool_e) else 0.0,
                            "required_e": 1.0 / alpha,
                            "block_coverage": diag["block_coverage"],
                            "n_nonempty_null_cal_blocks": diag["n_nonempty_null_cal_blocks"],
                        }
                    )
    return pd.DataFrame(rows)


def build_contamination_tables(args: argparse.Namespace, out_dir: Path) -> tuple[Path, Path]:
    seed_rows = ctc_contamination_rows(args)
    seed_path = out_dir / "table_ctc_audit_contamination_sensitivity_seed_rows.csv"
    seed_rows.to_csv(seed_path, index=False)
    summary_rows = []
    for key, group in seed_rows.groupby(
        ["domain", "dataset", "proposal_source", "rho", "epsilon_false_verified_positive", "alpha", "K"],
        dropna=False,
    ):
        domain, dataset, source, rho, epsilon, alpha, budget = key
        ftr = group["actual_FTR"].astype(float).to_numpy()
        ftr_lo, ftr_hi = bootstrap_ci(ftr)
        summary_rows.append(
            {
                "domain": domain,
                "dataset": dataset,
                "proposal_source": source,
                "rho": rho,
                "epsilon_false_verified_positive": epsilon,
                "alpha": alpha,
                "K": budget,
                "seeds": int(group["seed"].nunique()),
                "release_rate": float((group["released"].astype(int) > 0).mean()),
                "mean_release_size": float(group["released"].astype(float).mean()),
                "actual_FTR_mean": float(ftr.mean()),
                "actual_FTR_max": float(ftr.max()),
                "actual_FTR_bootstrap95_low": ftr_lo,
                "actual_FTR_bootstrap95_high": ftr_hi,
                "violation_rate": float(group["violates_alpha"].astype(bool).mean()),
                "mass_ratio_mean": float(group["mass_ratio"].astype(float).mean()),
                "raw_topK_actual_FTR_mean": float(group["raw_topK_actual_FTR"].astype(float).mean()),
                "false_links_injected_as_verified_positive_mean": float(
                    group["false_links_injected_as_verified_positive"].astype(float).mean()
                ),
                "realized_verified_positive_contamination_rate_mean": float(
                    group["realized_verified_positive_contamination_rate"].astype(float).mean()
                ),
                "interpretation": (
                    "one_sided_reliability_intact"
                    if float(epsilon) == 0.0
                    else "assumption_violation_sensitivity_not_a_formal_guarantee"
                ),
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary_path = out_dir / "table_ctc_audit_contamination_sensitivity.csv"
    figure_path = out_dir / "figure_ctc_audit_contamination_sensitivity.csv"
    summary.to_csv(summary_path, index=False)
    summary[
        [
            "epsilon_false_verified_positive",
            "alpha",
            "K",
            "release_rate",
            "mean_release_size",
            "actual_FTR_mean",
            "actual_FTR_bootstrap95_low",
            "actual_FTR_bootstrap95_high",
            "violation_rate",
            "mass_ratio_mean",
        ]
    ].to_csv(figure_path, index=False)
    return summary_path, figure_path


def write_report(out_dir: Path, outputs: dict[str, str]) -> Path:
    report_path = out_dir / "NEAR_BOUNDARY_AND_CONTAMINATION_CLOSEOUT.md"
    text = f"""# Near-Boundary Release and Audit-Contamination Closeout

## Near-Boundary Release Value

The main near-boundary practice-benefit row is intentionally non-random and
comes from the materials-discovery source.  CTC learned-hybrid and SpaceNet 7
geometry rows are included in the screening table as clean-slice positives, not
as near-boundary raw-risk evidence.  This prevents using a randomized source as
the main practice-benefit claim.

Primary table: `{outputs['near_boundary']}`

Domain screening table: `{outputs['near_boundary_screening']}`

## Audit-Contamination Sensitivity

The CTC sensitivity deliberately violates the one-sided reliability assumption
on a high-volume structured-link stress row (K=1000, alpha=0.20) by marking
calibration-block high-score false links as verified positives at rates epsilon
in {{0%, 1%, 3%, 5%, 10%}}.  These rows are not formal guarantees; they measure
how release rate, release size, actual FTR, violation rate, and mass ratio
change when the theorem assumption is broken.

Summary table: `{outputs['contamination']}`

Figure-ready CSV: `{outputs['contamination_figure']}`
"""
    report_path.write_text(text, encoding="utf-8")
    return report_path


def update_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path)}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/release_story/paper_diagnostics")
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--primary-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--weak-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")
    parser.add_argument("--primary-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--weak-pred-col", default="e_form_per_atom_megnet")
    parser.add_argument("--stability-threshold", type=float, default=0.0)
    parser.add_argument(
        "--ctc-learned-universe",
        default="/home/waas/paper_experiments/outputs/ctc_link_certification/universe_gt_tra_noisy_w90_win5/candidate_universe.csv",
    )
    parser.add_argument("--ctc-contamination-dataset-label", default="Cell Tracking Challenge structured-link high-volume stress")
    parser.add_argument("--ctc-contamination-source-label", default="GT-TRA noisy geometric linker")
    parser.add_argument("--ctc-rho", type=float, default=0.10)
    parser.add_argument("--ctc-alphas", default="0.20")
    parser.add_argument("--ctc-budgets", default="1000")
    parser.add_argument("--ctc-tune-ratio", type=float, default=1 / 6)
    parser.add_argument("--ctc-cal-ratio", type=float, default=1 / 2)
    args = parser.parse_args()
    args.ctc_alphas = parse_list(args.ctc_alphas, float)
    args.ctc_budgets = parse_list(args.ctc_budgets, int)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    near_boundary, near_boundary_screening = build_near_boundary_tables(args, out_dir)
    contamination, contamination_figure = build_contamination_tables(args, out_dir)
    report = write_report(
        out_dir,
        {
            "near_boundary": repo_relative(near_boundary),
            "near_boundary_screening": repo_relative(near_boundary_screening),
            "contamination": repo_relative(contamination),
            "contamination_figure": repo_relative(contamination_figure),
        },
    )
    meta = {
        "status": "completed",
        "outputs": {
            "near_boundary": repo_relative(near_boundary),
            "near_boundary_screening": repo_relative(near_boundary_screening),
            "contamination": repo_relative(contamination),
            "contamination_figure": repo_relative(contamination_figure),
            "report": repo_relative(report),
        },
        "input_hashes": {
            "wbm_summary_sha256": sha256_file(Path(args.wbm_summary)),
            "primary_predictions_sha256": sha256_file(Path(args.primary_predictions)),
            "ctc_contamination_universe_sha256": sha256_file(Path(args.ctc_learned_universe)),
        },
        "scope": "paper-facing derived diagnostics; raw datasets, raw images, structures, and model weights are not packaged",
    }
    (out_dir / "near_boundary_and_contamination_report.json").write_text(
        json.dumps(meta, indent=2),
        encoding="utf-8",
    )
    update_manifest(out_dir)
    print(json.dumps(meta, indent=2), flush=True)


if __name__ == "__main__":
    main()
