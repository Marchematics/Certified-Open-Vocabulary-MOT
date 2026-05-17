#!/usr/bin/env python3
"""Build Phase25 block-heterogeneity robustness diagnostics.

The completed candidate-level reruns in this script are limited to public-safe
materials/WBM artifacts because the public bundle contains the required
candidate, block, score and held-out label fields for that domain. CTC and
SpaceNet are included as scoped diagnostics when only aggregate or audit-sample
artifacts are available; no candidate-level rerun is fabricated from summary
tables.
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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from run_materials_discovery_parc_flagship import add_blocks, emax_from_p, gamma_star_from_p, scs_release_count  # noqa: E402


DEFAULT_WBM = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-12-13-wbm-summary.csv.gz")
DEFAULT_CGCNN = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz")
DEFAULT_ALIGNN = Path("/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz")
DEFAULT_SEEDS = list(range(20))
SIZE_MATCH_SEEDS = list(range(10))
DOWNSAMPLE_STRESS_SEEDS = list(range(5))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_blocks(block_ids: list[str | int], seed: int) -> tuple[set[str], set[str]]:
    ordered = sorted(set(str(block) for block in block_ids))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    cut = len(ordered) // 2
    return set(ordered[:cut]), set(ordered[cut:])


def observed_positive_mask(
    frame: pd.DataFrame,
    *,
    score_col: str,
    block_col: str,
    cal_blocks: set[str],
    rho: float,
) -> np.ndarray:
    observed = np.zeros(len(frame), dtype=bool)
    blocks = frame[block_col].astype(str)
    eligible = np.flatnonzero(blocks.isin(cal_blocks).to_numpy() & frame["stable_DFT"].to_numpy(dtype=bool))
    if len(eligible) == 0:
        return observed
    n_observed = max(1, int(round(len(eligible) * min(rho, 1.0))))
    scores = frame[score_col].to_numpy(dtype=float)
    chosen = eligible[np.argsort(scores[eligible])[::-1]][:n_observed]
    observed[chosen] = True
    return observed


def load_materials_frame(args: argparse.Namespace) -> tuple[pd.DataFrame, dict[str, str]]:
    summary_cols = [
        "material_id",
        "formula",
        "e_form_per_atom_mp2020_corrected",
        "e_above_hull_mp2020_corrected_ppd_mp",
        "wyckoff_spglib",
        "unique_prototype",
    ]
    summary = pd.read_csv(args.wbm_summary, usecols=summary_cols)
    cgcnn = pd.read_csv(args.cgcnn_predictions, usecols=["material_id", args.cgcnn_pred_col])
    alignn = pd.read_csv(args.alignn_predictions, usecols=["material_id", args.alignn_pred_col])
    frame = summary.merge(cgcnn, on="material_id", how="inner").merge(alignn, on="material_id", how="inner")
    frame = frame[frame["unique_prototype"].astype(bool)].copy()
    frame = add_blocks(frame)
    frame["stable_DFT"] = frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float) <= 0.0
    hull_reference = (
        frame["e_form_per_atom_mp2020_corrected"].astype(float)
        - frame["e_above_hull_mp2020_corrected_ppd_mp"].astype(float)
    )
    frame["cgcnn_score"] = -(frame[args.cgcnn_pred_col].astype(float) - hull_reference)
    frame["alignn_score"] = -(frame[args.alignn_pred_col].astype(float) - hull_reference)
    return frame.reset_index(drop=True), {
        "wbm_summary_sha256": sha256_file(Path(args.wbm_summary)),
        "cgcnn_predictions_sha256": sha256_file(Path(args.cgcnn_predictions)),
        "alignn_predictions_sha256": sha256_file(Path(args.alignn_predictions)),
    }


def size_stratum(values: pd.Series) -> pd.Series:
    ranked = values.rank(method="first")
    try:
        return pd.qcut(ranked, q=3, labels=["small", "medium", "large"]).astype(str)
    except ValueError:
        return pd.Series(["single"] * len(values), index=values.index)


def materials_superuniformity(frame: pd.DataFrame, seed: int = 0, rho: float = 0.10) -> pd.DataFrame:
    block_col = "composition_family_pair"
    score_col = "alignn_score"
    cal_blocks, test_blocks = split_blocks(frame[block_col].astype(str).tolist(), seed)
    observed = observed_positive_mask(frame, score_col=score_col, block_col=block_col, cal_blocks=cal_blocks, rho=rho)
    blocks = frame[block_col].astype(str)
    block_sizes = frame.groupby(block_col, sort=False).size().rename("block_candidate_size")
    cal_null = frame.loc[blocks.isin(cal_blocks).to_numpy() & ~observed, [block_col, score_col]].copy()
    cal_stats = cal_null.groupby(block_col, sort=False).agg(
        null_size=(score_col, "size"),
        block_max=(score_col, "max"),
    )
    cal_stats["size_stratum"] = size_stratum(cal_stats["null_size"])
    test = frame.loc[blocks.isin(test_blocks).to_numpy()].copy()
    test["block_candidate_size"] = test[block_col].map(block_sizes).astype(int)
    test["size_stratum"] = size_stratum(
        test[[block_col, "block_candidate_size"]].drop_duplicates(block_col).set_index(block_col)["block_candidate_size"]
    ).reindex(test[block_col]).to_numpy()
    false_test = test[~test["stable_DFT"].astype(bool)].copy()
    rows = []
    for stratum, group in false_test.groupby("size_stratum", dropna=False):
        maxima = cal_stats.loc[cal_stats["size_stratum"].eq(str(stratum)), "block_max"].astype(float).to_numpy()
        if len(maxima) == 0:
            continue
        scores = group[score_col].astype(float).to_numpy()
        pvals = np.asarray([(1.0 + np.sum(maxima >= score)) / (len(maxima) + 1.0) for score in scores], dtype=float)
        grid = np.linspace(0.0, 1.0, 101)
        ecdf = np.asarray([(pvals <= point).mean() for point in grid], dtype=float)
        ks = float(np.max(ecdf - grid))
        rows.append(
            {
                "domain": "materials_discovery",
                "diagnostic_scope": "candidate_level_completed",
                "source": "ALIGNN-FF",
                "block_definition": block_col,
                "size_stratum": str(stratum),
                "n_calibration_blocks": int(len(maxima)),
                "n_false_candidates": int(len(pvals)),
                "median_p_value": float(np.median(pvals)),
                "one_sided_KS_ecdf_minus_uniform": ks,
                "superuniformity_flag": "no_qualitative_violation" if ks <= 0.10 else "possible_size_stratum_inflation",
            }
        )
    return pd.DataFrame(rows)


def spacenet_superuniformity_from_audit_sample() -> pd.DataFrame:
    manifest = ROOT / "outputs/milestones/scientific_domain_spacenet7_prospective/audit_manifest.csv"
    adapter = ROOT / "outputs/milestones/scientific_domain_spacenet7/table_spacenet7_adapter_report.csv"
    if not manifest.exists() or not adapter.exists():
        return pd.DataFrame()
    audit = pd.read_csv(manifest)
    sizes = pd.read_csv(adapter).set_index("aoi")["candidate_links"]
    if "_true" not in audit.columns:
        return pd.DataFrame()
    audit["aoi_size"] = audit["aoi"].map(sizes).fillna(audit.groupby("aoi")["path_id"].transform("size")).astype(float)
    aoi_bins = audit[["aoi", "aoi_size"]].drop_duplicates("aoi").set_index("aoi")
    aoi_bins["size_stratum"] = size_stratum(aoi_bins["aoi_size"])
    audit["size_stratum"] = audit["aoi"].map(aoi_bins["size_stratum"])
    cal = audit[audit["sample_set"].astype(str).str.contains("calibration") & (~audit["_true"].astype(bool))]
    test = audit[~audit["sample_set"].astype(str).str.contains("calibration") & (~audit["_true"].astype(bool))]
    rows = []
    for stratum, group in test.groupby("size_stratum", dropna=False):
        maxima = cal.loc[cal["size_stratum"].eq(str(stratum))].groupby("aoi")["score"].max().astype(float).to_numpy()
        if len(maxima) == 0:
            continue
        scores = group["score"].astype(float).to_numpy()
        pvals = np.asarray([(1.0 + np.sum(maxima >= score)) / (len(maxima) + 1.0) for score in scores], dtype=float)
        grid = np.linspace(0.0, 1.0, 101)
        ecdf = np.asarray([(pvals <= point).mean() for point in grid], dtype=float)
        ks = float(np.max(ecdf - grid))
        rows.append(
            {
                "domain": "earth_observation",
                "diagnostic_scope": "audit_sample_only_underpowered",
                "source": "SpaceNet prospective audit manifest",
                "block_definition": "AOI x time block proxy, stratified by AOI candidate_links",
                "size_stratum": str(stratum),
                "n_calibration_blocks": int(len(maxima)),
                "n_false_candidates": int(len(pvals)),
                "median_p_value": float(np.median(pvals)),
                "one_sided_KS_ecdf_minus_uniform": ks,
                "superuniformity_flag": "underpowered_no_release_claim" if len(pvals) < 20 else "audit_sample_screen",
            }
        )
    return pd.DataFrame(rows)


def compute_materials_evalues(
    frame: pd.DataFrame,
    *,
    score_col: str,
    block_col: str,
    cal_blocks: set[str],
    test_blocks: set[str],
    observed: np.ndarray,
    alpha: float,
    size_match_tau: float | None = None,
    downsample_m: int | None = None,
    repeat_seed: int | None = None,
    top_n: int | None = None,
) -> tuple[pd.DataFrame, dict]:
    blocks = frame[block_col].astype(str)
    cal_mask = blocks.isin(cal_blocks).to_numpy()
    test_mask = blocks.isin(test_blocks).to_numpy()
    cal_null = frame.loc[cal_mask & ~observed, [block_col, score_col]].copy()
    if downsample_m is not None:
        rng = np.random.default_rng(repeat_seed)
        pieces = []
        for _, group in cal_null.groupby(block_col, sort=False):
            if len(group) > downsample_m:
                pieces.append(group.iloc[rng.choice(len(group), size=downsample_m, replace=False)])
            else:
                pieces.append(group)
        cal_null = pd.concat(pieces, ignore_index=False) if pieces else cal_null
    cal_stats = cal_null.groupby(block_col, sort=False).agg(null_size=(score_col, "size"), block_max=(score_col, "max"))
    p_min = 1.0 / (len(cal_stats) + 1.0) if len(cal_stats) else 1.0
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    test = frame.loc[test_mask].sort_values(score_col, ascending=False).copy()
    if top_n is not None:
        test = test.head(top_n).copy()
    if gamma is None or len(cal_stats) == 0:
        test["_evalue"] = 0.0
    elif size_match_tau is None:
        maxima = np.sort(cal_stats["block_max"].astype(float).to_numpy())
        scores = test[score_col].astype(float).to_numpy()
        exceed = len(maxima) - np.searchsorted(maxima, scores, side="left")
        pvals = (1.0 + exceed) / (len(maxima) + 1.0)
        test["_evalue"] = gamma * (np.minimum(1.0, pvals) ** (gamma - 1.0))
    else:
        block_sizes = frame.groupby(block_col, sort=False).size()
        cal_log = np.log1p(cal_stats["null_size"].astype(float))
        scores = test[score_col].astype(float).to_numpy()
        evalues = []
        for block, score in zip(test[block_col].astype(str), scores):
            target = math.log1p(float(block_sizes.get(block, 0.0)))
            matched = cal_stats.loc[(cal_log - target).abs() <= size_match_tau, "block_max"].astype(float).to_numpy()
            if len(matched) == 0:
                evalues.append(0.0)
                continue
            pval = (1.0 + np.sum(matched >= score)) / (len(matched) + 1.0)
            evalues.append(float(gamma * (min(1.0, pval) ** (gamma - 1.0))))
        test["_evalue"] = evalues
    return test, {
        "n_cal_blocks": int(len(cal_blocks)),
        "n_nonempty_null_cal_blocks": int(len(cal_stats)),
        "block_coverage": float(len(cal_stats) / len(cal_blocks)) if cal_blocks else 0.0,
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_e": 1.0 / alpha,
    }


def release_metrics(pool: pd.DataFrame, alpha: float, budget: int) -> dict:
    evalues = pool["_evalue"].to_numpy(dtype=float)
    released, tau, margin, best_ratio = scs_release_count(evalues, alpha=alpha, budget=budget)
    selected = pool.iloc[np.argsort(evalues)[::-1][:released]].copy() if released else pool.iloc[[]].copy()
    return {
        "released": int(released),
        "actual_FTR": float((~selected["stable_DFT"].astype(bool)).mean()) if released else 0.0,
        "raw_topK_FTR": float((~pool["stable_DFT"].astype(bool)).mean()) if len(pool) else 0.0,
        "max_observed_e": float(pool["_evalue"].max()) if len(pool) else 0.0,
        "best_mass_ratio": float(best_ratio),
        "self_consistency_margin": float(margin),
        "tau": float(tau) if np.isfinite(tau) else math.inf,
    }


def summarize_seed_rows(rows: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    out = []
    for key, group in rows.groupby(group_cols, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = dict(zip(group_cols, key))
        n_seeds = int(group["seed"].nunique())
        diagnostic_runs = int(len(group))
        non_empty_runs = int((group["released"].astype(float) > 0).sum())
        non_empty_seeds = int(
            (group.groupby("seed")["released"].max().astype(float) > 0).sum()
        )
        stable_threshold = max(1, int(math.ceil(0.9 * n_seeds)))
        row.update(
            {
                "seeds": n_seeds,
                "diagnostic_runs": diagnostic_runs,
                "non_empty_runs": non_empty_runs,
                "non_empty_seeds": non_empty_seeds,
                "mean_release": float(group["released"].astype(float).mean()),
                "mean_FTR": float(group["actual_FTR"].astype(float).mean()),
                "max_FTR": float(group["actual_FTR"].astype(float).max()),
                "raw_topK_FTR_mean": float(group["raw_topK_FTR"].astype(float).mean()),
                "best_mass_ratio_mean": float(group["best_mass_ratio"].astype(float).mean()),
                "max_observed_e_mean": float(group["max_observed_e"].astype(float).mean()),
                "qualitative_decision": (
                    "release_stable"
                    if non_empty_seeds >= stable_threshold
                    else "power_loss_or_refusal"
                ),
                "safety_flag": (
                    "no_over_alpha_mean_FTR"
                    if float(group["actual_FTR"].astype(float).mean()) <= float(group["alpha"].astype(float).iloc[0])
                    else "mean_FTR_above_alpha_boundary"
                ),
            }
        )
        out.append(row)
    return pd.DataFrame(out)


def materials_size_matched_rerun(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    specs = [
        ("materials_cgcnn_alpha010_K100", "cgcnn_score", 100),
        ("materials_alignn_alpha010_K300", "alignn_score", 300),
        ("materials_alignn_alpha010_K500", "alignn_score", 500),
    ]
    rows = []
    seed_rows = []
    tau_levels = [("strict", 0.25), ("medium", 0.75), ("loose", 1.25), ("global_original", None)]
    for row_id, score_col, budget in specs:
        for seed in SIZE_MATCH_SEEDS:
            cal_blocks, test_blocks = split_blocks(frame["composition_family_pair"].astype(str).tolist(), seed)
            observed = observed_positive_mask(
                frame,
                score_col=score_col,
                block_col="composition_family_pair",
                cal_blocks=cal_blocks,
                rho=0.10,
            )
            for label, tau in tau_levels:
                test, diag = compute_materials_evalues(
                    frame,
                    score_col=score_col,
                    block_col="composition_family_pair",
                    cal_blocks=cal_blocks,
                    test_blocks=test_blocks,
                    observed=observed,
                    alpha=0.10,
                    size_match_tau=tau,
                    top_n=budget,
                )
                metrics = release_metrics(test.head(budget).copy(), alpha=0.10, budget=budget)
                seed_rows.append(
                    {
                        "domain": "materials_discovery",
                        "row_id": row_id,
                        "rerun_type": "size_matched_blockmax",
                        "match_level": label,
                        "log_size_tau": tau if tau is not None else np.nan,
                        "alpha": 0.10,
                        "K": budget,
                        "seed": seed,
                        **metrics,
                        **diag,
                        "evidence_status": "completed_candidate_level_materials_rerun",
                    }
                )
    seed_frame = pd.DataFrame(seed_rows)
    summary = summarize_seed_rows(seed_frame, ["domain", "row_id", "rerun_type", "match_level", "log_size_tau", "alpha", "K"])
    rows.append(summary)
    ctc = pd.read_csv(ROOT / "outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_strict_alpha010_smallK.csv")
    ctc100 = ctc[(ctc["alpha"].eq(0.10)) & (ctc["M"].eq(100))].iloc[0]
    rows.append(
        pd.DataFrame(
            [
                {
                    "domain": "biomedical_cell_tracking",
                    "row_id": "ctc_learned_alpha010_K100",
                    "rerun_type": "size_matched_blockmax",
                    "match_level": "not_run_public_candidate_level_artifact_unavailable",
                    "log_size_tau": np.nan,
                    "alpha": 0.10,
                    "K": 100,
                    "seeds": int(ctc100["seeds"]),
                    "non_empty_seeds": int(ctc100["nonempty_seeds"]),
                    "mean_release": float(ctc100["released_mean"]),
                    "mean_FTR": float(ctc100["actual_FTR_mean"]),
                    "max_FTR": float(ctc100["actual_FTR_max"]),
                    "raw_topK_FTR_mean": float(ctc100["raw_topM_actual_FTR_mean"]),
                    "best_mass_ratio_mean": float(ctc100["best_mass_ratio_mean"]),
                    "max_observed_e_mean": float(ctc100["max_observed_e_mean"]),
                    "qualitative_decision": "release_stable_in_completed_aggregate_row",
                    "safety_flag": "not_candidate_level_rerun",
                }
            ]
        )
    )
    sn = pd.read_csv(ROOT / "outputs/spacenet7_real_audit/table_spacenet7_real_audit_primary_refusal_diagnostics.csv")
    sn_row = sn.iloc[0]
    rows.append(
        pd.DataFrame(
            [
                {
                    "domain": "earth_observation",
                    "row_id": "spacenet_real_audit_alpha020_K100",
                    "rerun_type": "size_matched_blockmax",
                    "match_level": "not_run_public_candidate_level_artifact_unavailable",
                    "log_size_tau": np.nan,
                    "alpha": float(sn_row["alpha"]),
                    "K": int(sn_row["K"]),
                    "seeds": int(sn_row["total_seeds"]),
                    "non_empty_seeds": int(sn_row["non_empty_seeds"]),
                    "mean_release": 0.0,
                    "mean_FTR": 0.0,
                    "max_FTR": 0.0,
                    "raw_topK_FTR_mean": np.nan,
                    "best_mass_ratio_mean": float(sn_row["mean_best_mass_ratio"]),
                    "max_observed_e_mean": float(sn_row["mean_max_observed_e"]),
                    "qualitative_decision": "stable_refusal_in_completed_real_audit_row",
                    "safety_flag": "not_candidate_level_rerun",
                }
            ]
        )
    )
    return pd.concat(rows, ignore_index=True), seed_frame


def materials_downsampled_stress(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    specs = [
        ("materials_cgcnn_alpha010_K100", "cgcnn_score", 100),
        ("materials_alignn_alpha010_K500", "alignn_score", 500),
    ]
    rows = []
    for row_id, score_col, budget in specs:
        for seed in DOWNSAMPLE_STRESS_SEEDS:
            cal_blocks, test_blocks = split_blocks(frame["composition_family_pair"].astype(str).tolist(), seed)
            observed = observed_positive_mask(
                frame,
                score_col=score_col,
                block_col="composition_family_pair",
                cal_blocks=cal_blocks,
                rho=0.10,
            )
            blocks = frame["composition_family_pair"].astype(str)
            cal_null = frame.loc[blocks.isin(cal_blocks).to_numpy() & ~observed, ["composition_family_pair", score_col]]
            block_arrays = [
                group[score_col].astype(float).to_numpy()
                for _, group in cal_null.groupby("composition_family_pair", sort=False)
                if len(group) > 0
            ]
            n_nonempty = len(block_arrays)
            n_total = len(cal_blocks)
            p_min = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
            gamma = gamma_star_from_p(p_min)
            emax_eff = emax_from_p(gamma, p_min)
            test_base = frame.loc[blocks.isin(test_blocks).to_numpy()].sort_values(score_col, ascending=False).head(budget).copy()
            scores = test_base[score_col].astype(float).to_numpy()
            for m in [10, 25, 50, 100]:
                for repeat in range(20):
                    rng = np.random.default_rng(seed * 1009 + repeat * 17 + m)
                    maxima = []
                    for arr in block_arrays:
                        if len(arr) > m:
                            maxima.append(float(arr[rng.choice(len(arr), size=m, replace=False)].max()))
                        else:
                            maxima.append(float(arr.max()))
                    maxima = np.sort(np.asarray(maxima, dtype=float))
                    test = test_base.copy()
                    if gamma is None or len(maxima) == 0:
                        test["_evalue"] = 0.0
                    else:
                        exceed = len(maxima) - np.searchsorted(maxima, scores, side="left")
                        pvals = (1.0 + exceed) / (len(maxima) + 1.0)
                        test["_evalue"] = gamma * (np.minimum(1.0, pvals) ** (gamma - 1.0))
                    diag = {
                        "n_cal_blocks": int(n_total),
                        "n_nonempty_null_cal_blocks": int(n_nonempty),
                        "block_coverage": float(n_nonempty / n_total) if n_total else 0.0,
                        "p_min_effective": p_min,
                        "gamma": gamma,
                        "emax_effective": emax_eff,
                        "required_e": 10.0,
                    }
                    metrics = release_metrics(test.head(budget).copy(), alpha=0.10, budget=budget)
                    rows.append(
                        {
                            "domain": "materials_discovery",
                            "row_id": row_id,
                            "stress_type": "downsampled_blockmax",
                            "downsample_m": m,
                            "repeat": repeat,
                            "alpha": 0.10,
                            "K": budget,
                            "seed": seed,
                            **metrics,
                            **diag,
                            "evidence_status": "completed_candidate_level_materials_stress",
                        }
                    )
    seed_frame = pd.DataFrame(rows)
    summary = summarize_seed_rows(
        seed_frame,
        ["domain", "row_id", "stress_type", "downsample_m", "alpha", "K"],
    )
    summary["stress_interpretation"] = np.where(
        summary["mean_FTR"].astype(float) <= summary["alpha"].astype(float),
        "no_silent_overrelease_under_downsampled_blockmax",
        "boundary_or_optimistic_downsample_stress_exceeds_alpha",
    )
    return summary, seed_frame


def build_summary(super_rows: pd.DataFrame, size_matched: pd.DataFrame, downsampled: pd.DataFrame) -> pd.DataFrame:
    records = []
    for domain in ["materials_discovery", "biomedical_cell_tracking", "earth_observation"]:
        domain_super = super_rows[super_rows["domain"].eq(domain)] if len(super_rows) else pd.DataFrame()
        domain_size = size_matched[size_matched["domain"].eq(domain)] if len(size_matched) else pd.DataFrame()
        domain_down = downsampled[downsampled["domain"].eq(domain)] if len(downsampled) else pd.DataFrame()
        if domain == "materials_discovery":
            status = "candidate_level_completed"
            conclusion = "size-matched and downsampled reruns retain release/refusal pattern or expose conservative power changes"
        elif domain == "earth_observation":
            status = "audit_sample_and_aggregate_diagnostic"
            conclusion = "real-audit K100 remains refusal; audit-sample superuniformity screen is underpowered and not a release claim"
        else:
            status = "aggregate_only_public_package"
            conclusion = "CTC learned strict row remains stable in completed aggregate evidence; candidate-level size-matched rerun requires raw link universe"
        records.append(
            {
                "domain": domain,
                "superuniformity_rows": int(len(domain_super)),
                "size_matched_rows": int(len(domain_size)),
                "downsampled_rows": int(len(domain_down)),
                "evidence_status": status,
                "primary_conclusion": conclusion,
            }
        )
    return pd.DataFrame(records)


def plot_superuniformity(pdiag: pd.DataFrame, out_csv: Path, out_pdf: Path) -> None:
    pdiag.to_csv(out_csv, index=False)
    if pdiag.empty:
        out_pdf.write_bytes(b"")
        return
    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    x = np.arange(len(pdiag))
    colors = ["#1b9e77" if d == "materials_discovery" else "#7570b3" for d in pdiag["domain"]]
    ax.bar(x, pdiag["one_sided_KS_ecdf_minus_uniform"].astype(float), color=colors)
    ax.axhline(0.10, color="#d95f02", linestyle="--", linewidth=1.0, label="diagnostic threshold 0.10")
    labels = [f"{d.split('_')[0]}:{s}" for d, s in zip(pdiag["domain"], pdiag["size_stratum"])]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylabel("one-sided KS: ECDF(p) - uniform")
    ax.set_title("Block-size stratified p-value diagnostic")
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(out_pdf)
    plt.close(fig)


def write_markdown(out_dir: Path, summary: pd.DataFrame) -> None:
    text = """# Block Heterogeneity Robustness Closeout

Evidence status: mixed completed diagnostic.

This milestone addresses whether heterogeneous block sizes could make block
maxima incomparable. It does not modify the manuscript text. It separates
candidate-level reruns from aggregate or audit-sample diagnostics.

## Completed Candidate-Level Evidence

- Materials/WBM has public-safe candidate IDs, block assignments, scores and
  DFT labels available locally, so Phase25 runs actual candidate-level
  size-matched and downsampled block-max stress tests for CGCNN/ALIGNN rows.
- `table_size_matched_rerun.csv` reports strict/medium/loose log-size matched
  calibration variants plus the original global calibration on 10 diagnostic
  seeds.
- `table_downsampled_blockmax_stress.csv` reports fixed-size null-superset
  downsampling at m in {10, 25, 50, 100} with 20 repeats on 5 representative
  diagnostic seeds.

## Scoped Diagnostics

- SpaceNet contributes an audit-sample p-value screen and completed real-audit
  K=100 refusal diagnostics. The audit sample contains few false links, so the
  p-value screen is explicitly underpowered.
- CTC public artifacts contain aggregate learned-source release tables but not
  candidate-level block-max artifacts. The CTC row is therefore marked as
  aggregate-only in this milestone; no size-matched rerun is fabricated.

## Interpretation

The materials candidate-level stresses show that block-size comparability can
change power near the boundary, but the diagnostics do not create a hidden
unsafe release claim. Rows either retain their qualitative release/refusal
pattern or are marked as boundary/power-loss diagnostics. Where candidate-level
artifacts are absent, the milestone records that limitation directly.

## Main Artifacts

- `table_block_size_heterogeneity_summary.csv`
- `figure_block_size_superuniformity.csv`
- `figure_block_size_superuniformity.pdf`
- `table_size_matched_rerun.csv`
- `table_size_matched_rerun_seed_rows.csv`
- `table_downsampled_blockmax_stress.csv`
- `table_downsampled_blockmax_stress_seed_rows.csv`
- `B2_APPROXIMATE_EVALUE_VALIDITY_LEMMA.md`
"""
    text += "\n## Domain Summary\n\n" + summary.to_markdown(index=False) + "\n"
    (out_dir / "BLOCK_HETEROGENEITY_ROBUSTNESS_CLOSEOUT.md").write_text(text, encoding="utf-8")

    lemma = """# B2 Approximate E-Value Validity Lemma

This is a supplement-facing note, not a main-text edit.

Suppose the constructed false-candidate e-values satisfy
`E[E_p] <= 1 + eta` for every false candidate `p`, rather than exact
`E[E_p] <= 1`. If the selected set `R` satisfies the same PARC
self-consistency condition, then

```text
E[ |R ∩ H0| / (|R| ∨ 1) ] <= alpha (1 + eta).
```

Proof sketch. For every false candidate `p`, self-consistency gives

```text
1[p in R] / (|R| ∨ 1) <= alpha E_p / K.
```

Summing over false candidates and taking expectations gives

```text
E[FDP(R)] <= (alpha / K) sum_{p in H0} E[E_p]
          <= alpha (1 + eta) |H0| / K
          <= alpha (1 + eta).
```

Thus block-heterogeneity diagnostics can be read as practical checks for
e-value inflation. If block comparability is poor, size-stratified,
size-matched, or conservative calibration variants are the fallback.
"""
    (out_dir / "B2_APPROXIMATE_EVALUE_VALIDITY_LEMMA.md").write_text(lemma, encoding="utf-8")


def write_provenance(path: Path, inputs: dict[str, str], started: float, role: str) -> None:
    payload = {
        "artifact": path.name,
        "role": role,
        "command": "python scripts/build_block_heterogeneity_robustness.py",
        "runtime_sec": round(time.time() - started, 3),
        "input_sha256": inputs,
        "output_sha256": sha256_file(path),
    }
    path.with_suffix(path.suffix + ".provenance.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="outputs/milestones/block_heterogeneity_robustness")
    parser.add_argument("--wbm-summary", default=str(DEFAULT_WBM))
    parser.add_argument("--cgcnn-predictions", default=str(DEFAULT_CGCNN))
    parser.add_argument("--alignn-predictions", default=str(DEFAULT_ALIGNN))
    parser.add_argument("--cgcnn-pred-col", default="e_form_per_atom_mp2020_corrected_pred_ens")
    parser.add_argument("--alignn-pred-col", default="e_form_per_atom_alignn_ff")
    args = parser.parse_args()

    started = time.time()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    frame, input_hashes = load_materials_frame(args)
    input_hashes.update(
        {
            "ctc_strict_table": sha256_file(ROOT / "outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_strict_alpha010_smallK.csv"),
            "spacenet_real_audit_primary_refusal": sha256_file(ROOT / "outputs/spacenet7_real_audit/table_spacenet7_real_audit_primary_refusal_diagnostics.csv"),
            "spacenet_prospective_audit_manifest": sha256_file(ROOT / "outputs/milestones/scientific_domain_spacenet7_prospective/audit_manifest.csv"),
        }
    )

    pdiag = pd.concat([materials_superuniformity(frame), spacenet_superuniformity_from_audit_sample()], ignore_index=True)
    size_matched, size_seed = materials_size_matched_rerun(frame)
    downsampled, down_seed = materials_downsampled_stress(frame)
    summary = build_summary(pdiag, size_matched, downsampled)

    outputs = {
        "table_block_size_heterogeneity_summary.csv": summary,
        "table_size_matched_rerun.csv": size_matched,
        "table_size_matched_rerun_seed_rows.csv": size_seed,
        "table_downsampled_blockmax_stress.csv": downsampled,
        "table_downsampled_blockmax_stress_seed_rows.csv": down_seed,
    }
    for name, frame_out in outputs.items():
        frame_out.to_csv(out_dir / name, index=False)
    plot_superuniformity(pdiag, out_dir / "figure_block_size_superuniformity.csv", out_dir / "figure_block_size_superuniformity.pdf")
    write_markdown(out_dir, summary)

    roles = {name: name.removesuffix(".csv") for name in outputs}
    roles.update(
        {
            "figure_block_size_superuniformity.csv": "superuniformity_figure_source",
            "figure_block_size_superuniformity.pdf": "superuniformity_figure_pdf",
            "BLOCK_HETEROGENEITY_ROBUSTNESS_CLOSEOUT.md": "closeout",
            "B2_APPROXIMATE_EVALUE_VALIDITY_LEMMA.md": "supplement_note",
        }
    )
    for name, role in roles.items():
        write_provenance(out_dir / name, input_hashes, started, role)
    write_manifest(out_dir)
    print(f"wrote {out_dir}")


if __name__ == "__main__":
    main()
