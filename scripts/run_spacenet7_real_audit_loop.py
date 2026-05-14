#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd


USECOLS = [
    "dataset",
    "domain",
    "generator",
    "aoi",
    "video_id",
    "path_id",
    "source_building_id",
    "target_building_id",
    "frame_start",
    "frame_end",
    "source_year",
    "source_month",
    "target_year",
    "target_month",
    "score",
    "candidate_rank",
    "is_unmatched",
    "bbox_iou",
    "centroid_distance_score",
    "area_ratio",
    "base_geometry_score",
]

DEFAULT_CANDIDATE_UNIVERSE = (
    "${SPACENET7_LINK_UNIVERSE}/candidate_universe.csv"
    if "SPACENET7_LINK_UNIVERSE" not in os.environ
    else str(Path(os.environ["SPACENET7_LINK_UNIVERSE"]) / "candidate_universe.csv")
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def bool_array(series: pd.Series) -> np.ndarray:
    return series.astype(str).str.lower().isin(["true", "1", "yes"]).to_numpy(dtype=bool)


def gamma_star_from_p(p_value: float | None) -> float | None:
    if p_value is None or p_value <= 0.0 or p_value >= 1.0:
        return None
    gamma = -1.0 / math.log(p_value)
    return gamma if 0.0 < gamma < 1.0 else None


def emax_from_p(gamma: float | None, p_value: float | None) -> float | None:
    if gamma is None or p_value is None or p_value <= 0.0 or p_value > 1.0:
        return None
    return gamma * (p_value ** (gamma - 1.0))


def scs_release_count(evalues: np.ndarray, alpha: float, m_budget: int) -> tuple[int, float, float, float]:
    if len(evalues) == 0:
        return 0, math.inf, -math.inf, 0.0
    sorted_e = np.sort(evalues.astype(float))[::-1]
    released = 0
    best_tau = math.inf
    best_margin = -math.inf
    best_ratio = 0.0
    for k in range(1, len(sorted_e) + 1):
        tau = m_budget / (alpha * k)
        margin = float(sorted_e[k - 1] - tau)
        ratio = float(alpha * k * sorted_e[k - 1] / m_budget)
        best_ratio = max(best_ratio, ratio)
        if margin > best_margin:
            best_margin = margin
            best_tau = tau
        if sorted_e[k - 1] >= tau:
            released = k
    if released:
        tau = m_budget / (alpha * released)
        return released, tau, float(sorted_e[released - 1] - tau), best_ratio
    return 0, best_tau, best_margin, best_ratio


def split_blocks(block_ids: np.ndarray, seed: int, tune_ratio: float, cal_ratio: float) -> tuple[np.ndarray, np.ndarray, list[int]]:
    ordered = sorted(set(int(v) for v in block_ids.tolist()))
    rng = random.Random(seed)
    rng.shuffle(ordered)
    tune_end = int(round(len(ordered) * tune_ratio))
    cal_end = tune_end + int(round(len(ordered) * cal_ratio))
    cal_blocks = set(ordered[tune_end:cal_end])
    test_blocks = set(ordered[cal_end:])
    cal_mask = np.fromiter((int(v) in cal_blocks for v in block_ids), dtype=bool, count=len(block_ids))
    test_mask = np.fromiter((int(v) in test_blocks for v in block_ids), dtype=bool, count=len(block_ids))
    return cal_mask, test_mask, sorted(cal_blocks)


def compute_test_evalues(
    scores: np.ndarray,
    block_ids: np.ndarray,
    cal_null_mask: np.ndarray,
    test_indices: np.ndarray,
    cal_blocks: list[int],
    alpha: float,
) -> tuple[np.ndarray, dict]:
    if cal_null_mask.any():
        cal_df = pd.DataFrame({"video_id": block_ids[cal_null_mask], "score": scores[cal_null_mask]})
        maxima = cal_df.groupby("video_id", sort=False)["score"].max().to_numpy(dtype=float)
    else:
        maxima = np.asarray([], dtype=float)
    n_nonempty = int(len(maxima))
    p_min = 1.0 / (n_nonempty + 1.0) if n_nonempty else 1.0
    gamma = gamma_star_from_p(p_min)
    emax_eff = emax_from_p(gamma, p_min)
    diag = {
        "n_cal_total": len(cal_blocks),
        "n_nonempty": n_nonempty,
        "p_min_effective": p_min,
        "gamma": gamma,
        "emax_effective": emax_eff,
        "required_emax": 1.0 / alpha if alpha > 0 else None,
    }
    if gamma is None or len(test_indices) == 0 or len(maxima) == 0:
        return np.zeros(len(test_indices), dtype=float), diag
    maxima_sorted = np.sort(maxima)
    test_scores = scores[test_indices]
    exceed = len(maxima_sorted) - np.searchsorted(maxima_sorted, test_scores, side="left")
    p_block = (1.0 + exceed) / (len(maxima_sorted) + 1.0)
    p_any = np.minimum(1.0, p_block)
    return (gamma * (p_any ** (gamma - 1.0))).astype(float), diag


def empty_reason(released: int, diag: dict, max_observed_e: float | None) -> str:
    if released:
        return ""
    required = diag.get("required_emax")
    emax = diag.get("emax_effective")
    if required is not None and (emax is None or float(emax) < float(required)):
        return "resolution_below_required_emax"
    if required is not None and (max_observed_e is None or float(max_observed_e) < float(required)):
        return "observed_e_below_required_emax"
    return "insufficient_high_e_mass_for_uniform_scs"


def make_audit_id(prefix: str, rank: int) -> str:
    return f"{prefix}-{rank:06d}"


def review_label(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    same = ~bool_array(out["is_unmatched"])
    out["initial_review_label"] = np.where(same, "same_building", "not_same_building")
    out["initial_verified_positive_for_calibration"] = np.where(same, "yes", "no")
    out["initial_review_confidence"] = np.where(same, "high", "medium")
    out["initial_review_reason"] = np.where(
        same,
        "source and target share the official SpaceNet building identifier; requires human visual confirmation",
        "source and target have different official SpaceNet building identifiers; requires human visual confirmation",
    )
    out["review_status"] = "requires_human_confirmation"
    return out


def blind_template(frame: pd.DataFrame) -> pd.DataFrame:
    visible_cols = [
        "audit_id",
        "sample_set",
        "aoi",
        "video_id",
        "source_year",
        "source_month",
        "target_year",
        "target_month",
        "source_building_id",
        "target_building_id",
        "bbox_iou",
        "centroid_distance_score",
        "area_ratio",
        "base_geometry_score",
        "path_id",
    ]
    out = frame[visible_cols].copy()
    out["human_label"] = ""
    out["human_verified_positive_for_calibration"] = ""
    out["human_reason"] = ""
    out["human_confidence"] = ""
    out["human_review_status"] = ""
    return out


def round_robin_by_block(frame: pd.DataFrame, n: int, per_block_cap: int) -> pd.DataFrame:
    groups: dict[int, pd.DataFrame] = {}
    for block, group in frame.sort_values(["video_id", "score", "candidate_rank"], ascending=[True, False, True]).groupby("video_id"):
        groups[int(block)] = group.head(per_block_cap).copy()
    selected = []
    offsets = {block: 0 for block in groups}
    blocks = sorted(groups)
    while len(selected) < n:
        added = False
        for block in blocks:
            group = groups[block]
            offset = offsets[block]
            if offset < len(group):
                selected.append(group.iloc[offset])
                offsets[block] += 1
                added = True
                if len(selected) >= n:
                    break
        if not added:
            break
    return pd.DataFrame(selected).reset_index(drop=True)


def run_parc_with_observed(df: pd.DataFrame, observed_ranks: set[int], alphas: list[float], budgets: list[int], seeds: list[int]) -> tuple[pd.DataFrame, dict[tuple[float, int, int], np.ndarray]]:
    df = df.sort_values(["candidate_rank", "score"], ascending=[True, False]).reset_index(drop=True)
    block_ids = df["video_id"].astype(int).to_numpy()
    scores = df["score"].astype(float).to_numpy()
    ranks = df["candidate_rank"].astype(int).to_numpy()
    full_false = bool_array(df["is_unmatched"])
    observed = np.isin(ranks, np.asarray(sorted(observed_ranks), dtype=int))
    partial_null = ~observed
    selected_by_setting: dict[tuple[float, int, int], np.ndarray] = {}
    rows = []
    for seed in seeds:
        cal_mask, test_mask, cal_blocks = split_blocks(block_ids, seed, tune_ratio=1 / 6, cal_ratio=1 / 2)
        test_indices = np.flatnonzero(test_mask)
        cal_null_mask = cal_mask & partial_null
        for alpha in alphas:
            evalues, diag = compute_test_evalues(scores, block_ids, cal_null_mask, test_indices, cal_blocks, alpha)
            max_observed_e = float(np.max(evalues)) if len(evalues) else None
            for budget in budgets:
                pool_indices = test_indices[: min(budget, len(test_indices))]
                pool_e = evalues[: len(pool_indices)]
                released, tau, margin, best_mass_ratio = scs_release_count(pool_e, alpha, budget)
                if released:
                    local = np.argsort(pool_e)[::-1][:released]
                    selected_indices = pool_indices[local]
                    actual_ftr = float(full_false[selected_indices].mean())
                    partial_utr = float(partial_null[selected_indices].mean())
                else:
                    selected_indices = np.asarray([], dtype=int)
                    actual_ftr = 0.0
                    partial_utr = 0.0
                raw_ftr = float(full_false[pool_indices].mean()) if len(pool_indices) else 0.0
                raw_partial = float(partial_null[pool_indices].mean()) if len(pool_indices) else 0.0
                selected_by_setting[(alpha, budget, seed)] = selected_indices
                rows.append(
                    {
                        "alpha": alpha,
                        "seed": seed,
                        "M": budget,
                        "released": int(released),
                        "official_GT_FTR": actual_ftr,
                        "partial_UTR_seen_by_PARC": partial_utr,
                        "raw_topM_official_GT_FTR": raw_ftr,
                        "raw_topM_partial_unsupported_rate": raw_partial,
                        "n_cal_blocks": int(diag["n_cal_total"]),
                        "n_nonempty_null_cal_blocks": int(diag["n_nonempty"]),
                        "p_min_effective": diag["p_min_effective"],
                        "gamma": diag["gamma"],
                        "emax_effective": diag["emax_effective"],
                        "required_emax": diag["required_emax"],
                        "max_observed_e": max_observed_e,
                        "best_mass_ratio": best_mass_ratio,
                        "tau_k": tau if released else "",
                        "self_consistency_margin": margin if released else "",
                        "empty_reason": empty_reason(released, diag, max_observed_e),
                    }
    )
    return pd.DataFrame(rows), selected_by_setting


def choose_release_audit_setting(
    seed_results: pd.DataFrame, primary_alpha: float, primary_M: int
) -> tuple[float, int, str]:
    primary = seed_results[(seed_results["alpha"] == primary_alpha) & (seed_results["M"] == primary_M)]
    if not primary.empty and int((primary["released"] > 0).sum()) > 0:
        return primary_alpha, primary_M, "primary"

    grouped = (
        seed_results.groupby(["alpha", "M"], as_index=False)
        .agg(nonempty=("released", lambda s: int((s > 0).sum())), mean_release=("released", "mean"))
    )
    grouped = grouped[(grouped["alpha"] == primary_alpha) & (grouped["nonempty"] >= 15)].copy()
    if grouped.empty:
        grouped = (
            seed_results.groupby(["alpha", "M"], as_index=False)
            .agg(nonempty=("released", lambda s: int((s > 0).sum())), mean_release=("released", "mean"))
            .query("nonempty > 0")
            .copy()
        )
    if grouped.empty:
        return primary_alpha, primary_M, "none_available"

    grouped = grouped.sort_values(["mean_release", "nonempty", "M"], ascending=[False, False, False])
    row = grouped.iloc[0]
    return float(row["alpha"]), int(row["M"]), "diagnostic_predefined_budget_after_primary_refusal"


def write_review_files(out_dir: Path, name: str, frame: pd.DataFrame) -> tuple[Path, Path]:
    blind = out_dir / f"{name}_blind_template.csv"
    prefill = out_dir / f"{name}_review_prefill.csv"
    blind_template(frame).to_csv(blind, index=False)
    review_label(frame).to_csv(prefill, index=False)
    return blind, prefill


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-universe", default=DEFAULT_CANDIDATE_UNIVERSE)
    parser.add_argument("--out-dir", default="outputs/spacenet7_real_audit")
    parser.add_argument("--calibration-n", type=int, default=800)
    parser.add_argument("--release-audit-n", type=int, default=200)
    parser.add_argument("--raw-topk-audit-n", type=int, default=200)
    parser.add_argument("--primary-alpha", type=float, default=0.20)
    parser.add_argument("--primary-M", type=int, default=100)
    parser.add_argument("--alphas", default="0.10,0.20")
    parser.add_argument("--budgets", default="25,50,75,100")
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = Path(args.candidate_universe)
    df = pd.read_csv(candidate_path, usecols=USECOLS)
    df = df.sort_values(["candidate_rank", "score"], ascending=[True, False]).reset_index(drop=True)

    per_block_cap = max(1, int(math.ceil(args.calibration_n / max(1, df["video_id"].nunique()))) + 2)
    calibration = round_robin_by_block(df, args.calibration_n, per_block_cap)
    calibration.insert(0, "audit_id", [make_audit_id("CAL", i + 1) for i in range(len(calibration))])
    calibration.insert(1, "sample_set", "calibration_audit")

    cal_blind, cal_prefill = write_review_files(out_dir, "calibration_audit", calibration)
    observed_ranks = set(
        calibration.loc[~bool_array(calibration["is_unmatched"]), "candidate_rank"].astype(int).tolist()
    )

    alphas = [float(v) for v in args.alphas.split(",") if v.strip()]
    budgets = [int(v) for v in args.budgets.split(",") if v.strip()]
    if args.primary_M not in budgets:
        budgets.append(args.primary_M)
        budgets = sorted(set(budgets))
    seeds = [int(v) for v in args.seeds.split(",") if v.strip()]
    seed_results, selected = run_parc_with_observed(df, observed_ranks, alphas, budgets, seeds)
    seed_results.to_csv(out_dir / "table_spacenet7_real_audit_seed_results.csv", index=False)

    release_alpha, release_M, release_setting_status = choose_release_audit_setting(
        seed_results, args.primary_alpha, args.primary_M
    )
    release_key_prefix = (release_alpha, release_M)
    union_indices: list[int] = []
    for seed in seeds:
        union_indices.extend(selected.get((*release_key_prefix, seed), np.asarray([], dtype=int)).tolist())
    unique_indices = sorted(set(union_indices), key=lambda idx: int(df.iloc[idx]["candidate_rank"]))
    release_frame = df.iloc[unique_indices[: args.release_audit_n]].copy().reset_index(drop=True)
    release_frame.insert(0, "audit_id", [make_audit_id("REL", i + 1) for i in range(len(release_frame))])
    release_frame.insert(1, "sample_set", "release_audit")
    rel_blind, rel_prefill = write_review_files(out_dir, "release_audit", release_frame)

    released_ranks = set(release_frame["candidate_rank"].astype(int).tolist()) if not release_frame.empty else set()
    raw_pool = df.head(max(args.raw_topk_audit_n * 5, args.primary_M * 20)).copy()
    raw_pool = raw_pool[~raw_pool["candidate_rank"].astype(int).isin(released_ranks)]
    raw_frame = raw_pool.head(args.raw_topk_audit_n).copy().reset_index(drop=True)
    raw_frame.insert(0, "audit_id", [make_audit_id("RAW", i + 1) for i in range(len(raw_frame))])
    raw_frame.insert(1, "sample_set", "raw_topk_audit")
    raw_blind, raw_prefill = write_review_files(out_dir, "raw_topk_audit", raw_frame)

    manifest = pd.concat(
        [
            calibration.drop(columns=["is_unmatched"], errors="ignore"),
            release_frame.drop(columns=["is_unmatched"], errors="ignore"),
            raw_frame.drop(columns=["is_unmatched"], errors="ignore"),
        ],
        ignore_index=True,
    )
    manifest.to_csv(out_dir / "audit_manifest.csv", index=False)

    primary = seed_results[(seed_results["alpha"] == args.primary_alpha) & (seed_results["M"] == args.primary_M)]
    summary = {
        "status": "review_ready_requires_human_confirmation",
        "candidate_universe": "${SPACENET7_LINK_UNIVERSE}/candidate_universe.csv",
        "candidate_universe_sha256": sha256_file(candidate_path),
        "calibration_audit_rows": int(len(calibration)),
        "calibration_initial_verified_positive_rows": int(len(observed_ranks)),
        "calibration_block_coverage": int(calibration["video_id"].nunique()),
        "release_audit_rows": int(len(release_frame)),
        "release_audit_setting_status": release_setting_status,
        "release_audit_alpha": release_alpha,
        "release_audit_M": release_M,
        "raw_topk_audit_rows": int(len(raw_frame)),
        "primary_alpha": args.primary_alpha,
        "primary_M": args.primary_M,
        "primary_nonempty_seeds": int((primary["released"] > 0).sum()) if not primary.empty else 0,
        "primary_mean_release": float(primary["released"].mean()) if not primary.empty else 0.0,
        "primary_official_GT_FTR_mean": float(primary["official_GT_FTR"].mean()) if not primary.empty else 0.0,
        "primary_raw_topM_official_GT_FTR_mean": float(primary["raw_topM_official_GT_FTR"].mean()) if not primary.empty else 0.0,
        "paper_status": "not_paper_facing_until_human_confirmed",
    }
    pd.DataFrame([summary]).to_csv(out_dir / "table_spacenet7_real_audit_summary.csv", index=False)

    report = out_dir / "RUN_REPORT.md"
    report.write_text(
        "# SpaceNet 7 Real-Audit Loop Report\n\n"
        "Status: review-ready audit materials generated. The initial labels are not paper-facing human audit labels until human-confirmed.\n\n"
        "## Outputs\n\n"
        f"- Calibration blind template: `{cal_blind}`\n"
        f"- Calibration review prefill: `{cal_prefill}`\n"
        f"- Release blind template: `{rel_blind}`\n"
        f"- Release review prefill: `{rel_prefill}`\n"
        f"- Raw top-K blind template: `{raw_blind}`\n"
        f"- Raw top-K review prefill: `{raw_prefill}`\n"
        "- Seed results: `table_spacenet7_real_audit_seed_results.csv`\n"
        "- Summary: `table_spacenet7_real_audit_summary.csv`\n\n"
        "## Primary preliminary status\n\n"
        f"- Non-empty seeds: {summary['primary_nonempty_seeds']}/20\n"
        f"- Mean release: {summary['primary_mean_release']:.3f}\n"
        f"- Official-GT FTR mean: {summary['primary_official_GT_FTR_mean']:.6f}\n"
        f"- Raw top-M official-GT FTR mean: {summary['primary_raw_topM_official_GT_FTR_mean']:.6f}\n\n"
        "## Release-audit target\n\n"
        f"- Setting status: {release_setting_status}\n"
        f"- Release-audit alpha: {release_alpha}\n"
        f"- Release-audit M: {release_M}\n"
        f"- Release-audit rows: {len(release_frame)}\n\n"
        "Human confirmation is required before these labels can be reported as real audit evidence.\n",
        encoding="utf-8",
    )

    with (out_dir / "spacenet7_real_audit_loop_summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
