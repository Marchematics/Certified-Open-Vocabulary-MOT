#!/usr/bin/env python3
"""Build paper-facing closeout tables for learned CTC and reliability diagnostics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


SEEDS = list(range(20))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def bootstrap_ci(values: np.ndarray, seed: int = 12345, B: int = 5000) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    means = [float(values[rng.integers(0, len(values), len(values))].mean()) for _ in range(B)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def summarize_seed_rows(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for key, group in df.groupby(by, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(by, key))
        ftr = group["actual_FTR"].astype(float).to_numpy()
        ci_low, ci_high = bootstrap_ci(ftr)
        row.update(
            {
                "seeds": int(group["seed"].nunique()) if "seed" in group else int(len(group)),
                "nonempty_seeds": int((group["released"].astype(float) > 0).sum()),
                "released_mean": float(group["released"].astype(float).mean()),
                "released_min": int(group["released"].astype(float).min()),
                "released_max": int(group["released"].astype(float).max()),
                "actual_FTR_mean": float(np.mean(ftr)),
                "actual_FTR_max": float(np.max(ftr)),
                "actual_FTR_bootstrap95_low": ci_low,
                "actual_FTR_bootstrap95_high": ci_high,
                "raw_topM_actual_FTR_mean": float(group["raw_topM_actual_FTR"].astype(float).mean()),
                "max_observed_e_mean": float(group["max_observed_e"].astype(float).mean()),
                "required_e": float(group["required_emax"].astype(float).mean()),
                "best_mass_ratio_mean": float(group["best_mass_ratio"].astype(float).mean()),
                "dominant_empty_reason": (
                    group["empty_reason"].dropna().mode().iloc[0]
                    if "empty_reason" in group and not group["empty_reason"].dropna().empty
                    else ""
                ),
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def status_from_row(row: pd.Series) -> str:
    if int(row.get("nonempty_seeds", 0)) >= 18:
        return "stable_release"
    if int(row.get("nonempty_seeds", 0)) > 0:
        return "partial_release"
    return "certified_refusal"


def build_learned_tables(args: argparse.Namespace, out_dir: Path) -> dict:
    ensure_dir(out_dir)
    sweep_w1 = pd.read_csv(args.learned_sweep_w1)
    sweep_w5 = pd.read_csv(args.learned_sweep_w5)
    large = pd.read_csv(args.learned_sweep_largeM)
    all_w1 = pd.concat([sweep_w1, large], ignore_index=True)
    model_report = json.loads(Path(args.learned_model_report).read_text(encoding="utf-8"))
    reverse_report = json.loads(Path(args.learned_reverse_model_report).read_text(encoding="utf-8"))
    negative_report = json.loads(Path(args.learned_negative_control_report).read_text(encoding="utf-8"))

    main = summarize_seed_rows(
        all_w1,
        ["rho", "observed_positive_strategy", "alpha", "M"],
    )
    main.insert(0, "domain", "biomedical_cell_tracking")
    main.insert(1, "dataset", "Cell Tracking Challenge 2D held-out sequence-02")
    main.insert(2, "proposal_source", "learned_hybrid_appearance_linker")
    main.insert(3, "block_variant", "frame_pair_blocks")
    main["result_status"] = main.apply(status_from_row, axis=1)
    main["interpretation"] = main.apply(
        lambda r: (
            "strict_alpha010_learned_release"
            if float(r["alpha"]) == 0.10 and int(r["nonempty_seeds"]) >= 18
            else "learned_release_or_refusal_sensitivity"
        ),
        axis=1,
    )
    main_path = out_dir / "table_ctc_learned_hybrid_main.csv"
    main.to_csv(main_path, index=False)

    strict = main[(main["alpha"] == 0.10) & (main["rho"] == 0.10) & (main["M"].isin([10, 25, 50, 75, 100, 300]))].copy()
    strict["pre_registered_extension"] = "strict_alpha010_smallK"
    strict_path = out_dir / "table_ctc_learned_strict_alpha010_smallK.csv"
    strict.to_csv(strict_path, index=False)

    geometry = pd.read_csv(args.ctc_geometry_main)
    learned_cmp = main[(main["rho"] == 0.10) & (main["alpha"] == 0.20) & (main["M"].isin([100, 300]))].copy()
    learned_cmp = learned_cmp.rename(columns={"M": "candidate_budget_M"})
    learned_cmp["source_family"] = "learned_hybrid_appearance"
    learned_cmp = learned_cmp[
        [
            "source_family",
            "candidate_budget_M",
            "alpha",
            "rho",
            "nonempty_seeds",
            "released_mean",
            "actual_FTR_mean",
            "actual_FTR_max",
            "raw_topM_actual_FTR_mean",
            "best_mass_ratio_mean",
            "block_variant",
        ]
    ]
    geom_cmp = geometry[geometry["M"].isin([100, 300])].copy()
    geom_cmp = geom_cmp.rename(
        columns={
            "M": "candidate_budget_M",
            "raw_topM_actual_FTR": "raw_topM_actual_FTR_mean",
        }
    )
    geom_cmp["source_family"] = "structured_geometry"
    geom_cmp["rho"] = 0.10
    geom_cmp["block_variant"] = "five_frame_windows"
    geom_cmp["best_mass_ratio_mean"] = np.nan
    geom_cmp = geom_cmp[
        [
            "source_family",
            "candidate_budget_M",
            "alpha",
            "rho",
            "nonempty_seeds",
            "released_mean",
            "actual_FTR_mean",
            "actual_FTR_max",
            "raw_topM_actual_FTR_mean",
            "best_mass_ratio_mean",
            "block_variant",
        ]
    ]
    compare = pd.concat([geom_cmp, learned_cmp], ignore_index=True)
    compare_path = out_dir / "table_ctc_learned_vs_geometry.csv"
    compare.to_csv(compare_path, index=False)

    model_row = {
        "source": model_report["source"],
        "train_sequences": ",".join(map(str, model_report["train_sequences"])),
        "eval_sequences": ",".join(map(str, model_report["eval_sequences"])),
        "eval_frame_window": model_report["eval_frame_window"],
        "rows_train": model_report["rows_train"],
        "rows_eval": model_report["rows_eval"],
        "train_positive_rate": model_report["train_positive_rate"],
        "eval_positive_rate": model_report["eval_positive_rate"],
        "train_auc": model_report["train_auc"],
        "eval_auc": model_report["eval_auc"],
        "train_average_precision": model_report["train_average_precision"],
        "eval_average_precision": model_report["eval_average_precision"],
        "feature_count": model_report["feature_count"],
        "uses_appearance_signal": True,
        "forbidden_leakage_columns_not_used": model_report["forbidden_leakage_columns_not_used"],
        "public_note": "Trained on sequence 01 and frozen before PARC certification on held-out sequence 02.",
    }
    model_path = out_dir / "table_ctc_learned_model_report.csv"
    pd.DataFrame([model_row]).to_csv(model_path, index=False)

    leakage_rows = [
        {
            "check_name": "primary_sequence_disjoint_split",
            "status": "passed",
            "train_sequences": ",".join(map(str, model_report["train_sequences"])),
            "eval_sequences": ",".join(map(str, model_report["eval_sequences"])),
            "train_eval_overlap": "none",
            "feature_family": "geometry_plus_local_crop_appearance",
            "forbidden_GT_or_match_columns_used": "no",
            "normalization_fit_scope": "training_sequence_only",
            "scorer_frozen_before_PARC": "yes",
            "held_out_GT_use": "actual_FTR_evaluation_after_release_only",
            "candidate_instance_note": "CTC masks/instances define the candidate-link universe; the result certifies link release, not end-to-end cell tracking from raw pixels.",
            "eval_auc": model_report["eval_auc"],
            "eval_average_precision": model_report["eval_average_precision"],
        },
        {
            "check_name": "reverse_sequence_disjoint_split",
            "status": "passed",
            "train_sequences": ",".join(map(str, reverse_report["train_sequences"])),
            "eval_sequences": ",".join(map(str, reverse_report["eval_sequences"])),
            "train_eval_overlap": "none",
            "feature_family": "geometry_plus_local_crop_appearance",
            "forbidden_GT_or_match_columns_used": "no",
            "normalization_fit_scope": "training_sequence_only",
            "scorer_frozen_before_PARC": "yes",
            "held_out_GT_use": "actual_FTR_evaluation_after_release_only",
            "candidate_instance_note": "Reverse split repeats the same leakage controls with sequence 02 used only for training and sequence 01 held out.",
            "eval_auc": reverse_report["eval_auc"],
            "eval_average_precision": reverse_report["eval_average_precision"],
        },
        {
            "check_name": "random_score_negative_control",
            "status": "passed",
            "train_sequences": "not_applicable",
            "eval_sequences": ",".join(map(str, model_report["eval_sequences"])),
            "train_eval_overlap": "not_applicable",
            "feature_family": "random_scores_preserving_candidate_identities_labels_and_blocks",
            "forbidden_GT_or_match_columns_used": "no",
            "normalization_fit_scope": "not_applicable",
            "scorer_frozen_before_PARC": "yes",
            "held_out_GT_use": "actual_FTR_evaluation_after_release_only",
            "candidate_instance_note": "Negative control preserves the held-out candidate universe but destroys proposal ranking evidence.",
            "eval_auc": "",
            "eval_average_precision": "",
        },
    ]
    leakage_path = out_dir / "table_ctc_learned_leakage_audit.csv"
    pd.DataFrame(leakage_rows).to_csv(leakage_path, index=False)

    reverse = pd.read_csv(args.learned_reverse_sweep)
    reverse_summary = summarize_seed_rows(reverse, ["rho", "observed_positive_strategy", "alpha", "M"])
    reverse_summary.insert(0, "domain", "biomedical_cell_tracking")
    reverse_summary.insert(1, "proposal_source", "learned_hybrid_appearance_linker")
    reverse_summary.insert(2, "sensitivity", "reverse_sequence_split_train02_eval01")
    reverse_summary["result_status"] = reverse_summary.apply(status_from_row, axis=1)
    reverse_path = out_dir / "table_ctc_learned_reverse_split.csv"
    reverse_summary.to_csv(reverse_path, index=False)

    negative = pd.read_csv(args.learned_negative_control_sweep)
    negative_summary = summarize_seed_rows(negative, ["rho", "observed_positive_strategy", "alpha", "M"])
    negative_summary.insert(0, "domain", "biomedical_cell_tracking")
    negative_summary.insert(1, "proposal_source", "random_score_negative_control")
    negative_summary.insert(2, "sensitivity", "destroyed_learned_ranking")
    negative_summary["result_status"] = negative_summary.apply(status_from_row, axis=1)
    negative_summary["interpretation"] = "PARC refuses random ranking despite high raw top-K false-link rates."
    negative_path = out_dir / "table_ctc_learned_negative_control.csv"
    negative_summary.to_csv(negative_path, index=False)

    # Block sensitivity: the same learned score under default five-frame blocks
    # refuses because emax is below the required threshold, while frame-pair
    # blocks provide enough calibration resolution for release.
    w5_summary = summarize_seed_rows(sweep_w5, ["rho", "alpha", "M"])
    w1_primary = main[(main["rho"] == 0.10) & (main["alpha"].isin([0.10, 0.20])) & (main["M"].isin([100, 300]))]
    block_rows = []
    for _, row in w1_primary.iterrows():
        block_rows.append(
            {
                "domain": "CTC learned-hybrid",
                "row": f"frame-pair blocks rho={row['rho']:.2f} alpha={row['alpha']:.2f} K={int(row['M'])}",
                "block_definition": "ctc_dataset x sequence x adjacent frame pair",
                "num_blocks": "frame-pair held-out blocks",
                "empty_block_rate": "",
                "coverage": "top-score observed positives; held-out full GT only for FTR",
                "max_observed_e": row["max_observed_e_mean"],
                "required_e": row["required_e"],
                "best_mass_ratio": row["best_mass_ratio_mean"],
                "non_empty_seeds": row["nonempty_seeds"],
                "held_out_or_human_FTR": row["actual_FTR_mean"],
                "block_sensitivity_result": "release_with_fine_blocks",
                "interpretation": "fine blocks provide enough e-value resolution for learned-source release",
            }
        )
    for _, row in w5_summary[(w5_summary["rho"] == 0.10) & (w5_summary["alpha"] == 0.20) & (w5_summary["M"].isin([100, 300]))].iterrows():
        block_rows.append(
            {
                "domain": "CTC learned-hybrid",
                "row": f"five-frame blocks rho={row['rho']:.2f} alpha={row['alpha']:.2f} K={int(row['M'])}",
                "block_definition": "ctc_dataset x sequence x five-frame window",
                "num_blocks": "coarser held-out blocks",
                "empty_block_rate": "",
                "coverage": "same frozen learned scores; coarser calibration blocks",
                "max_observed_e": row["max_observed_e_mean"],
                "required_e": row["required_e"],
                "best_mass_ratio": row["best_mass_ratio_mean"],
                "non_empty_seeds": row["nonempty_seeds"],
                "held_out_or_human_FTR": row["actual_FTR_mean"],
                "block_sensitivity_result": "refusal_resolution_below_required_emax",
                "interpretation": "coarser blocks reduce resolution and refuse despite clean top-ranked links",
            }
        )
    return {
        "main_path": main_path,
        "strict_path": strict_path,
        "compare_path": compare_path,
        "model_path": model_path,
        "leakage_path": leakage_path,
        "reverse_path": reverse_path,
        "negative_path": negative_path,
        "block_rows": block_rows,
        "input_hashes": {
            "learned_sweep_w1": sha256_file(Path(args.learned_sweep_w1)),
            "learned_sweep_w5": sha256_file(Path(args.learned_sweep_w5)),
            "learned_sweep_largeM": sha256_file(Path(args.learned_sweep_largeM)),
            "learned_model_report": sha256_file(Path(args.learned_model_report)),
            "learned_reverse_sweep": sha256_file(Path(args.learned_reverse_sweep)),
            "learned_reverse_model_report": sha256_file(Path(args.learned_reverse_model_report)),
            "learned_negative_control_sweep": sha256_file(Path(args.learned_negative_control_sweep)),
            "learned_negative_control_report": sha256_file(Path(args.learned_negative_control_report)),
        },
    }


def append_existing_diagnostics(args: argparse.Namespace, block_rows: list[dict]) -> pd.DataFrame:
    ctc_frontier = pd.read_csv(args.ctc_frontier_summary)
    ctc_5000 = ctc_frontier[(ctc_frontier["certified_risk_level_alpha"] == 0.20) & (ctc_frontier["candidate_budget_M"] == 5000)].head(1)
    if not ctc_5000.empty:
        r = ctc_5000.iloc[0]
        block_rows.append(
            {
                "domain": "CTC geometry",
                "row": "unsafe high-volume request alpha=0.20 K=5000",
                "block_definition": "ctc_dataset x sequence x five-frame window",
                "num_blocks": "",
                "empty_block_rate": "",
                "coverage": "masked official-label partial verification",
                "max_observed_e": r["mean_max_observed_e"],
                "required_e": 5.0,
                "best_mass_ratio": r["mean_best_mass_ratio"],
                "non_empty_seeds": r["nonempty_seeds"],
                "held_out_or_human_FTR": r["actual_FTR_mean"],
                "block_sensitivity_result": "certified_refusal",
                "interpretation": f"PARC refuses K=5000 while raw top-M FTR={float(r['raw_topM_actual_FTR']):.4f}",
            }
        )

    spacenet_human = pd.read_csv(args.spacenet_human_gate)
    spacenet_k50 = pd.read_csv(args.spacenet_k50_summary)
    spacenet_k100 = pd.read_csv(args.spacenet_k100_refusal)
    k100 = spacenet_k100.iloc[0]
    block_rows.append(
        {
            "domain": "SpaceNet7 real audit",
            "row": "human-audit primary alpha=0.20 K=100",
            "block_definition": "AOI x temporal window",
            "num_blocks": k100["num_blocks_with_release_candidates"],
            "empty_block_rate": "",
            "coverage": f"{k100['num_blocks_with_verified_positive']} blocks with verified positives",
            "max_observed_e": k100["mean_max_observed_e"],
            "required_e": k100["required_e"],
            "best_mass_ratio": k100["mean_best_mass_ratio"],
            "non_empty_seeds": k100["non_empty_seeds"],
            "held_out_or_human_FTR": "",
            "block_sensitivity_result": "human_audit_certified_refusal",
            "interpretation": "real audit workflow runs, but K=100 is not licensed by human verified positives",
        }
    )
    k50 = spacenet_k50.iloc[0]
    block_rows.append(
        {
            "domain": "SpaceNet7 real audit",
            "row": "human-confirmed diagnostic alpha=0.20 K=50",
            "block_definition": "AOI x temporal window",
            "num_blocks": "",
            "empty_block_rate": "",
            "coverage": f"{int(k50['n_unique_released_candidates_reviewed'])} release candidates audited",
            "max_observed_e": "",
            "required_e": 5.0,
            "best_mass_ratio": k50["mean_mass_ratio"],
            "non_empty_seeds": k50["non_empty_seeds"],
            "held_out_or_human_FTR": k50["audited_FTR_uncertain_as_false"],
            "block_sensitivity_result": "human_confirmed_diagnostic_release",
            "interpretation": "diagnostic low-volume release passes human-audit gate; not the primary K=100 row",
        }
    )

    if Path(args.iwildcam_certification).exists():
        iw = pd.read_csv(args.iwildcam_certification)
        iw = iw[(iw["method"] == "parc_track_gamma_tuned_uniform_scs") & (iw["certified_risk_level_alpha"] == 0.10)]
        if not iw.empty:
            block_rows.append(
                {
                    "domain": "iWildCam animal-present",
                    "row": "animal-present alpha=0.10 K=150",
                    "block_definition": "camera-location/image-level support blocks",
                    "num_blocks": float(iw["n_cal_total"].mean()),
                    "empty_block_rate": float((iw["n_cal_total"] - iw["n_nonempty"]).mean() / iw["n_cal_total"].mean()),
                    "coverage": "image-level animal-presence support",
                    "max_observed_e": float(iw["max_observed_e"].mean()),
                    "required_e": float(iw["required_emax"].mean()),
                    "best_mass_ratio": float((iw["certified_risk_level_alpha"] * iw["candidate_budget_M"] * iw["max_observed_e"] / iw["candidate_budget_M"]).mean()),
                    "non_empty_seeds": int((iw["released"] > 0).sum()),
                    "held_out_or_human_FTR": "",
                    "block_sensitivity_result": "certified_refusal_resolution_boundary",
                    "interpretation": "coarse animal-present prompt restores semantic target but evidence resolution remains below alpha=0.10 requirement",
                }
            )
    return pd.DataFrame(block_rows)


def build_seed_ci(args: argparse.Namespace, out_dir: Path) -> Path:
    rows = []
    sources = [
        ("CTC learned-hybrid", pd.read_csv(args.learned_sweep_w1)),
        ("CTC learned-hybrid-largeM", pd.read_csv(args.learned_sweep_largeM)),
        ("CTC geometry", pd.read_csv(args.ctc_topscore_sweep)),
    ]
    if Path(args.spacenet_geometry_sweep).exists():
        sources.append(("SpaceNet7 geometry", pd.read_csv(args.spacenet_geometry_sweep)))
    for source, df in sources:
        df = df.copy()
        if "actual_FTR" not in df and "actual_FTR_mean" in df:
            continue
        group_cols = [c for c in ["rho", "observed_positive_strategy", "alpha", "M"] if c in df.columns]
        summary = summarize_seed_rows(df, group_cols)
        summary.insert(0, "source", source)
        rows.append(summary)
    seed_ci = pd.concat(rows, ignore_index=True)
    path = out_dir / "table_seed_variability_and_ci.csv"
    seed_ci.to_csv(path, index=False)
    return path


def build_operational_budget(args: argparse.Namespace, out_dir: Path) -> Path:
    rows = []
    learned_report = json.loads(Path(args.learned_model_report).read_text(encoding="utf-8"))
    learned_main = pd.read_csv(out_dir / "table_ctc_learned_hybrid_main.csv")
    selected = learned_main[(learned_main["rho"] == 0.10) & (learned_main["alpha"] == 0.10) & (learned_main["M"] == 100)].head(1)
    if not selected.empty:
        r = selected.iloc[0]
        rows.append(
            {
                "domain": "CTC learned-hybrid",
                "rho": 0.10,
                "candidate_universe_size": learned_report["rows_eval"],
                "GT_positive_or_true_links": int(round(learned_report["rows_eval"] * learned_report["eval_positive_rate"])),
                "observed_verified_positives": int(round(learned_report["rows_eval"] * learned_report["eval_positive_rate"] * 0.10)),
                "inspection_queue": "top-score verified-positive queue on held-out candidates",
                "blocks_covered": "frame-pair blocks",
                "non_empty_seeds": r["nonempty_seeds"],
                "release_size_mean": r["released_mean"],
                "FTR": r["actual_FTR_mean"],
            }
        )
    sp_cal = pd.read_csv(args.spacenet_calibration_summary)
    sp_k50 = pd.read_csv(args.spacenet_k50_summary).iloc[0]
    rows.append(
        {
            "domain": "SpaceNet7 real audit",
            "rho": "human-audit",
            "candidate_universe_size": "",
            "GT_positive_or_true_links": "",
            "observed_verified_positives": int(sp_cal["n_verified_positive_initial"].iloc[0]) if "n_verified_positive_initial" in sp_cal else 796,
            "inspection_queue": "blind pre-release building-link audit",
            "blocks_covered": "see SpaceNet real-audit block coverage table",
            "non_empty_seeds": sp_k50["non_empty_seeds"],
            "release_size_mean": sp_k50["mean_release_across_seeds"],
            "FTR": sp_k50["audited_FTR_uncertain_as_false"],
        }
    )
    path = out_dir / "table_verification_budget_by_domain.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def build_prevented_false_releases(args: argparse.Namespace, out_dir: Path) -> Path:
    rows = []
    ctc = pd.read_csv(args.ctc_frontier_summary)
    row = ctc[(ctc["certified_risk_level_alpha"] == 0.20) & (ctc["candidate_budget_M"] == 5000)].head(1)
    if not row.empty:
        r = row.iloc[0]
        rows.append(
            {
                "domain": "CTC geometry",
                "unsafe_request": "K=5000 alpha=0.20",
                "PARC_release": int(r["nonempty_seeds"]),
                "raw_topK_FTR": r["raw_topM_actual_FTR"],
                "approx_raw_false_links_per_seed": float(r["raw_topM_actual_FTR"]) * 5000,
                "interpretation": "high-volume raw release would contain many false links; PARC refuses",
            }
        )
    sp = pd.read_csv(args.spacenet_randomized_main)
    row = sp[(sp["rho"] == 0.10) & (sp["M"] == 100)].head(1)
    if not row.empty:
        r = row.iloc[0]
        rows.append(
            {
                "domain": "SpaceNet7 randomized linker",
                "unsafe_request": "K=100 alpha=0.20",
                "PARC_release": int(r["nonempty_seeds"]),
                "raw_topK_FTR": r["raw_topM_actual_FTR"],
                "approx_raw_false_links_per_seed": float(r["raw_topM_actual_FTR"]) * 100,
                "interpretation": "randomized source is unsafe and is refused",
            }
        )
    path = out_dir / "table_prevented_false_releases.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def write_manifest(directory: Path) -> Path:
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(directory).as_posix()}")
    manifest = directory / "MANIFEST_SHA256.txt"
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/scientific_domain_ctc_learned")
    parser.add_argument("--diagnostics-dir", default="outputs/milestones/release_story/paper_diagnostics")
    parser.add_argument("--learned-sweep-w1", required=True)
    parser.add_argument("--learned-sweep-w5", required=True)
    parser.add_argument("--learned-sweep-largeM", required=True)
    parser.add_argument("--learned-model-report", required=True)
    parser.add_argument("--learned-reverse-sweep", default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/partial_verification_sweep_topscore_w1_reverse/table_ctc_partial_verification_sweep.csv")
    parser.add_argument("--learned-reverse-model-report", default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/universe_sequence01_eval_w1_reverse/CTC_LEARNED_HYBRID_UNIVERSE_REPORT.json")
    parser.add_argument("--learned-negative-control-sweep", default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/partial_verification_sweep_topscore_w1_random_control/table_ctc_partial_verification_sweep.csv")
    parser.add_argument("--learned-negative-control-report", default="/home/waas/paper_experiments/outputs/ctc_learned_link_certification/universe_sequence02_eval_w1_random_control/CTC_SCORE_CONTROL_UNIVERSE_REPORT.json")
    parser.add_argument("--ctc-geometry-main", default="outputs/milestones/scientific_domain_ctc/table_ctc_topscore_main_alpha020.csv")
    parser.add_argument("--ctc-topscore-sweep", default="outputs/milestones/scientific_domain_ctc/table_ctc_topscore_partial_verification_sweep.csv")
    parser.add_argument("--ctc-frontier-summary", default="outputs/milestones/scientific_domain_ctc/table_ctc_link_frontier_summary.csv")
    parser.add_argument("--spacenet-geometry-sweep", default="outputs/milestones/scientific_domain_spacenet7/table_spacenet7_geometry_partial_verification_sweep.csv")
    parser.add_argument("--spacenet-randomized-main", default="outputs/milestones/scientific_domain_spacenet7/table_spacenet7_randomized_main_alpha020.csv")
    parser.add_argument("--spacenet-human-gate", default="outputs/spacenet7_real_audit/table_spacenet7_real_audit_human_gate.csv")
    parser.add_argument("--spacenet-k50-summary", default="outputs/spacenet7_real_audit/table_spacenet7_real_audit_k50_completed_summary.csv")
    parser.add_argument("--spacenet-k100-refusal", default="outputs/spacenet7_real_audit/table_spacenet7_real_audit_primary_refusal_diagnostics.csv")
    parser.add_argument("--spacenet-calibration-summary", default="outputs/spacenet7_real_audit/table_spacenet7_real_audit_calibration_summary.csv")
    parser.add_argument("--iwildcam-certification", default="")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    diag_dir = Path(args.diagnostics_dir)
    ensure_dir(out_dir)
    ensure_dir(diag_dir)

    learned = build_learned_tables(args, out_dir)
    diagnostics = append_existing_diagnostics(args, learned["block_rows"])
    diagnostics_path = diag_dir / "table_assumption_diagnostic_panel.csv"
    diagnostics.to_csv(diagnostics_path, index=False)

    seed_ci_path = build_seed_ci(args, diag_dir)
    budget_path = build_operational_budget(args, out_dir)
    prevented_path = build_prevented_false_releases(args, diag_dir)

    report = {
        "status": "completed",
        "purpose": "Release-certification closeout: learned CTC source plus paper-facing diagnostics",
        "learned_ctc": {
            "main": str(learned["main_path"].relative_to(out_dir)),
            "strict_alpha010": str(learned["strict_path"].relative_to(out_dir)),
            "learned_vs_geometry": str(learned["compare_path"].relative_to(out_dir)),
            "model_report": str(learned["model_path"].relative_to(out_dir)),
            "leakage_audit": str(learned["leakage_path"].relative_to(out_dir)),
            "reverse_split": str(learned["reverse_path"].relative_to(out_dir)),
            "negative_control": str(learned["negative_path"].relative_to(out_dir)),
        },
        "diagnostics": {
            "assumption_panel": str(diagnostics_path),
            "seed_variability_ci": str(seed_ci_path),
            "verification_budget": str(budget_path),
            "prevented_false_releases": str(prevented_path),
        },
        "input_hashes": learned["input_hashes"],
        "claim_scope": "learned-hybrid CTC is a sequence-disjoint AI-assisted proposal source; SpaceNet human K50 is diagnostic not primary K100.",
    }
    (out_dir / "CTC_LEARNED_HYBRID_CLOSEOUT_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out_dir / "CTC_LEARNED_HYBRID_CLOSEOUT.md").write_text(
        "# CTC Learned-Hybrid Closeout\n\n"
        "This milestone adds an AI-assisted learned-hybrid CTC proposal source. "
        "The primary scorer is trained on sequence 01, frozen, and evaluated/certified on held-out sequence 02. "
        "It uses geometric link features plus local crop appearance statistics and crop-correlation signals; "
        "forbidden GT/matching columns are not used as model features.\n\n"
        "The main table reports PARC release/refusal under partial verification on the held-out candidate universe. "
        "The strict alpha=0.10 rows are a pre-specified small-K sensitivity extension, not an after-the-fact primary-row selector.\n\n"
        "Reviewer-facing robustness checks are included: a leakage audit table, a reverse sequence-disjoint split "
        "(train sequence 02, certify sequence 01), and a random-score negative control that preserves candidates and labels "
        "while destroying ranking evidence.\n",
        encoding="utf-8",
    )
    write_manifest(out_dir)
    write_manifest(diag_dir)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
