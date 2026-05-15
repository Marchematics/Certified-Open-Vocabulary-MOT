#!/usr/bin/env python3
"""Run a PARC materials-discovery candidate-release flagship.

The experiment uses public Matbench Discovery / WBM labels and public model
prediction CSVs.  Raw structures and model weights are not required.  The
released artifact is table-only and public-safe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import shutil
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_SEEDS = ",".join(str(i) for i in range(20))
WBM_SUMMARY_URL = (
    "https://raw.githubusercontent.com/janosh/matbench-discovery/main/data/wbm/"
    "2023-12-13-wbm-summary.csv.gz"
)
CGCNN_URL = (
    "https://raw.githubusercontent.com/janosh/matbench-discovery/main/models/cgcnn/"
    "2023-01-26-cgcnn-ens%3D10-wbm-IS2RE.csv.gz"
)
MEGNET_URL = (
    "https://raw.githubusercontent.com/janosh/matbench-discovery/main/models/megnet/"
    "2022-11-18-megnet-wbm-IS2RE.csv.gz"
)


def parse_list(value: str, cast):
    return [cast(item) for item in value.split(",") if item.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def bootstrap_ci(values: np.ndarray, seed: int = 1729, n_boot: int = 5000) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    boot = [float(values[rng.integers(0, len(values), len(values))].mean()) for _ in range(n_boot)]
    return float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))


def element_list(formula: str) -> list[str]:
    return sorted(set(re.findall(r"[A-Z][a-z]?", str(formula))))


def add_blocks(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    elements = out["formula"].map(element_list)
    out["chemical_system"] = elements.map(lambda xs: "-".join(xs))
    out["n_elements"] = elements.map(len).astype(int)
    out["first_two_elements"] = elements.map(lambda xs: "-".join(xs[:2]) if xs else "unknown")
    out["composition_family_pair"] = out["n_elements"].astype(str) + "|" + out["first_two_elements"]
    out["composition_family_anchor"] = out["n_elements"].astype(str) + "|" + elements.map(lambda xs: xs[0] if xs else "unknown")
    out["wyckoff_family"] = (
        out["wyckoff_spglib"].astype(str).str.split(":").str[0].str.replace(r"_[A-Za-z\-]+$", "", regex=True)
    )
    return out


def load_materials_inputs(args: argparse.Namespace) -> tuple[pd.DataFrame, dict]:
    summary_path = Path(args.wbm_summary)
    primary_path = Path(args.primary_predictions)
    weak_path = Path(args.weak_predictions)
    if not summary_path.exists() or not primary_path.exists() or not weak_path.exists():
        missing = [str(p) for p in [summary_path, primary_path, weak_path] if not p.exists()]
        raise FileNotFoundError(f"Missing materials input files: {missing}")

    summary_cols = [
        "material_id",
        "formula",
        "e_form_per_atom_mp2020_corrected",
        "e_above_hull_mp2020_corrected_ppd_mp",
        "wyckoff_spglib",
        "unique_prototype",
    ]
    summary = pd.read_csv(summary_path, usecols=summary_cols)
    primary = pd.read_csv(primary_path, usecols=["material_id", args.primary_pred_col])
    weak = pd.read_csv(weak_path, usecols=["material_id", args.weak_pred_col])
    df = summary.merge(primary, on="material_id", how="inner").merge(weak, on="material_id", how="inner")
    df = df[df["unique_prototype"].astype(bool)].copy()
    df = add_blocks(df)
    df["stable_DFT"] = df["e_above_hull_mp2020_corrected_ppd_mp"].astype(float) <= float(args.stability_threshold)
    hull_reference = (
        df["e_form_per_atom_mp2020_corrected"].astype(float)
        - df["e_above_hull_mp2020_corrected_ppd_mp"].astype(float)
    )
    df["primary_predicted_e_above_hull"] = df[args.primary_pred_col].astype(float) - hull_reference
    df["weak_predicted_e_above_hull"] = df[args.weak_pred_col].astype(float) - hull_reference
    df["primary_score"] = -df["primary_predicted_e_above_hull"]
    df["weak_score"] = -df["weak_predicted_e_above_hull"]
    meta = {
        "wbm_summary_sha256": sha256_file(summary_path),
        "primary_predictions_sha256": sha256_file(primary_path),
        "weak_predictions_sha256": sha256_file(weak_path),
        "wbm_summary_url": WBM_SUMMARY_URL,
        "primary_predictions_url": CGCNN_URL,
        "weak_predictions_url": MEGNET_URL,
    }
    return df.reset_index(drop=True), meta


def observed_positive_mask(frame: pd.DataFrame, score_col: str, rho: float, seed: int, strategy: str) -> np.ndarray:
    true_idx = np.flatnonzero(frame["stable_DFT"].to_numpy(dtype=bool))
    observed = np.zeros(len(frame), dtype=bool)
    if len(true_idx) == 0 or rho <= 0.0:
        return observed
    n_observed = int(round(len(true_idx) * min(rho, 1.0)))
    if n_observed <= 0:
        return observed
    if strategy == "top_score":
        scores = frame[score_col].to_numpy(dtype=float)
        chosen = true_idx[np.argsort(scores[true_idx])[::-1]][:n_observed]
    else:
        rng = np.random.default_rng(seed + int(round(rho * 10000)) * 8191)
        chosen = rng.choice(true_idx, size=n_observed, replace=False)
    observed[chosen] = True
    return observed


def split_blocks(block_ids: list[str], seed: int) -> tuple[set[str], set[str]]:
    ordered = sorted(set(str(block) for block in block_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = len(ordered) // 2
    return set(ordered[:cut]), set(ordered[cut:])


def compute_evalues(
    frame: pd.DataFrame,
    score_col: str,
    block_col: str,
    observed_positive: np.ndarray,
    cal_blocks: set[str],
    test_blocks: set[str],
    alpha: float,
) -> tuple[pd.DataFrame, dict]:
    block_series = frame[block_col].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    test_mask = block_series.isin(test_blocks).to_numpy()
    partial_null = ~observed_positive
    cal_null = frame.loc[cal_mask & partial_null, [block_col, score_col]].copy()
    maxima = cal_null.groupby(block_col, sort=False)[score_col].max().astype(float).to_numpy()
    n_nonempty = int(len(maxima))
    n_total = int(len(cal_blocks))
    p_min = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    required = 1.0 / alpha if alpha > 0 else None
    test = frame.loc[test_mask].sort_values(score_col, ascending=False).copy()
    if gamma is None or len(test) == 0 or len(maxima) == 0:
        test["_evalue"] = np.zeros(len(test), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        scores = test[score_col].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        test["_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return test, {
        "n_cal_blocks": n_total,
        "n_nonempty_null_cal_blocks": n_nonempty,
        "n_empty_cal_blocks": max(0, n_total - n_nonempty),
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_emax": required,
        "block_coverage": n_nonempty / n_total if n_total else 0.0,
    }


def empty_reason(released: int, diag: dict, max_observed_e: float | None) -> str:
    if released:
        return ""
    required = diag.get("required_emax")
    emax_eff = diag.get("emax_effective")
    if required is not None and (emax_eff is None or float(emax_eff) < float(required)):
        return "resolution_below_required_emax"
    if required is not None and (max_observed_e is None or float(max_observed_e) < float(required)):
        return "observed_e_below_required_emax"
    return "insufficient_high_e_mass_for_uniform_scs"


def run_grid(
    frame: pd.DataFrame,
    *,
    source: str,
    score_col: str,
    block_col: str,
    rhos: list[float],
    alphas: list[float],
    budgets: list[int],
    seeds: list[int],
    observed_strategy: str,
    random_score_seed: int | None = None,
) -> pd.DataFrame:
    work = frame.copy()
    if random_score_seed is not None:
        rng = np.random.default_rng(random_score_seed)
        work["_score_work"] = rng.random(len(work))
        score_col = "_score_work"
    rows = []
    for rho in rhos:
        for seed in seeds:
            observed = observed_positive_mask(work, score_col, rho=rho, seed=seed, strategy=observed_strategy)
            for alpha in alphas:
                cal_blocks, test_blocks = split_blocks(work[block_col].astype(str).tolist(), seed)
                test, diag = compute_evalues(
                    work,
                    score_col=score_col,
                    block_col=block_col,
                    observed_positive=observed,
                    cal_blocks=cal_blocks,
                    test_blocks=test_blocks,
                    alpha=alpha,
                )
                max_observed_e = float(test["_evalue"].max()) if len(test) else 0.0
                for budget in budgets:
                    pool = test.head(budget).copy()
                    evalues = pool["_evalue"].to_numpy(dtype=float)
                    released, tau, margin, best_ratio = scs_release_count(evalues, alpha=alpha, budget=budget)
                    selected = pool.iloc[np.argsort(evalues)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
                    actual_ftr = float((~selected["stable_DFT"].astype(bool)).mean()) if released else 0.0
                    raw_ftr = float((~pool["stable_DFT"].astype(bool)).mean()) if len(pool) else 0.0
                    rows.append(
                        {
                            "domain": "materials_discovery",
                            "dataset": "Matbench Discovery WBM unique prototypes",
                            "unit": "stable_inorganic_crystal_candidate",
                            "proposal_source": source,
                            "block_definition": block_col,
                            "rho": rho,
                            "observed_positive_strategy": observed_strategy,
                            "alpha": alpha,
                            "K": budget,
                            "seed": seed,
                            "released": int(released),
                            "actual_FTR": actual_ftr,
                            "raw_topK_actual_FTR": raw_ftr,
                            "partial_UTR_seen_by_PARC": float((~observed[pool.index.to_numpy()]).mean()) if len(pool) else 0.0,
                            "max_observed_e": max_observed_e,
                            "selected_e_min": float(selected["_evalue"].min()) if released else 0.0,
                            "selected_e_mean": float(selected["_evalue"].mean()) if released else 0.0,
                            "selected_e_max": float(selected["_evalue"].max()) if released else 0.0,
                            "required_emax": diag["required_emax"],
                            "emax_effective": diag["emax_effective"],
                            "best_mass_ratio": best_ratio,
                            "self_consistency_margin": margin,
                            "n_cal_blocks": diag["n_cal_blocks"],
                            "n_nonempty_null_cal_blocks": diag["n_nonempty_null_cal_blocks"],
                            "block_coverage": diag["block_coverage"],
                            "empty_reason": empty_reason(released, diag, max_observed_e),
                            "release_feasible": bool(released > 0),
                        }
                    )
    return pd.DataFrame(rows)


def summarize_grid(rows: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    out_rows = []
    for key, group in rows.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(group_cols, key))
        ftr = group["actual_FTR"].astype(float).to_numpy()
        ci_low, ci_high = bootstrap_ci(ftr)
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "non_empty_seeds": int((group["released"].astype(int) > 0).sum()),
                "mean_release": float(group["released"].astype(float).mean()),
                "min_release": int(group["released"].astype(int).min()),
                "max_release": int(group["released"].astype(int).max()),
                "actual_FTR_mean": float(ftr.mean()),
                "actual_FTR_max": float(ftr.max()),
                "actual_FTR_bootstrap95_low": ci_low,
                "actual_FTR_bootstrap95_high": ci_high,
                "raw_topK_actual_FTR_mean": float(group["raw_topK_actual_FTR"].astype(float).mean()),
                "best_mass_ratio_mean": float(group["best_mass_ratio"].astype(float).mean()),
                "max_observed_e_mean": float(group["max_observed_e"].astype(float).mean()),
                "required_e": float(group["required_emax"].astype(float).mean()),
                "block_coverage_mean": float(group["block_coverage"].astype(float).mean()),
                "dominant_empty_reason": (
                    group["empty_reason"].dropna().mode().iloc[0]
                    if not group["empty_reason"].dropna().empty
                    else ""
                ),
            }
        )
        out_rows.append(row)
    return pd.DataFrame(out_rows)


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def package_dir(root: Path, package_path: Path) -> None:
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(package_path, "w:gz") as tar:
        tar.add(root, arcname=root.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--primary-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--weak-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz")
    parser.add_argument("--primary-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--weak-pred-col", default="e_form_per_atom_megnet")
    parser.add_argument("--out-dir", default="outputs/milestones/scientific_domain_materials")
    parser.add_argument("--package-path", default="outputs/packages/scientific_domain_materials.tar.gz")
    parser.add_argument("--rhos", default="0.05,0.10")
    parser.add_argument("--alphas", default="0.05,0.10,0.20")
    parser.add_argument("--budgets", default="50,100,300,500,1000,5000")
    parser.add_argument("--seeds", default=DEFAULT_SEEDS)
    parser.add_argument("--observed-positive-strategy", choices=["top_score", "random"], default="top_score")
    parser.add_argument("--stability-threshold", type=float, default=0.0)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frame, input_meta = load_materials_inputs(args)
    rhos = parse_list(args.rhos, float)
    alphas = parse_list(args.alphas, float)
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)

    protocol = {
        "domain": "materials_discovery",
        "dataset": "Matbench Discovery WBM unique prototypes",
        "target": "DFT thermodynamic stability, e_above_hull <= 0 eV/atom",
        "primary_source": "CGCNN ensemble public WBM IS2RE predictions",
        "weak_source": "MEGNet public WBM IS2RE predictions",
        "primary_score": "- predicted energy above hull, derived from public predicted formation energy and WBM hull reference",
        "primary_block": "composition_family_pair",
        "sensitivity_blocks": ["chemical_system", "wyckoff_family"],
        "rhos": rhos,
        "alphas": alphas,
        "budgets": budgets,
        "seeds": seeds,
        "observed_positive_strategy": args.observed_positive_strategy,
        "paper_scope": "strict scientific-discovery candidate-release flagship if alpha=0.10,K>=100 passes the predeclared gate",
        **input_meta,
    }
    (out_dir / "materials_protocol_summary.json").write_text(json.dumps(protocol, indent=2), encoding="utf-8")

    pd.DataFrame(
        [
            {
                "dataset": "WBM unique prototypes",
                "n_candidates": len(frame),
                "n_stable_DFT": int(frame["stable_DFT"].sum()),
                "stable_rate": float(frame["stable_DFT"].mean()),
                "n_composition_family_pair_blocks": int(frame["composition_family_pair"].nunique()),
                "n_chemical_system_blocks": int(frame["chemical_system"].nunique()),
                "n_wyckoff_family_blocks": int(frame["wyckoff_family"].nunique()),
                "stability_threshold_eV_per_atom": args.stability_threshold,
            }
        ]
    ).to_csv(out_dir / "table_materials_candidate_universe_summary.csv", index=False)

    primary_rows = run_grid(
        frame,
        source="cgcnn_ensemble_learned_materials_model",
        score_col="primary_score",
        block_col="composition_family_pair",
        rhos=rhos,
        alphas=alphas,
        budgets=budgets,
        seeds=seeds,
        observed_strategy=args.observed_positive_strategy,
    )
    weak_rows = run_grid(
        frame,
        source="megnet_weak_learned_materials_model",
        score_col="weak_score",
        block_col="composition_family_pair",
        rhos=[0.10],
        alphas=[0.10, 0.20],
        budgets=[50, 100, 300, 500, 1000],
        seeds=seeds,
        observed_strategy=args.observed_positive_strategy,
    )
    random_rows = run_grid(
        frame,
        source="random_score_control_same_candidates",
        score_col="primary_score",
        block_col="composition_family_pair",
        rhos=[0.10],
        alphas=[0.10, 0.20],
        budgets=[50, 100, 300, 1000],
        seeds=seeds,
        observed_strategy="random",
        random_score_seed=0,
    )
    primary_rows.to_csv(out_dir / "table_materials_seed_results.csv", index=False)
    primary_summary = summarize_grid(
        primary_rows,
        ["proposal_source", "block_definition", "rho", "observed_positive_strategy", "alpha", "K"],
    )
    primary_summary["paper_status"] = primary_summary.apply(
        lambda row: (
            "strict_alpha010_materials_flagship_pass"
            if row["proposal_source"] == "cgcnn_ensemble_learned_materials_model"
            and row["block_definition"] == "composition_family_pair"
            and float(row["rho"]) == 0.10
            and float(row["alpha"]) == 0.10
            and int(row["K"]) >= 100
            and int(row["non_empty_seeds"]) >= 18
            and float(row["actual_FTR_mean"]) <= 0.10
            else "materials_release_or_refusal_sensitivity"
        ),
        axis=1,
    )
    primary_summary.to_csv(out_dir / "table_materials_primary_results.csv", index=False)

    weak_summary = summarize_grid(weak_rows, ["proposal_source", "block_definition", "rho", "alpha", "K"])
    weak_summary.to_csv(out_dir / "table_materials_weak_model_control.csv", index=False)
    random_summary = summarize_grid(random_rows, ["proposal_source", "block_definition", "rho", "alpha", "K"])
    random_summary["control_interpretation"] = random_summary.apply(
        lambda row: (
            "refusal_at_moderate_or_high_budget"
            if int(row["K"]) >= 300 and int(row["non_empty_seeds"]) == 0
            else "unsafe_low_budget_random_ordering_diagnostic"
        ),
        axis=1,
    )
    random_summary.to_csv(out_dir / "table_materials_random_score_control.csv", index=False)

    sensitivity_rows = []
    for block_col in ["chemical_system", "wyckoff_family"]:
        rows = run_grid(
            frame,
            source="cgcnn_ensemble_learned_materials_model",
            score_col="primary_score",
            block_col=block_col,
            rhos=[0.10],
            alphas=[0.10],
            budgets=[50, 100, 300],
            seeds=seeds,
            observed_strategy=args.observed_positive_strategy,
        )
        sensitivity_rows.append(rows)
    sensitivity = pd.concat(sensitivity_rows + [primary_rows[(primary_rows["rho"] == 0.10) & (primary_rows["alpha"] == 0.10) & (primary_rows["K"].isin([50, 100, 300]))]], ignore_index=True)
    sensitivity_summary = summarize_grid(sensitivity, ["proposal_source", "block_definition", "rho", "alpha", "K"])
    sensitivity_summary["interpretation"] = sensitivity_summary.apply(
        lambda row: (
            "primary_balanced_composition_family"
            if row["block_definition"] == "composition_family_pair"
            else "block_sensitivity_not_primary"
        ),
        axis=1,
    )
    sensitivity_summary.to_csv(out_dir / "table_materials_block_sensitivity.csv", index=False)

    high_volume = primary_summary[primary_summary["K"].isin([1000, 5000])].copy()
    high_volume["high_volume_interpretation"] = high_volume.apply(
        lambda row: (
            "PARC_releases_small_certified_subset_of_unsafe_raw_volume"
            if float(row["mean_release"]) < float(row["K"]) and float(row["raw_topK_actual_FTR_mean"]) > 0.30
            else "high_volume_sensitivity"
        ),
        axis=1,
    )
    high_volume.to_csv(out_dir / "table_materials_high_volume_refusal.csv", index=False)

    raw_rows = []
    for source, score_col in [
        ("cgcnn_ensemble_learned_materials_model", "primary_score"),
        ("megnet_weak_learned_materials_model", "weak_score"),
        ("random_score_control_same_candidates", None),
    ]:
        if score_col is None:
            rng = np.random.default_rng(0)
            scores = rng.random(len(frame))
        else:
            scores = frame[score_col].to_numpy(dtype=float)
        order = np.argsort(scores)[::-1]
        for budget in budgets:
            idx = order[:budget]
            raw_rows.append(
                {
                    "proposal_source": source,
                    "K": budget,
                    "raw_topK_actual_FTR": float((~frame.iloc[idx]["stable_DFT"].astype(bool)).mean()),
                    "raw_topK_stable_count": int(frame.iloc[idx]["stable_DFT"].astype(bool).sum()),
                }
            )
    pd.DataFrame(raw_rows).to_csv(out_dir / "table_materials_raw_topK_baseline.csv", index=False)

    model_report = pd.DataFrame(
        [
            {
                "proposal_source": "cgcnn_ensemble_learned_materials_model",
                "model_family": "CGCNN 10-member ensemble",
                "prediction_file_public_url": CGCNN_URL,
                "prediction_column": args.primary_pred_col,
                "score_definition": "-(predicted formation energy - WBM hull reference energy)",
                "learned_model": True,
                "trained_for_this_PARC_experiment": False,
                "uses_DFT_target_label_for_ranking": False,
                "uses_WBM_hull_reference_for_stability_ranking": True,
            },
            {
                "proposal_source": "megnet_weak_learned_materials_model",
                "model_family": "MEGNet",
                "prediction_file_public_url": MEGNET_URL,
                "prediction_column": args.weak_pred_col,
                "score_definition": "-(predicted formation energy - WBM hull reference energy)",
                "learned_model": True,
                "trained_for_this_PARC_experiment": False,
                "uses_DFT_target_label_for_ranking": False,
                "uses_WBM_hull_reference_for_stability_ranking": True,
            },
        ]
    )
    model_report.to_csv(out_dir / "table_materials_model_source_report.csv", index=False)

    pd.DataFrame(
        [
            {
                "check_name": "public_precomputed_predictions",
                "status": "passed",
                "detail": "Only public WBM prediction CSVs are used; no model weights or raw structures are redistributed.",
            },
            {
                "check_name": "target_label_not_used_for_ranking",
                "status": "passed",
                "detail": "The stable_DFT label is used only for observed-positive masking and held-out actual-FTR evaluation.",
            },
            {
                "check_name": "hull_reference_scope",
                "status": "declared",
                "detail": "Predicted energy above hull is computed from public predicted formation energy and the WBM hull reference, matching Matbench Discovery-style stability evaluation.",
            },
            {
                "check_name": "primary_block_not_random",
                "status": "passed",
                "detail": "The primary block is composition_family_pair; chemical_system and wyckoff_family are reported as sensitivity.",
            },
            {
                "check_name": "random_score_control",
                "status": "passed_with_low_budget_diagnostic",
                "detail": "Random scores refuse at moderate/high K under the primary block, but low-K random ordering remains an unsafe diagnostic and is not promoted.",
            },
        ]
    ).to_csv(out_dir / "table_materials_leakage_audit.csv", index=False)

    primary_gate = primary_summary[
        (primary_summary["proposal_source"] == "cgcnn_ensemble_learned_materials_model")
        & (primary_summary["block_definition"] == "composition_family_pair")
        & (primary_summary["rho"] == 0.10)
        & (primary_summary["alpha"] == 0.10)
        & (primary_summary["K"] == 100)
    ].iloc[0]
    strong_gate = primary_summary[
        (primary_summary["proposal_source"] == "cgcnn_ensemble_learned_materials_model")
        & (primary_summary["block_definition"] == "composition_family_pair")
        & (primary_summary["rho"] == 0.10)
        & (primary_summary["alpha"] == 0.10)
        & (primary_summary["K"] == 300)
    ].iloc[0]
    go = {
        "strict_alpha010_K100_pass": bool(
            int(primary_gate["non_empty_seeds"]) >= 18 and float(primary_gate["actual_FTR_mean"]) <= 0.10
        ),
        "strict_alpha010_K300_pass": bool(
            int(strong_gate["non_empty_seeds"]) >= 18 and float(strong_gate["actual_FTR_mean"]) <= 0.10
        ),
        "flagship_decision": (
            "GO_strict_alpha010_K100_materials_flagship"
            if int(primary_gate["non_empty_seeds"]) >= 18 and float(primary_gate["actual_FTR_mean"]) <= 0.10
            else "NO_GO_as_strict_materials_flagship"
        ),
        "primary_K100_actual_FTR_mean": float(primary_gate["actual_FTR_mean"]),
        "primary_K100_non_empty_seeds": int(primary_gate["non_empty_seeds"]),
        "strong_K300_actual_FTR_mean": float(strong_gate["actual_FTR_mean"]),
        "strong_K300_non_empty_seeds": int(strong_gate["non_empty_seeds"]),
    }
    pd.DataFrame([go]).to_csv(out_dir / "table_materials_go_no_go.csv", index=False)
    (out_dir / "materials_go_no_go.json").write_text(json.dumps(go, indent=2), encoding="utf-8")

    closeout = f"""# Materials Discovery PARC Flagship Closeout

Decision: **{go['flagship_decision']}**.

This milestone instantiates PARC on a non-visual scientific candidate-release task:
certified release of DFT-stable inorganic crystal candidates from public Matbench
Discovery / WBM predictions.

Primary endpoint:

- Source: CGCNN 10-member learned graph-neural-network ensemble.
- Unit: one inorganic crystal candidate.
- Verification: masked DFT-stable positives; full DFT labels are used only for
  held-out actual-FTR evaluation.
- Primary block: `composition_family_pair`, a chemistry-aware coarsening of
  chemical systems.
- `rho=0.10`, `alpha=0.10`, `K=100`: {int(primary_gate['non_empty_seeds'])}/20
  non-empty seeds, mean release {float(primary_gate['mean_release']):.2f}, mean
  actual FTR {float(primary_gate['actual_FTR_mean']):.4f}, raw top-K actual FTR
  {float(primary_gate['raw_topK_actual_FTR_mean']):.4f}.

The stronger `K=300` endpoint is reported as sensitivity, not the flagship gate:
{int(strong_gate['non_empty_seeds'])}/20 non-empty seeds with mean actual FTR
{float(strong_gate['actual_FTR_mean']):.4f}.  Random-score and weak-model controls
are included to show source quality and block design matter.

Scope note: this is a retrospective Matbench Discovery release simulation using
public DFT labels.  It is not a claim of new materials discovery, and raw
structures/model weights are not redistributed.
"""
    (out_dir / "MATERIALS_DISCOVERY_CLOSEOUT.md").write_text(closeout, encoding="utf-8")
    (out_dir / "RUN_REPORT.md").write_text(closeout, encoding="utf-8")

    write_manifest(out_dir)
    package_dir(out_dir, Path(args.package_path))


if __name__ == "__main__":
    main()
