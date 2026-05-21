#!/usr/bin/env python3
"""Build candidate-level source-uncertainty overlays for materials queues.

This milestone reconstructs the frozen ALIGNN-FF materials release queues at
alpha=0.10, rho=0.10, K in {300, 500}, then joins them to the completed
alex-mp exact-structure diagnostic.  Formula-only rows are carried as tags but
are never used as the denominator for alex-mp FTR or source-discordance rates.
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
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_materials_discovery_parc_flagship import (
    add_blocks,
    compute_evalues,
    parse_list,
    scs_release_count,
    sha256_file,
    split_blocks,
    write_manifest,
)


DEFAULT_ALEX_MATCHES = (
    REPO_ROOT
    / "outputs/milestones/materials_alex_mp_a1_a2_validation/table_alex_mp_a2_candidate_matches.csv"
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
        raise FileNotFoundError(f"Missing materials overlay inputs: {missing}")

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


def boolean_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame:
        return pd.Series(False, index=frame.index)
    return frame[column].fillna(False).astype(bool)


def reconstruct_queues(
    frame: pd.DataFrame,
    *,
    seeds: list[int],
    budgets: list[int],
    alpha: float,
    rho: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_rows: list[pd.DataFrame] = []
    seed_rows: list[dict] = []
    work = frame.reset_index(drop=True).copy()
    for seed in seeds:
        observed = observed_positive_mask(work, "stable_exact", "alignn_score", rho, seed)
        cal_blocks, test_blocks = split_blocks(work["composition_family_pair"].astype(str).tolist(), seed)
        test, diag = compute_evalues(
            work,
            score_col="alignn_score",
            block_col="composition_family_pair",
            observed_positive=observed,
            cal_blocks=cal_blocks,
            test_blocks=test_blocks,
            alpha=alpha,
        )
        test = test.sort_values("alignn_score", ascending=False).copy()
        for budget in budgets:
            pool = test.head(budget).copy()
            released_n, tau, margin, best_ratio = scs_release_count(
                pool["_evalue"].to_numpy(dtype=float),
                alpha=alpha,
                budget=budget,
            )
            release = (
                pool.iloc[np.argsort(pool["_evalue"].to_numpy(dtype=float))[::-1][:released_n]].copy()
                if released_n
                else pool.iloc[[]].copy()
            )
            raw_topr = pool.head(released_n).copy() if released_n else pool.iloc[[]].copy()
            release_ids = set(release["material_id"].astype(str))
            raw_only = pool[~pool["material_id"].astype(str).isin(release_ids)].copy()
            arm_frames = [
                ("raw_topK_requested_budget", pool),
                ("PARC_release", release),
                ("raw_topR_matched_release_size", raw_topr),
                ("raw_only_rejected_tail", raw_only),
            ]
            for arm, arm_frame in arm_frames:
                out = arm_frame[
                    [
                        "material_id",
                        "formula",
                        "chemical_system",
                        "composition_family_pair",
                        "alignn_score",
                        "alignn_predicted_e_above_hull",
                        "e_hull",
                        "stable_exact",
                        "_evalue",
                    ]
                ].copy()
                out.insert(0, "arm", arm)
                out.insert(0, "K", budget)
                out.insert(0, "alpha", alpha)
                out.insert(0, "rho", rho)
                out.insert(0, "seed", seed)
                out["raw_rank_within_test"] = np.arange(1, len(out) + 1)
                out["released_n_for_seed_budget"] = released_n
                out["required_e"] = 1.0 / alpha
                out["best_mass_ratio"] = best_ratio
                out["self_consistency_margin"] = margin
                out["selection_tau"] = tau
                candidate_rows.append(out)
            seed_rows.append(
                {
                    "seed": seed,
                    "rho": rho,
                    "alpha": alpha,
                    "K": budget,
                    "raw_topK_n": int(len(pool)),
                    "released_n": int(released_n),
                    "raw_only_rejected_tail_n": int(len(raw_only)),
                    "raw_topK_WBM_FTR": float((~pool["stable_exact"].astype(bool)).mean()) if len(pool) else 0.0,
                    "PARC_release_WBM_FTR": float((~release["stable_exact"].astype(bool)).mean()) if len(release) else 0.0,
                    "raw_topR_WBM_FTR": float((~raw_topr["stable_exact"].astype(bool)).mean()) if len(raw_topr) else 0.0,
                    "required_e": 1.0 / alpha,
                    "best_mass_ratio": best_ratio,
                    "self_consistency_margin": margin,
                    "block_coverage": diag["block_coverage"],
                    "n_nonempty_null_cal_blocks": diag["n_nonempty_null_cal_blocks"],
                }
            )
    candidates = pd.concat(candidate_rows, ignore_index=True) if candidate_rows else pd.DataFrame()
    return candidates, pd.DataFrame(seed_rows)


def attach_alex_matches(candidates: pd.DataFrame, alex_matches: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        "material_id",
        "match_confidence",
        "alex_match_count",
        "alex_material_ids",
        "alex_min_e_above_hull",
        "alex_stable_exact",
        "alex_source_files",
        "formula_only_candidate_count",
        "wbm_stable_DFT",
        "wbm_e_above_hull",
    ]
    matches = alex_matches[[col for col in keep_cols if col in alex_matches.columns]].copy()
    out = candidates.merge(matches, on="material_id", how="left")
    out["match_confidence"] = out["match_confidence"].fillna("not_in_alex_mp_A2_candidate_match_table")
    out["included_in_alex_exact_metrics"] = out["match_confidence"].eq("exact_structure_match")
    alex_bool = out["alex_stable_exact"].map(
        lambda value: bool(value) if isinstance(value, (bool, np.bool_)) else (str(value).lower() == "true")
    ).astype("object")
    alex_bool.loc[~out["included_in_alex_exact_metrics"]] = np.nan
    out["alex_stable_exact_bool"] = alex_bool
    out["source_discordant_exact"] = (
        out["included_in_alex_exact_metrics"]
        & out["alex_stable_exact_bool"].notna()
        & (out["stable_exact"].astype(bool) != out["alex_stable_exact_bool"].astype("boolean"))
    )
    alex_hull = pd.to_numeric(out["alex_min_e_above_hull"], errors="coerce")
    wbm_hull = pd.to_numeric(out["e_hull"], errors="coerce")
    out["either_source_near_hull_25meV_exact"] = (
        out["included_in_alex_exact_metrics"] & ((alex_hull.abs() <= 0.025) | (wbm_hull.abs() <= 0.025))
    )
    out["source_uncertain_or_boundary_exact"] = (
        out["source_discordant_exact"].fillna(False) | out["either_source_near_hull_25meV_exact"].fillna(False)
    )
    out["paper_role"] = "candidate_level_source_uncertainty_diagnostic_not_primary_validation"
    return out


def summarize_overlay(candidate_rows: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    group_cols = ["K", "arm"]
    for key, group in candidate_rows.groupby(group_cols, dropna=False):
        k, arm = key
        seed_summaries: list[dict] = []
        for seed, seed_group in group.groupby("seed"):
            exact = seed_group[seed_group["included_in_alex_exact_metrics"].astype(bool)].copy()
            alex_ftr = (
                float((~exact["alex_stable_exact_bool"].astype(bool)).mean()) if len(exact) else math.nan
            )
            discordance = float(exact["source_discordant_exact"].astype(bool).mean()) if len(exact) else math.nan
            seed_summaries.append(
                {
                    "seed": seed,
                    "n_candidates": len(seed_group),
                    "exact_matched_n": len(exact),
                    "formula_only_tag_n": int(seed_group["match_confidence"].eq("formula_only_no_structure_match").sum()),
                    "no_formula_match_n": int(seed_group["match_confidence"].eq("no_formula_match").sum()),
                    "not_in_match_table_n": int(seed_group["match_confidence"].eq("not_in_alex_mp_A2_candidate_match_table").sum()),
                    "WBM_FTR": float((~seed_group["stable_exact"].astype(bool)).mean()) if len(seed_group) else math.nan,
                    "alex_exact_FTR": alex_ftr,
                    "source_discordance_rate_exact": discordance,
                    "source_uncertain_or_boundary_rate_exact": (
                        float(exact["source_uncertain_or_boundary_exact"].astype(bool).mean()) if len(exact) else math.nan
                    ),
                }
            )
        seed_df = pd.DataFrame(seed_summaries)
        rows.append(
            {
                "K": k,
                "arm": arm,
                "n_seeds": int(seed_df["seed"].nunique()),
                "mean_candidates": float(seed_df["n_candidates"].mean()),
                "mean_exact_matched_n": float(seed_df["exact_matched_n"].mean()),
                "mean_exact_match_coverage": float((seed_df["exact_matched_n"] / seed_df["n_candidates"].replace(0, np.nan)).mean()),
                "mean_formula_only_tag_n": float(seed_df["formula_only_tag_n"].mean()),
                "mean_no_formula_match_n": float(seed_df["no_formula_match_n"].mean()),
                "mean_not_in_match_table_n": float(seed_df["not_in_match_table_n"].mean()),
                "mean_WBM_FTR": float(seed_df["WBM_FTR"].mean()),
                "mean_alex_exact_FTR": float(seed_df["alex_exact_FTR"].mean(skipna=True)),
                "mean_source_discordance_rate_exact": float(seed_df["source_discordance_rate_exact"].mean(skipna=True)),
                "mean_source_uncertain_or_boundary_rate_exact": float(seed_df["source_uncertain_or_boundary_rate_exact"].mean(skipna=True)),
                "alex_exact_metrics_denominator": "exact_structure_match_only",
                "formula_only_rows_used_for_FTR": False,
                "paper_role": "diagnostic_only_source_uncertainty_overlay",
            }
        )
    return pd.DataFrame(rows)


def build_lead_contrasts(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for k, group in summary.groupby("K"):
        by_arm = {row["arm"]: row for _, row in group.iterrows()}
        if "PARC_release" not in by_arm or "raw_topK_requested_budget" not in by_arm:
            continue
        parc = by_arm["PARC_release"]
        raw = by_arm["raw_topK_requested_budget"]
        rows.append(
            {
                "K": k,
                "comparison": "PARC_release_vs_raw_topK_requested_budget",
                "PARC_mean_exact_match_coverage": parc["mean_exact_match_coverage"],
                "raw_mean_exact_match_coverage": raw["mean_exact_match_coverage"],
                "PARC_WBM_FTR": parc["mean_WBM_FTR"],
                "raw_WBM_FTR": raw["mean_WBM_FTR"],
                "PARC_alex_exact_FTR": parc["mean_alex_exact_FTR"],
                "raw_alex_exact_FTR": raw["mean_alex_exact_FTR"],
                "PARC_source_discordance_rate_exact": parc["mean_source_discordance_rate_exact"],
                "raw_source_discordance_rate_exact": raw["mean_source_discordance_rate_exact"],
                "interpretation": "candidate_level_overlay_diagnostic_not_independent_validation",
            }
        )
    return pd.DataFrame(rows)


def update_docs(out_dir: Path, summary: pd.DataFrame, contrasts: pd.DataFrame, meta: dict) -> None:
    best_lines = []
    for _, row in contrasts.iterrows():
        best_lines.append(
            f"- K={int(row['K'])}: PARC WBM FTR {row['PARC_WBM_FTR']:.3f} vs raw WBM FTR "
            f"{row['raw_WBM_FTR']:.3f}; PARC alex exact-match FTR {row['PARC_alex_exact_FTR']:.3f} "
            f"vs raw alex exact-match FTR {row['raw_alex_exact_FTR']:.3f}. Exact-match coverage is "
            f"{row['PARC_mean_exact_match_coverage']:.3f} for PARC and {row['raw_mean_exact_match_coverage']:.3f} for raw."
        )
    (out_dir / "MATERIALS_QUEUE_SOURCE_UNCERTAINTY_OVERLAY.md").write_text(
        "# Materials Queue Source-Uncertainty Overlay\n\n"
        "Status: completed candidate-level diagnostic. This milestone reconstructs the "
        "ALIGNN-FF alpha=0.10, rho=0.10, K=300/500 materials queues and joins them to "
        "the alex-mp A2 candidate-match table.\n\n"
        "Claim boundary: diagnostic only. The alex-mp rows are a source-discordance "
        "stress test, not positive independent validation and not prospective materials "
        "discovery. Formula-only matches are retained as tags but excluded from alex-mp "
        "FTR and discordance denominators.\n\n"
        "Lead diagnostic contrasts:\n"
        + "\n".join(best_lines)
        + "\n\nSource hashes:\n"
        + "\n".join(f"- {key}: {value}" for key, value in meta.items())
        + "\n",
        encoding="utf-8",
    )
    (out_dir / "provenance.json").write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wbm-summary", default="/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
    parser.add_argument("--cgcnn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
    parser.add_argument("--alignn-predictions", default="/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
    parser.add_argument("--cgcnn-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--alignn-pred-col", default="e_form_per_atom_alignn_ff")
    parser.add_argument("--alex-matches", default=str(DEFAULT_ALEX_MATCHES))
    parser.add_argument("--out-dir", default="outputs/milestones/materials_queue_source_uncertainty_overlay")
    parser.add_argument("--budgets", default="300,500")
    parser.add_argument("--seeds", default=",".join(str(i) for i in range(20)))
    parser.add_argument("--rho", type=float, default=0.10)
    parser.add_argument("--alpha", type=float, default=0.10)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frame, meta = load_frame(args)
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)
    alex_path = Path(args.alex_matches)
    alex_matches = pd.read_csv(alex_path)

    candidates, seed_rows = reconstruct_queues(frame, seeds=seeds, budgets=budgets, alpha=args.alpha, rho=args.rho)
    candidate_rows = attach_alex_matches(candidates, alex_matches)
    summary = summarize_overlay(candidate_rows)
    contrasts = build_lead_contrasts(summary)
    seed_rows = seed_rows.merge(
        summary[["K", "arm", "mean_exact_match_coverage"]].query("arm == 'PARC_release'").rename(
            columns={"mean_exact_match_coverage": "PARC_mean_exact_match_coverage"}
        )[["K", "PARC_mean_exact_match_coverage"]],
        on="K",
        how="left",
    )

    candidate_rows.to_csv(out_dir / "table_materials_queue_overlay_candidate_rows.csv", index=False)
    summary.to_csv(out_dir / "table_materials_queue_overlay_summary.csv", index=False)
    contrasts.to_csv(out_dir / "table_materials_queue_overlay_lead_contrasts.csv", index=False)
    seed_rows.to_csv(out_dir / "table_materials_queue_reconstruction_seed_rows.csv", index=False)
    policy = pd.DataFrame(
        [
            {
                "rule": "alex_exact_metrics_denominator",
                "setting": "exact_structure_match_only",
                "reason": "formula-only rows are not valid independent label denominators",
            },
            {
                "rule": "paper_role",
                "setting": "diagnostic_only_source_discordance_stress",
                "reason": "alex-mp discordance does not support positive independent validation",
            },
            {
                "rule": "prospective_claim",
                "setting": "forbidden",
                "reason": "no new DFT outcome is used and A3 gates are separate",
            },
        ]
    )
    policy.to_csv(out_dir / "table_materials_queue_overlay_claim_boundary.csv", index=False)

    meta.update(
        {
            "alex_mp_candidate_matches_sha256": sha256_file(alex_path),
            "alex_mp_candidate_matches_artifact": str(alex_path.relative_to(REPO_ROOT) if alex_path.is_absolute() and alex_path.is_relative_to(REPO_ROOT) else alex_path),
            "alpha": args.alpha,
            "rho": args.rho,
            "budgets": budgets,
            "seeds": seeds,
            "status": "completed_candidate_level_source_uncertainty_diagnostic",
        }
    )
    update_docs(out_dir, summary, contrasts, meta)
    write_manifest(out_dir)


if __name__ == "__main__":
    main()
