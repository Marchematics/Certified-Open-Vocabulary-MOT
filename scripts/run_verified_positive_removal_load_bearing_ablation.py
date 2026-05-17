#!/usr/bin/env python3
"""Run candidate-level verified-positive removal load-bearing ablations.

This script intentionally recomputes the null-superset e-values from
candidate-level artifacts.  It does not infer no-removal or random-removal
rows from summary CSVs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_materials_threshold_robustness as materials_threshold  # noqa: E402


DEFAULT_SEEDS = list(range(20))
REMOVAL_MODES = ["full_parc", "no_verified_positive_removal", "random_positive_removal"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


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


def split_ids(ids: list[str | int], seed: int) -> tuple[set[str], set[str]]:
    ordered = sorted(set(str(item) for item in ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = len(ordered) // 2
    return set(ordered[:cut]), set(ordered[cut:])


def observed_positive_mask(labels: np.ndarray, scores: np.ndarray, rho: float, seed: int) -> np.ndarray:
    positive = np.flatnonzero(labels.astype(bool))
    observed = np.zeros(len(labels), dtype=bool)
    if len(positive) == 0 or rho <= 0.0:
        return observed
    n = int(round(len(positive) * min(rho, 1.0)))
    if n <= 0:
        return observed
    chosen = positive[np.argsort(scores[positive])[::-1]][:n]
    observed[chosen] = True
    return observed


def random_calibration_removal(cal_index: np.ndarray, n_remove: int, seed: int) -> np.ndarray:
    remove = np.zeros(len(cal_index), dtype=bool)
    if n_remove <= 0 or len(cal_index) == 0:
        return remove
    rng = np.random.default_rng(seed + 7919)
    local = rng.choice(np.arange(len(cal_index)), size=min(n_remove, len(cal_index)), replace=False)
    remove[local] = True
    return remove


def compute_evalues_from_null(
    test: pd.DataFrame,
    cal: pd.DataFrame,
    *,
    block_col: str,
    score_col: str,
    cal_block_ids: list[str],
    cal_null_mask: np.ndarray,
    alpha: float,
) -> tuple[np.ndarray, dict]:
    null_cal = cal.loc[cal_null_mask].copy()
    maxima = (
        null_cal.groupby(block_col, sort=False)[score_col].max().astype(float).to_numpy()
        if len(null_cal)
        else np.asarray([], dtype=float)
    )
    n_nonempty = int(len(maxima))
    n_total = int(len(set(str(x) for x in cal_block_ids)))
    p_min = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    required = 1.0 / alpha if alpha > 0 else None
    if gamma is None or len(test) == 0 or len(maxima) == 0:
        evalues = np.zeros(len(test), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        scores = test[score_col].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        evalues = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return evalues.astype(float), {
        "n_cal_blocks": n_total,
        "n_nonempty_null_cal_blocks": n_nonempty,
        "n_empty_cal_blocks": max(0, n_total - n_nonempty),
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_e": required,
        "block_coverage": n_nonempty / n_total if n_total else 0.0,
    }


def empty_reason(released: int, diag: dict, max_observed_e: float) -> str:
    if released:
        return ""
    required = diag.get("required_e")
    emax = diag.get("emax_effective")
    if required is not None and (emax is None or float(emax) < float(required)):
        return "resolution_below_required_emax"
    if required is not None and float(max_observed_e) < float(required):
        return "observed_e_below_required_emax"
    return "insufficient_high_e_mass_for_uniform_scs"


def run_row(
    *,
    frame: pd.DataFrame,
    target_row: str,
    domain: str,
    dataset: str,
    proposal_source: str,
    unit: str,
    block_col: str,
    score_col: str,
    label_col: str,
    rho: float,
    alpha: float,
    budget: int,
    seeds: list[int],
) -> pd.DataFrame:
    rows: list[dict] = []
    work = frame.reset_index(drop=True).copy()
    labels = work[label_col].to_numpy(dtype=bool)
    scores = work[score_col].to_numpy(dtype=float)
    block_values = work[block_col].astype(str)
    for seed in seeds:
        observed = observed_positive_mask(labels, scores, rho=rho, seed=seed)
        cal_blocks, test_blocks = split_ids(block_values.tolist(), seed)
        cal_mask = block_values.isin(cal_blocks).to_numpy()
        test_mask = block_values.isin(test_blocks).to_numpy()
        cal = work.loc[cal_mask].copy()
        test = work.loc[test_mask].sort_values(score_col, ascending=False).copy()
        cal_observed = observed[cal_mask]
        for mode in REMOVAL_MODES:
            if mode == "full_parc":
                cal_null_mask = ~cal_observed
            elif mode == "no_verified_positive_removal":
                cal_null_mask = np.ones(len(cal), dtype=bool)
            elif mode == "random_positive_removal":
                random_removed = random_calibration_removal(cal.index.to_numpy(), int(cal_observed.sum()), seed)
                cal_null_mask = ~random_removed
            else:
                raise ValueError(mode)
            evalues, diag = compute_evalues_from_null(
                test,
                cal,
                block_col=block_col,
                score_col=score_col,
                cal_block_ids=list(cal_blocks),
                cal_null_mask=cal_null_mask,
                alpha=alpha,
            )
            pool = test.head(budget).copy()
            pool_e = evalues[: len(pool)]
            released, tau, margin, best_ratio = scs_release_count(pool_e, alpha=alpha, budget=budget)
            selected = pool.iloc[np.argsort(pool_e)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
            actual_ftr = float((~selected[label_col].astype(bool)).mean()) if released else 0.0
            raw_ftr = float((~pool[label_col].astype(bool)).mean()) if len(pool) else 0.0
            max_observed_e = float(np.max(evalues)) if len(evalues) else 0.0
            rows.append(
                {
                    "domain": domain,
                    "dataset": dataset,
                    "unit": unit,
                    "target_row": target_row,
                    "proposal_source": proposal_source,
                    "block_definition": block_col,
                    "rho": rho,
                    "alpha": alpha,
                    "K": budget,
                    "seed": seed,
                    "removal_mode": mode,
                    "observed_positive_strategy": "top_score",
                    "observed_positive_total": int(observed.sum()),
                    "observed_positive_in_calibration": int(cal_observed.sum()),
                    "removed_from_calibration_null": int((~cal_null_mask).sum()),
                    "released": int(released),
                    "actual_FTR": actual_ftr,
                    "raw_topK_actual_FTR": raw_ftr,
                    "max_observed_e": max_observed_e,
                    "selected_e_min": float(pool_e[np.argsort(pool_e)[::-1][:released]].min()) if released else 0.0,
                    "selected_e_mean": float(pool_e[np.argsort(pool_e)[::-1][:released]].mean()) if released else 0.0,
                    "selected_e_max": float(pool_e.max()) if released else 0.0,
                    "required_e": float(diag["required_e"]) if diag["required_e"] is not None else math.nan,
                    "emax_effective": diag["emax_effective"],
                    "best_mass_ratio": best_ratio,
                    "self_consistency_margin": margin,
                    "tau_k": tau if released else "",
                    "n_cal_blocks": diag["n_cal_blocks"],
                    "n_nonempty_null_cal_blocks": diag["n_nonempty_null_cal_blocks"],
                    "block_coverage": diag["block_coverage"],
                    "empty_reason": empty_reason(released, diag, max_observed_e),
                    "evidence_status": "completed_candidate_level_rerun",
                }
            )
    return pd.DataFrame(rows)


def summarize(seed_rows: pd.DataFrame) -> pd.DataFrame:
    group_cols = [
        "domain",
        "dataset",
        "unit",
        "target_row",
        "proposal_source",
        "block_definition",
        "rho",
        "alpha",
        "K",
        "removal_mode",
    ]
    rows: list[dict] = []
    for key, group in seed_rows.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "non_empty_seeds": int((group["released"].astype(int) > 0).sum()),
                "mean_release": float(group["released"].astype(float).mean()),
                "min_release": int(group["released"].astype(int).min()),
                "max_release": int(group["released"].astype(int).max()),
                "actual_FTR_mean": float(group["actual_FTR"].astype(float).mean()),
                "actual_FTR_max": float(group["actual_FTR"].astype(float).max()),
                "raw_topK_actual_FTR_mean": float(group["raw_topK_actual_FTR"].astype(float).mean()),
                "best_mass_ratio_mean": float(group["best_mass_ratio"].astype(float).mean()),
                "max_observed_e_mean": float(group["max_observed_e"].astype(float).mean()),
                "required_e": float(group["required_e"].astype(float).mean()),
                "block_coverage_mean": float(group["block_coverage"].astype(float).mean()),
                "observed_positive_total_mean": float(group["observed_positive_total"].astype(float).mean()),
                "observed_positive_in_calibration_mean": float(group["observed_positive_in_calibration"].astype(float).mean()),
                "removed_from_calibration_null_mean": float(group["removed_from_calibration_null"].astype(float).mean()),
                "dominant_empty_reason": (
                    group["empty_reason"].dropna().mode().iloc[0]
                    if not group["empty_reason"].dropna().empty
                    else ""
                ),
                "evidence_status": "completed_candidate_level_rerun",
            }
        )
        rows.append(row)
    summary = pd.DataFrame(rows)
    full = summary[summary["removal_mode"] == "full_parc"][
        ["target_row", "mean_release", "actual_FTR_mean", "best_mass_ratio_mean", "non_empty_seeds"]
    ].rename(
        columns={
            "mean_release": "full_parc_mean_release",
            "actual_FTR_mean": "full_parc_actual_FTR_mean",
            "best_mass_ratio_mean": "full_parc_best_mass_ratio_mean",
            "non_empty_seeds": "full_parc_non_empty_seeds",
        }
    )
    summary = summary.merge(full, on="target_row", how="left")
    summary["release_delta_vs_full"] = summary["mean_release"] - summary["full_parc_mean_release"]
    summary["ftr_delta_vs_full"] = summary["actual_FTR_mean"] - summary["full_parc_actual_FTR_mean"]
    summary["mass_ratio_delta_vs_full"] = summary["best_mass_ratio_mean"] - summary["full_parc_best_mass_ratio_mean"]
    summary["load_bearing_interpretation"] = summary.apply(
        lambda row: (
            "verified_positive_removal_load_bearing"
            if row["removal_mode"] != "full_parc" and row["mean_release"] < row["full_parc_mean_release"]
            else (
                "verified_positive_removal_not_load_bearing_for_this_row"
                if row["removal_mode"] != "full_parc"
                else "reference_full_parc"
            )
        ),
        axis=1,
    )
    return summary


def ctc_rows(args: argparse.Namespace) -> pd.DataFrame:
    path = Path(args.ctc_universe)
    frame = pd.read_csv(path, low_memory=False)
    frame["_full_true"] = ~bool_series(frame["is_unmatched"]).to_numpy(dtype=bool)
    rows = []
    for budget in [100, 300]:
        rows.append(
            run_row(
                frame=frame,
                target_row=f"ctc_learned_strict_alpha010_K{budget}",
                domain="biomedical_cell_tracking",
                dataset="Cell Tracking Challenge learned-hybrid held-out sequence",
                proposal_source="ctc_learned_hybrid_appearance_sequence_disjoint",
                unit="cell_link",
                block_col="video_id",
                score_col="score",
                label_col="_full_true",
                rho=0.10,
                alpha=0.10,
                budget=budget,
                seeds=args.seeds,
            )
        )
    return pd.concat(rows, ignore_index=True)


def materials_rows(args: argparse.Namespace) -> pd.DataFrame:
    frame, _meta = materials_threshold.load_frame(args)
    specs = [
        {
            "target_row": "materials_cgcnn_exact_stable_alpha010_K100",
            "frame": frame,
            "source": "cgcnn_ensemble_learned_materials_model",
            "score_col": "cgcnn_score",
            "label_col": "stable_exact",
            "budget": 100,
        },
        {
            "target_row": "materials_alignn_exact_stable_alpha010_K300",
            "frame": frame,
            "source": "alignn_ff_modern_learned_materials_model",
            "score_col": "alignn_score",
            "label_col": "stable_exact",
            "budget": 300,
        },
        {
            "target_row": "materials_alignn_exact_stable_alpha010_K500",
            "frame": frame,
            "source": "alignn_ff_modern_learned_materials_model",
            "score_col": "alignn_score",
            "label_col": "stable_exact",
            "budget": 500,
        },
        {
            "target_row": "materials_alignn_margin_excluded_25meV_alpha010_K100",
            "frame": frame[~frame["near_boundary_25meV"].astype(bool)].copy(),
            "source": "alignn_ff_modern_learned_materials_model",
            "score_col": "alignn_score",
            "label_col": "stable_exact",
            "budget": 100,
        },
    ]
    rows = []
    for spec in specs:
        rows.append(
            run_row(
                frame=spec["frame"],
                target_row=spec["target_row"],
                domain="materials_discovery",
                dataset="Matbench Discovery WBM unique prototypes",
                proposal_source=spec["source"],
                unit="stable_inorganic_crystal_candidate",
                block_col="composition_family_pair",
                score_col=spec["score_col"],
                label_col=spec["label_col"],
                rho=0.10,
                alpha=0.10,
                budget=spec["budget"],
                seeds=args.seeds,
            )
        )
    return pd.concat(rows, ignore_index=True)


def write_closeout(path: Path, summary: pd.DataFrame, seed_path: Path, summary_path: Path) -> None:
    n_rows = int(summary["target_row"].nunique())
    n_load_bearing = int(
        summary[
            summary["load_bearing_interpretation"].astype(str).eq("verified_positive_removal_load_bearing")
        ]["target_row"].nunique()
    )
    boundary = summary[
        summary["target_row"].astype(str).eq("materials_alignn_margin_excluded_25meV_alpha010_K100")
        & summary["removal_mode"].astype(str).eq("full_parc")
    ]
    boundary_text = ""
    if not boundary.empty:
        boundary_text = (
            f"- ALIGNN margin-excluded 25meV K=100 full-PARC FTR: "
            f"{float(boundary.iloc[0]['actual_FTR_mean']):.3f}; this remains a boundary sensitivity row, not a strict pass.\n"
        )
    text = (
        "# Verified-Positive Removal Load-Bearing Closeout\n\n"
        "This closeout is completed evidence from candidate-level reruns. It is not derived from summary-only tables.\n\n"
        f"- Target rows rerun: {n_rows}\n"
        f"- Seed-level rows: {len(pd.read_csv(seed_path))}\n"
        f"- Target rows showing lower release under no-removal or random-removal controls: {n_load_bearing}\n"
        f"{boundary_text}\n"
        "## Removal modes\n\n"
        "- `full_parc`: remove top-score observed true positives from the calibration null superset.\n"
        "- `no_verified_positive_removal`: keep observed positives inside the calibration null superset.\n"
        "- `random_positive_removal`: remove the same number of calibration candidates at random as a negative control.\n\n"
        "## Artifacts\n\n"
        f"- Seed rows: `{seed_path.name}`\n"
        f"- Summary rows: `{summary_path.name}`\n"
    )
    path.write_text(text, encoding="utf-8")


def write_provenance(path: Path, artifact_path: Path, args: argparse.Namespace, report: dict, role: str) -> None:
    provenance = {
        "status": "completed",
        "evidence_status": "completed_candidate_level_rerun",
        "role": role,
        "artifact": artifact_path.name,
        "command": "python scripts/run_verified_positive_removal_load_bearing_ablation.py",
        "parameters": {
            "seeds": args.seeds,
            "rho": 0.10,
            "alpha": 0.10,
            "removal_modes": REMOVAL_MODES,
            "target_rows": report["target_rows"],
        },
        "inputs": {
            "ctc_universe_sha256": report["ctc_universe_sha256"],
            "wbm_summary_sha256": report["wbm_summary_sha256"],
            "cgcnn_predictions_sha256": report["cgcnn_predictions_sha256"],
            "alignn_predictions_sha256": report["alignn_predictions_sha256"],
        },
        "output_sha256": sha256_file(artifact_path),
        "notes": [
            "Candidate-level rerun; no no-removal row was inferred from summary tables.",
            "ALIGNN margin-excluded 25meV K=100 remains boundary sensitivity, not a strict pass.",
        ],
    }
    path.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")


def update_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ctc-universe",
        default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/universe_sequence02_eval_w1/candidate_universe.csv",
    )
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--cgcnn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--alignn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
    parser.add_argument("--cgcnn-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--alignn-pred-col", default="e_form_per_atom_alignn_ff")
    parser.add_argument("--out-dir", default="outputs/milestones/scientific_release_success_map")
    parser.add_argument("--seeds", default=",".join(str(seed) for seed in DEFAULT_SEEDS))
    args = parser.parse_args()
    args.seeds = [int(seed) for seed in str(args.seeds).split(",") if str(seed).strip()]

    started = time.perf_counter()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_rows = pd.concat([ctc_rows(args), materials_rows(args)], ignore_index=True)
    summary = summarize(seed_rows)

    seed_path = out_dir / "table_verified_positive_removal_load_bearing_seed_rows.csv"
    summary_path = out_dir / "table_verified_positive_removal_load_bearing.csv"
    closeout_path = out_dir / "VERIFIED_POSITIVE_REMOVAL_LOAD_BEARING_CLOSEOUT.md"
    report_path = out_dir / "verified_positive_removal_load_bearing_summary.json"
    seed_rows.to_csv(seed_path, index=False)
    summary.to_csv(summary_path, index=False)
    write_closeout(closeout_path, summary, seed_path, summary_path)
    report = {
        "status": "completed",
        "evidence_status": "completed_candidate_level_rerun",
        "runtime_sec": time.perf_counter() - started,
        "target_rows": int(summary["target_row"].nunique()),
        "seed_rows": int(len(seed_rows)),
        "summary_table": str(summary_path),
        "seed_table": str(seed_path),
        "ctc_universe_sha256": sha256_file(Path(args.ctc_universe)),
        "wbm_summary_sha256": sha256_file(Path(args.wbm_summary)),
        "cgcnn_predictions_sha256": sha256_file(Path(args.cgcnn_predictions)),
        "alignn_predictions_sha256": sha256_file(Path(args.alignn_predictions)),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_provenance(
        summary_path.with_suffix(summary_path.suffix + ".provenance.json"),
        summary_path,
        args,
        report,
        "summary_table",
    )
    write_provenance(
        seed_path.with_suffix(seed_path.suffix + ".provenance.json"),
        seed_path,
        args,
        report,
        "seed_rows_table",
    )
    write_provenance(
        closeout_path.with_suffix(closeout_path.suffix + ".provenance.json"),
        closeout_path,
        args,
        report,
        "closeout",
    )
    update_manifest(out_dir)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
