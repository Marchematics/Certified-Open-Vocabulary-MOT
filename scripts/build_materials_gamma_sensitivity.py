#!/usr/bin/env python3
"""Build fixed-gamma sensitivity tables for materials release rows."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_materials_threshold_robustness import load_frame, observed_positive_mask
from scripts.run_materials_discovery_parc_flagship import (
    bootstrap_ci,
    parse_list,
    scs_release_count,
    sha256_file,
    split_blocks,
    write_manifest,
)


def fixed_gamma_evalues(
    frame: pd.DataFrame,
    *,
    score_col: str,
    block_col: str,
    observed_positive: np.ndarray,
    cal_blocks: set[str],
    test_blocks: set[str],
    gamma: float,
) -> tuple[pd.DataFrame, dict]:
    block_series = frame[block_col].astype(str)
    cal_mask = block_series.isin(cal_blocks).to_numpy()
    test_mask = block_series.isin(test_blocks).to_numpy()
    partial_null = ~observed_positive
    cal_null = frame.loc[cal_mask & partial_null, [block_col, score_col]].copy()
    maxima = cal_null.groupby(block_col, sort=False)[score_col].max().astype(float).to_numpy()
    test = frame.loc[test_mask].sort_values(score_col, ascending=False).copy()
    if len(test) == 0 or len(maxima) == 0:
        test["_evalue"] = np.zeros(len(test), dtype=float)
    else:
        maxima_sorted = np.sort(maxima)
        scores = test[score_col].to_numpy(dtype=float)
        exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, scores, side="left")
        p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
        test["_evalue"] = gamma * (np.minimum(1.0, p_block) ** (gamma - 1.0))
    return test, {
        "n_cal_blocks": int(len(cal_blocks)),
        "n_nonempty_null_cal_blocks": int(len(maxima)),
        "block_coverage": float(len(maxima) / len(cal_blocks)) if cal_blocks else 0.0,
        "max_observed_e": float(test["_evalue"].max()) if len(test) else 0.0,
    }


def run_gamma_grid(
    frame: pd.DataFrame,
    *,
    source: str,
    score_col: str,
    block_col: str,
    rho: float,
    alpha: float,
    budgets: list[int],
    seeds: list[int],
    gammas: list[float],
) -> pd.DataFrame:
    rows: list[dict] = []
    work = frame.reset_index(drop=True).copy()
    for seed in seeds:
        observed = observed_positive_mask(work, "stable_exact", score_col, rho, seed)
        cal_blocks, test_blocks = split_blocks(work[block_col].astype(str).tolist(), seed)
        for gamma in gammas:
            test, diag = fixed_gamma_evalues(
                work,
                score_col=score_col,
                block_col=block_col,
                observed_positive=observed,
                cal_blocks=cal_blocks,
                test_blocks=test_blocks,
                gamma=gamma,
            )
            for budget in budgets:
                pool = test.head(budget).copy()
                evalues = pool["_evalue"].to_numpy(dtype=float)
                released, _tau, margin, best_ratio = scs_release_count(evalues, alpha=alpha, budget=budget)
                selected = pool.iloc[np.argsort(evalues)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
                actual_ftr = float((~selected["stable_exact"].astype(bool)).mean()) if released else 0.0
                raw_ftr = float((~pool["stable_exact"].astype(bool)).mean()) if len(pool) else 0.0
                rows.append(
                    {
                        "proposal_source": source,
                        "block_definition": block_col,
                        "rho": rho,
                        "alpha": alpha,
                        "K": budget,
                        "seed": seed,
                        "gamma": gamma,
                        "released": int(released),
                        "actual_FTR": actual_ftr,
                        "raw_topK_actual_FTR": raw_ftr,
                        "max_observed_e": diag["max_observed_e"],
                        "required_e": 1.0 / alpha,
                        "best_mass_ratio": best_ratio,
                        "self_consistency_margin": margin,
                        "block_coverage": diag["block_coverage"],
                        "release_feasible": bool(released > 0),
                    }
                )
    return pd.DataFrame(rows)


def summarize(rows: pd.DataFrame) -> pd.DataFrame:
    out_rows: list[dict] = []
    group_cols = ["proposal_source", "block_definition", "rho", "alpha", "K", "gamma"]
    for key, group in rows.groupby(group_cols, dropna=False):
        row = dict(zip(group_cols, key))
        ftr = group["actual_FTR"].astype(float).to_numpy()
        ci_low, ci_high = bootstrap_ci(ftr)
        row.update(
            {
                "seeds": int(group["seed"].nunique()),
                "non_empty_seeds": int((group["released"].astype(int) > 0).sum()),
                "mean_release": float(group["released"].astype(float).mean()),
                "actual_FTR_mean": float(ftr.mean()),
                "actual_FTR_max": float(ftr.max()),
                "actual_FTR_bootstrap95_low": ci_low,
                "actual_FTR_bootstrap95_high": ci_high,
                "raw_topK_actual_FTR_mean": float(group["raw_topK_actual_FTR"].astype(float).mean()),
                "best_mass_ratio_mean": float(group["best_mass_ratio"].astype(float).mean()),
                "max_observed_e_mean": float(group["max_observed_e"].astype(float).mean()),
                "block_coverage_mean": float(group["block_coverage"].astype(float).mean()),
            }
        )
        row["conclusion"] = (
            "release_low_FTR"
            if row["non_empty_seeds"] >= 18 and row["actual_FTR_mean"] <= row["alpha"]
            else "refusal_or_low_power"
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
    parser.add_argument("--budgets", default="100,300,500,1000")
    parser.add_argument("--seeds", default=",".join(str(i) for i in range(20)))
    parser.add_argument("--gammas", default="0.05,0.10,0.15,0.20,0.25,0.30,0.40,0.50")
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--alpha", type=float, default=0.10)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frame, meta = load_frame(args)
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)
    gammas = parse_list(args.gammas, float)
    seed_rows = []
    for source, score_col in [
        ("cgcnn_ensemble_learned_materials_model", "cgcnn_score"),
        ("alignn_ff_modern_learned_materials_model", "alignn_score"),
    ]:
        seed_rows.append(
            run_gamma_grid(
                frame,
                source=source,
                score_col=score_col,
                block_col="composition_family_pair",
                rho=args.rho,
                alpha=args.alpha,
                budgets=budgets,
                seeds=seeds,
                gammas=gammas,
            )
        )
    seed_table = pd.concat(seed_rows, ignore_index=True)
    summary = summarize(seed_table)
    seed_table.to_csv(out_dir / "table_materials_gamma_sensitivity_seed_rows.csv", index=False)
    summary.to_csv(out_dir / "table_materials_gamma_sensitivity.csv", index=False)
    (out_dir / "materials_gamma_sensitivity_summary.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "inputs": meta,
                "alpha": args.alpha,
                "rho": args.rho,
                "budgets": budgets,
                "gammas": gammas,
                "seeds": seeds,
                "summary_table": str(out_dir / "table_materials_gamma_sensitivity.csv"),
                "seed_table": str(out_dir / "table_materials_gamma_sensitivity_seed_rows.csv"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_manifest(out_dir)


if __name__ == "__main__":
    main()
