#!/usr/bin/env python3
"""Build materials stability-threshold robustness tables.

This is a supplemental rerun over the public Matbench Discovery / WBM summary
and public model prediction CSVs.  It does not overwrite the primary materials
milestone tables; it adds threshold and boundary-condition sensitivity rows.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_materials_discovery_parc_flagship import (
    add_blocks,
    bootstrap_ci,
    compute_evalues,
    empty_reason,
    parse_list,
    scs_release_count,
    sha256_file,
    split_blocks,
    write_manifest,
)


SUMMARY_COLS = [
    "material_id",
    "formula",
    "e_form_per_atom_mp2020_corrected",
    "e_above_hull_mp2020_corrected_ppd_mp",
    "wyckoff_spglib",
    "unique_prototype",
]


def load_frame(args: argparse.Namespace) -> tuple[pd.DataFrame, dict]:
    summary_path = Path(args.wbm_summary)
    cgcnn_path = Path(args.cgcnn_predictions)
    alignn_path = Path(args.alignn_predictions)
    missing = [str(path) for path in [summary_path, cgcnn_path, alignn_path] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing materials robustness inputs: {missing}")

    summary = pd.read_csv(summary_path, usecols=SUMMARY_COLS)
    cgcnn = pd.read_csv(cgcnn_path, usecols=["material_id", args.cgcnn_pred_col])
    alignn = pd.read_csv(alignn_path, usecols=["material_id", args.alignn_pred_col])
    frame = summary.merge(cgcnn, on="material_id", how="inner").merge(alignn, on="material_id", how="inner")
    frame = frame[frame["unique_prototype"].astype(bool)].copy()
    frame = add_blocks(frame)
    hull_reference = (
        frame["e_form_per_atom_mp2020_corrected"].astype(float)
        - frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float)
    )
    frame["cgcnn_predicted_e_above_hull"] = frame[args.cgcnn_pred_col].astype(float) - hull_reference
    frame["alignn_predicted_e_above_hull"] = frame[args.alignn_pred_col].astype(float) - hull_reference
    frame["cgcnn_score"] = -frame["cgcnn_predicted_e_above_hull"]
    frame["alignn_score"] = -frame["alignn_predicted_e_above_hull"]
    frame["e_hull"] = frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float)
    frame["stable_exact"] = frame["e_hull"] <= 0.0
    frame["stable_tolerance_25meV"] = frame["e_hull"] <= 0.025
    frame["clear_stable_minus25meV"] = frame["e_hull"] <= -0.025
    frame["near_boundary_25meV"] = frame["e_hull"].between(-0.025, 0.025, inclusive="both")
    meta = {
        "wbm_summary_sha256": sha256_file(summary_path),
        "cgcnn_predictions_sha256": sha256_file(cgcnn_path),
        "alignn_predictions_sha256": sha256_file(alignn_path),
    }
    return frame.reset_index(drop=True), meta


def observed_positive_mask(frame: pd.DataFrame, label_col: str, score_col: str, rho: float, seed: int) -> np.ndarray:
    true_idx = np.flatnonzero(frame[label_col].to_numpy(dtype=bool))
    observed = np.zeros(len(frame), dtype=bool)
    if len(true_idx) == 0 or rho <= 0.0:
        return observed
    n_observed = int(round(len(true_idx) * min(rho, 1.0)))
    if n_observed <= 0:
        return observed
    scores = frame[score_col].to_numpy(dtype=float)
    chosen = true_idx[np.argsort(scores[true_idx])[::-1]][:n_observed]
    observed[chosen] = True
    return observed


def run_dual_label_grid(
    frame: pd.DataFrame,
    *,
    variant: str,
    source: str,
    score_col: str,
    observed_label_col: str,
    eval_label_col: str,
    block_col: str,
    rho: float,
    alpha: float,
    budgets: list[int],
    seeds: list[int],
) -> pd.DataFrame:
    rows: list[dict] = []
    work = frame.reset_index(drop=True).copy()
    for seed in seeds:
        observed = observed_positive_mask(work, observed_label_col, score_col, rho, seed)
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
            released, _tau, margin, best_ratio = scs_release_count(evalues, alpha=alpha, budget=budget)
            selected = pool.iloc[np.argsort(evalues)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
            actual_ftr = float((~selected[eval_label_col].astype(bool)).mean()) if released else 0.0
            raw_ftr = float((~pool[eval_label_col].astype(bool)).mean()) if len(pool) else 0.0
            boundary_release_rate = (
                float(selected["near_boundary_25meV"].astype(bool).mean()) if released and "near_boundary_25meV" in selected else 0.0
            )
            rows.append(
                {
                    "variant": variant,
                    "proposal_source": source,
                    "block_definition": block_col,
                    "rho": rho,
                    "alpha": alpha,
                    "K": budget,
                    "seed": seed,
                    "observed_label_col": observed_label_col,
                    "eval_label_col": eval_label_col,
                    "candidate_count": len(work),
                    "observed_positive_count": int(observed.sum()),
                    "eval_positive_count": int(work[eval_label_col].astype(bool).sum()),
                    "released": int(released),
                    "actual_FTR": actual_ftr,
                    "raw_topK_actual_FTR": raw_ftr,
                    "released_boundary_rate_25meV": boundary_release_rate,
                    "max_observed_e": max_observed_e,
                    "required_e": diag["required_emax"],
                    "emax_effective": diag["emax_effective"],
                    "best_mass_ratio": best_ratio,
                    "self_consistency_margin": margin,
                    "block_coverage": diag["block_coverage"],
                    "empty_reason": empty_reason(released, diag, max_observed_e),
                    "release_feasible": bool(released > 0),
                }
            )
    return pd.DataFrame(rows)


def summarize(rows: pd.DataFrame) -> pd.DataFrame:
    out_rows: list[dict] = []
    group_cols = ["variant", "proposal_source", "block_definition", "rho", "alpha", "K"]
    for key, group in rows.groupby(group_cols, dropna=False):
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
                "required_e": float(group["required_e"].astype(float).mean()),
                "block_coverage_mean": float(group["block_coverage"].astype(float).mean()),
                "released_boundary_rate_25meV_mean": float(group["released_boundary_rate_25meV"].astype(float).mean()),
                "dominant_empty_reason": (
                    group["empty_reason"].dropna().mode().iloc[0]
                    if not group["empty_reason"].dropna().empty
                    else ""
                ),
            }
        )
        row["robustness_interpretation"] = (
            "strict_alpha010_pass"
            if row["non_empty_seeds"] >= math.ceil(0.9 * row["seeds"]) and row["actual_FTR_mean"] <= row["alpha"]
            else "sensitivity_or_refusal"
        )
        out_rows.append(row)
    return pd.DataFrame(out_rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--cgcnn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--alignn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
    parser.add_argument("--cgcnn-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--alignn-pred-col", default="e_form_per_atom_alignn_ff")
    parser.add_argument("--out-dir", default="outputs/milestones/scientific_domain_materials")
    parser.add_argument("--budgets", default="50,100,300,500,1000,5000")
    parser.add_argument("--seeds", default=",".join(str(i) for i in range(20)))
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--alpha", type=float, default=0.10)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frame, meta = load_frame(args)
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)

    variant_specs = [
        {
            "variant": "exact_stable_primary",
            "frame": frame,
            "observed_label_col": "stable_exact",
            "eval_label_col": "stable_exact",
            "description": "Primary exact-stability target: E_hull <= 0.",
        },
        {
            "variant": "tolerance_positive_25meV",
            "frame": frame,
            "observed_label_col": "stable_tolerance_25meV",
            "eval_label_col": "stable_tolerance_25meV",
            "description": "Tolerance-positive target: E_hull <= 25 meV/atom.",
        },
        {
            "variant": "margin_excluded_25meV",
            "frame": frame[~frame["near_boundary_25meV"].astype(bool)].copy(),
            "observed_label_col": "stable_exact",
            "eval_label_col": "stable_exact",
            "description": "Remove candidates within +/-25 meV/atom of the stability boundary before calibration and evaluation.",
        },
        {
            "variant": "conservative_clear_stable_observed_25meV",
            "frame": frame,
            "observed_label_col": "clear_stable_minus25meV",
            "eval_label_col": "stable_exact",
            "description": "Only clearly stable E_hull <= -25 meV/atom candidates can be observed positives; exact stability remains the evaluation target.",
        },
    ]
    source_specs = [
        ("cgcnn_ensemble_learned_materials_model", "cgcnn_score"),
        ("alignn_ff_modern_learned_materials_model", "alignn_score"),
    ]

    seed_rows = []
    for variant in variant_specs:
        for source, score_col in source_specs:
            seed_rows.append(
                run_dual_label_grid(
                    variant["frame"],
                    variant=variant["variant"],
                    source=source,
                    score_col=score_col,
                    observed_label_col=variant["observed_label_col"],
                    eval_label_col=variant["eval_label_col"],
                    block_col="composition_family_pair",
                    rho=args.rho,
                    alpha=args.alpha,
                    budgets=budgets,
                    seeds=seeds,
                )
            )
    seed_table = pd.concat(seed_rows, ignore_index=True)
    summary = summarize(seed_table)
    variant_report = pd.DataFrame(
        [
            {
                "variant": spec["variant"],
                "description": spec["description"],
                "n_candidates": len(spec["frame"]),
                "observed_label_col": spec["observed_label_col"],
                "eval_label_col": spec["eval_label_col"],
                "n_observed_label_positive": int(spec["frame"][spec["observed_label_col"]].astype(bool).sum()),
                "n_eval_label_positive": int(spec["frame"][spec["eval_label_col"]].astype(bool).sum()),
            }
            for spec in variant_specs
        ]
    )

    seed_path = out_dir / "table_materials_stability_threshold_robustness_seed_rows.csv"
    summary_path = out_dir / "table_materials_stability_threshold_robustness.csv"
    report_path = out_dir / "table_materials_stability_threshold_variant_report.csv"
    seed_table.to_csv(seed_path, index=False)
    summary.to_csv(summary_path, index=False)
    variant_report.to_csv(report_path, index=False)
    (out_dir / "materials_threshold_robustness_summary.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "inputs": meta,
                "alpha": args.alpha,
                "rho": args.rho,
                "budgets": budgets,
                "seeds": seeds,
                "summary_table": str(summary_path),
                "seed_table": str(seed_path),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_manifest(out_dir)


if __name__ == "__main__":
    main()
