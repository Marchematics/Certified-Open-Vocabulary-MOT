#!/usr/bin/env python3
"""Prepare an iWildCam animal-present prospective human-audit trial.

The script creates a public-safe prospective audit package.  It does not claim
human FTR unless human-confirmed label files are supplied.  Official iWildCam
support is used only for proxy planning diagnostics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd


FORBIDDEN_HUMAN_CLAIM = "proxy_planning_only_requires_human_confirmation"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_array(series: pd.Series) -> np.ndarray:
    return series.astype(str).str.lower().isin(["true", "1", "yes"]).to_numpy(dtype=bool)


def parse_list(value: str, cast):
    return [cast(item) for item in value.split(",") if item.strip()]


def gamma_star_from_p(p_value: float | None) -> float | None:
    if p_value is None or p_value <= 0.0 or p_value >= 1.0:
        return None
    gamma = -1.0 / math.log(p_value)
    return gamma if 0.0 < gamma < 1.0 else None


def emax_from_p(gamma: float | None, p_value: float | None) -> float | None:
    if gamma is None or p_value is None or p_value <= 0.0 or p_value > 1.0:
        return None
    return gamma * (p_value ** (gamma - 1.0))


def scs_release_count(evalues: np.ndarray, alpha: float, M: int) -> tuple[int, float, float, float]:
    if len(evalues) == 0:
        return 0, math.inf, -math.inf, 0.0
    sorted_e = np.sort(evalues.astype(float))[::-1]
    released = 0
    best_tau = math.inf
    best_margin = -math.inf
    best_ratio = 0.0
    for k in range(1, len(sorted_e) + 1):
        tau = M / (alpha * k)
        margin = float(sorted_e[k - 1] - tau)
        ratio = float(alpha * k * sorted_e[k - 1] / M)
        best_ratio = max(best_ratio, ratio)
        if margin > best_margin:
            best_margin = margin
            best_tau = tau
        if sorted_e[k - 1] >= tau:
            released = k
    if released:
        tau = M / (alpha * released)
        return released, tau, float(sorted_e[released - 1] - tau), best_ratio
    return 0, best_tau, best_margin, best_ratio


def split_blocks(block_ids: np.ndarray, seed: int, tune_ratio: float = 1 / 6, cal_ratio: float = 1 / 2) -> tuple[np.ndarray, np.ndarray, list[int]]:
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


def compute_evalues(
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


def safe_int_from_path(path_id: str) -> int:
    match = re.search(r"_img(\d+)_", str(path_id))
    return int(match.group(1)) if match else 0


def add_temporal_blocks(universe: pd.DataFrame, chunks: int) -> pd.DataFrame:
    df = universe.copy()
    if "location_id" not in df.columns:
        df["location_id"] = df["video_id"]
    df["_order_key"] = df["path_id"].map(safe_int_from_path)
    df["_temporal_chunk"] = 0
    for loc, idx in df.groupby("location_id").groups.items():
        loc_idx = list(idx)
        order = df.loc[loc_idx, "_order_key"].rank(method="dense", ascending=True).to_numpy()
        if len(order) <= 1:
            chunk = np.zeros(len(order), dtype=int)
        else:
            chunk = np.floor((order - 1) / max(order.max(), 1) * chunks).astype(int)
            chunk = np.minimum(chunk, chunks - 1)
        df.loc[loc_idx, "_temporal_chunk"] = chunk
    df["original_video_id"] = df["video_id"]
    df["video_id"] = df["location_id"].astype(int) * 100 + df["_temporal_chunk"].astype(int)
    df["iwildcam_block_definition"] = "camera_location_x_temporal_chunk"
    return df


def round_robin_by_block(frame: pd.DataFrame, n: int, per_block_cap: int) -> pd.DataFrame:
    selected = []
    groups = {
        int(block): group.sort_values(["score", "candidate_rank"], ascending=[False, True]).head(per_block_cap).reset_index(drop=True)
        for block, group in frame.groupby("video_id", sort=True)
    }
    offsets = {block: 0 for block in groups}
    while len(selected) < n:
        added = False
        for block in sorted(groups):
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


def add_human_fields(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["human_label"] = ""
    out["human_verified_positive_for_calibration"] = ""
    out["human_reason"] = ""
    out["human_confidence"] = ""
    out["human_review_status"] = ""
    return out


def blind_columns(frame: pd.DataFrame, sample_set: str) -> pd.DataFrame:
    keep = [
        "audit_id",
        "sample_set",
        "dataset",
        "location_id",
        "video_id",
        "original_video_id",
        "_temporal_chunk",
        "path_id",
        "query",
        "score",
        "objectness",
        "candidate_rank",
        "frame_start",
        "frame_end",
        "support_semantics",
    ]
    available = [col for col in keep if col in frame.columns]
    out = frame[available].copy()
    out["sample_set"] = sample_set
    return add_human_fields(out)


def official_proxy_initial(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_human_fields(frame.copy())
    animal = ~bool_array(out["is_unmatched"])
    out["official_proxy_label_for_planning_only"] = np.where(animal, "animal", "not_animal")
    out["official_proxy_verified_positive_for_planning_only"] = np.where(animal, "yes", "no")
    out["official_proxy_note"] = "planning proxy only; human fields control paper-facing real audit"
    return out


def load_human_verified(path: str | None) -> set[str]:
    if not path:
        return set()
    label_path = Path(path)
    if not label_path.exists():
        raise FileNotFoundError(label_path)
    labels = pd.read_csv(label_path)
    required = {"path_id", "human_label", "human_verified_positive_for_calibration"}
    missing = required - set(labels.columns)
    if missing:
        raise ValueError(f"missing human label columns: {sorted(missing)}")
    verified = (
        labels["human_verified_positive_for_calibration"].astype(str).str.lower().isin(["yes", "true", "1"])
        & labels["human_label"].astype(str).str.lower().isin(["animal", "true_animal"])
    )
    return set(labels.loc[verified, "path_id"].astype(str))


def run_parc_with_observed(
    df: pd.DataFrame,
    observed_paths: set[str],
    alphas: list[float],
    budgets: list[int],
    seeds: list[int],
    score_column: str,
) -> tuple[pd.DataFrame, dict[tuple[float, int, int], np.ndarray]]:
    df = df.sort_values([score_column, "candidate_rank"], ascending=[False, True]).reset_index(drop=True)
    block_ids = df["video_id"].astype(int).to_numpy()
    scores = df[score_column].astype(float).to_numpy()
    path_ids = df["path_id"].astype(str).to_numpy()
    full_false = bool_array(df["is_unmatched"])
    observed = np.isin(path_ids, np.asarray(sorted(observed_paths), dtype=object))
    partial_null = ~observed
    rows = []
    selected_by_setting: dict[tuple[float, int, int], np.ndarray] = {}
    for seed in seeds:
        cal_mask, test_mask, cal_blocks = split_blocks(block_ids, seed)
        test_indices_all = np.flatnonzero(test_mask)
        order = np.argsort(scores[test_indices_all])[::-1]
        test_indices = test_indices_all[order]
        cal_null_mask = cal_mask & partial_null
        for alpha in alphas:
            evalues, diag = compute_evalues(scores, block_ids, cal_null_mask, test_indices, cal_blocks, alpha)
            max_observed_e = float(np.max(evalues)) if len(evalues) else None
            for M in budgets:
                pool_indices = test_indices[: min(M, len(test_indices))]
                pool_e = evalues[: len(pool_indices)]
                released, tau, margin, best_mass_ratio = scs_release_count(pool_e, alpha, M)
                if released:
                    local = np.argsort(pool_e)[::-1][:released]
                    selected_indices = pool_indices[local]
                    official_ftr = float(full_false[selected_indices].mean())
                    partial_utr = float(partial_null[selected_indices].mean())
                else:
                    selected_indices = np.asarray([], dtype=int)
                    official_ftr = 0.0
                    partial_utr = 0.0
                raw_ftr = float(full_false[pool_indices].mean()) if len(pool_indices) else 0.0
                selected_by_setting[(alpha, M, seed)] = selected_indices
                rows.append(
                    {
                        "alpha": alpha,
                        "seed": seed,
                        "K": M,
                        "released": int(released),
                        "official_proxy_FTR": official_ftr,
                        "partial_UTR_seen_by_PARC": partial_utr,
                        "raw_topK_official_proxy_FTR": raw_ftr,
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


def summarize_seed_results(seed_results: pd.DataFrame) -> pd.DataFrame:
    return (
        seed_results.groupby(["alpha", "K"], as_index=False)
        .agg(
            non_empty_seeds=("released", lambda s: int((s > 0).sum())),
            mean_release=("released", "mean"),
            max_release=("released", "max"),
            mean_official_proxy_FTR=("official_proxy_FTR", "mean"),
            max_official_proxy_FTR=("official_proxy_FTR", "max"),
            mean_raw_topK_official_proxy_FTR=("raw_topK_official_proxy_FTR", "mean"),
            mean_best_mass_ratio=("best_mass_ratio", "mean"),
            max_observed_e=("max_observed_e", "max"),
            required_e=("required_emax", "first"),
            dominant_empty_reason=("empty_reason", lambda s: s[s.astype(str) != ""].mode().iloc[0] if (s.astype(str) != "").any() else ""),
        )
    )


def choose_endpoint(summary: pd.DataFrame) -> tuple[float, int, str]:
    hierarchy = [
        (0.10, 50, "strict_primary"),
        (0.10, 25, "strict_fallback"),
        (0.20, 50, "operational_primary_k50"),
        (0.20, 100, "operational_primary_k100"),
        (0.20, 25, "diagnostic_low_volume"),
    ]
    for alpha, K, status in hierarchy:
        row = summary[(summary["alpha"] == alpha) & (summary["K"] == K)]
        if not row.empty and int(row.iloc[0]["non_empty_seeds"]) >= 18:
            return alpha, K, status
    available = summary[summary["non_empty_seeds"] > 0].copy()
    if available.empty:
        return 0.20, 50, "none_available"
    chosen = available.sort_values(["non_empty_seeds", "mean_release", "alpha", "K"], ascending=[False, False, True, True]).iloc[0]
    return float(chosen["alpha"]), int(chosen["K"]), "diagnostic_only_not_primary"


def make_release_audit(
    df: pd.DataFrame,
    selected_by_setting: dict[tuple[float, int, int], np.ndarray],
    alpha: float,
    K: int,
    seeds: list[int],
    n: int,
) -> pd.DataFrame:
    indices: list[int] = []
    for seed in seeds:
        indices.extend(int(i) for i in selected_by_setting.get((alpha, K, seed), np.asarray([], dtype=int)))
    if not indices:
        return pd.DataFrame(columns=df.columns)
    unique = df.iloc[sorted(set(indices))].copy()
    if len(unique) <= n:
        return unique.reset_index(drop=True)
    return round_robin_by_block(unique, n=n, per_block_cap=max(1, math.ceil(n / max(unique["video_id"].nunique(), 1))))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-universe", default="/home/waas/paper_experiments/outputs/iwildcam_animal_present_certification/gdino_animal/candidate_universe.csv")
    parser.add_argument("--out-dir", default="outputs/iwildcam_animal_human_audit")
    parser.add_argument("--source-name", default="GroundingDINO-SwinT animal-present fallback")
    parser.add_argument("--preferred-source-status", default="MegaDetector outputs not found locally; frozen GDINO animal-present source used as fallback")
    parser.add_argument("--old-audit-files", default="/home/waas/paper_experiments/outputs/iwildcam_release_certification/audit_batch_500/iwildcam_blind_audit_500_analysis_key.csv,/home/waas/paper_experiments/outputs/iwildcam_animal_present_certification/certification_M50_alpha0p20/audit_candidates_iwildcam_animal.csv,/home/waas/paper_experiments/outputs/iwildcam_animal_present_certification/certification_M50_alpha0p30/audit_candidates_iwildcam_animal.csv")
    parser.add_argument("--human-calibration-labels", default="")
    parser.add_argument("--calibration-n", type=int, default=2000)
    parser.add_argument("--release-audit-n", type=int, default=300)
    parser.add_argument("--raw-topk-audit-n", type=int, default=300)
    parser.add_argument("--temporal-chunks", type=int, default=5)
    parser.add_argument("--alphas", default="0.10,0.20")
    parser.add_argument("--budgets", default="25,50,100")
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = Path(args.candidate_universe)
    universe = pd.read_csv(candidate_path)
    universe = universe.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    universe = add_temporal_blocks(universe, chunks=args.temporal_chunks)
    universe = universe.sort_values(["score", "candidate_rank"], ascending=[False, True]).reset_index(drop=True)
    universe["candidate_rank"] = np.arange(1, len(universe) + 1)

    old_paths: set[str] = set()
    for item in [v for v in args.old_audit_files.split(",") if v.strip()]:
        path = Path(item)
        if path.exists():
            try:
                old_paths.update(pd.read_csv(path, usecols=["path_id"])["path_id"].astype(str))
            except Exception:
                continue
    available = universe[~universe["path_id"].astype(str).isin(old_paths)].copy()

    per_block_cap = max(2, math.ceil(args.calibration_n / max(available["video_id"].nunique(), 1)))
    calibration = round_robin_by_block(available, n=args.calibration_n, per_block_cap=per_block_cap)
    calibration["audit_id"] = [f"iwild-cal-{i:06d}" for i in range(1, len(calibration) + 1)]
    calibration["sample_set"] = "calibration_audit"
    calibration_blind = blind_columns(calibration, "calibration_audit")
    calibration_blind.to_csv(out_dir / "calibration_audit_blind_template.csv", index=False)
    official_proxy_initial(calibration).to_csv(out_dir / "calibration_audit_proxy_planning_only.csv", index=False)

    raw_topk = available.head(args.raw_topk_audit_n).copy()
    raw_topk["audit_id"] = [f"iwild-raw-{i:06d}" for i in range(1, len(raw_topk) + 1)]
    raw_topk["sample_set"] = "raw_topK_audit"
    blind_columns(raw_topk, "raw_topK_audit").to_csv(out_dir / "raw_topk_audit_blind_template.csv", index=False)
    official_proxy_initial(raw_topk).to_csv(out_dir / "raw_topk_audit_proxy_planning_only.csv", index=False)

    human_observed = load_human_verified(args.human_calibration_labels if args.human_calibration_labels else None)
    if human_observed:
        observed_paths = human_observed
        observed_source = "human_confirmed_verified_positives"
        paper_status = "human_confirmed_trial_ready_for_release_audit"
    else:
        observed_paths = set(calibration.loc[~bool_array(calibration["is_unmatched"]), "path_id"].astype(str))
        observed_source = "official_proxy_from_calibration_audit_for_planning_only"
        paper_status = "not_a_human_audited_flagship_until_human_fields_are_confirmed"

    alphas = parse_list(args.alphas, float)
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)
    seed_results, selected = run_parc_with_observed(universe, observed_paths, alphas, budgets, seeds, score_column="score")
    seed_results["observed_positive_source"] = observed_source
    seed_results["paper_status"] = paper_status
    seed_results["source_name"] = args.source_name
    seed_results.to_csv(out_dir / "table_iwildcam_human_audit_proxy_seed_results.csv", index=False)
    summary = summarize_seed_results(seed_results)
    summary["observed_positive_source"] = observed_source
    summary["paper_status"] = paper_status
    summary["source_name"] = args.source_name
    summary["human_FTR"] = ""
    summary["conservative_human_FTR"] = ""
    summary["human_audit_status"] = "requires_human_confirmation"
    summary.to_csv(out_dir / "table_iwildcam_human_audit_proxy_primary_results.csv", index=False)

    endpoint_alpha, endpoint_K, endpoint_status = choose_endpoint(summary)
    release_candidates = make_release_audit(universe, selected, endpoint_alpha, endpoint_K, seeds, args.release_audit_n)
    if not release_candidates.empty:
        release_candidates["audit_id"] = [f"iwild-rel-{i:06d}" for i in range(1, len(release_candidates) + 1)]
        release_candidates["sample_set"] = f"release_audit_alpha{str(endpoint_alpha).replace('.', 'p')}_K{endpoint_K}"
    release_blind = blind_columns(release_candidates, "release_audit") if not release_candidates.empty else add_human_fields(pd.DataFrame(columns=["audit_id", "sample_set", "path_id"]))
    release_blind.to_csv(out_dir / "release_audit_blind_template.csv", index=False)
    if not release_candidates.empty:
        official_proxy_initial(release_candidates).to_csv(out_dir / "release_audit_proxy_planning_only.csv", index=False)

    rng = np.random.default_rng(20260515)
    randomized = universe.copy()
    randomized["score"] = rng.random(len(randomized))
    random_seed_results, _ = run_parc_with_observed(randomized, observed_paths, alphas, budgets, seeds, score_column="score")
    random_summary = summarize_seed_results(random_seed_results)
    random_summary["control"] = "random_score_control"
    random_summary["paper_status"] = paper_status
    random_summary.to_csv(out_dir / "table_iwildcam_random_score_control.csv", index=False)

    block_summary = (
        universe.groupby("video_id", as_index=False)
        .agg(
            location_id=("location_id", "first"),
            temporal_chunk=("_temporal_chunk", "first"),
            candidates=("path_id", "count"),
            official_supported=("is_unmatched", lambda s: int((~pd.Series(s).astype(str).str.lower().isin(["true", "1", "yes"])).sum())),
            max_score=("score", "max"),
        )
    )
    block_summary["calibration_audit_candidates"] = block_summary["video_id"].map(calibration.groupby("video_id").size()).fillna(0).astype(int)
    block_summary.to_csv(out_dir / "table_iwildcam_block_coverage.csv", index=False)

    protocol = pd.DataFrame(
        [
            {
                "dataset": "iWildCam2022",
                "source_name": args.source_name,
                "preferred_source_status": args.preferred_source_status,
                "target": "animal_present_detection",
                "block_definition": "camera_location_x_temporal_chunk",
                "temporal_chunks_per_location": args.temporal_chunks,
                "candidate_rows": len(universe),
                "locations": universe["location_id"].nunique(),
                "blocks": universe["video_id"].nunique(),
                "calibration_audit_n_requested": args.calibration_n,
                "calibration_audit_n_written": len(calibration_blind),
                "release_audit_n_written": len(release_blind),
                "raw_topK_audit_n_written": len(raw_topk),
                "endpoint_alpha_for_release_audit_template": endpoint_alpha,
                "endpoint_K_for_release_audit_template": endpoint_K,
                "endpoint_status": endpoint_status,
                "paper_status": paper_status,
            }
        ]
    )
    protocol.to_csv(out_dir / "table_iwildcam_human_audit_protocol_summary.csv", index=False)

    closeout = {
        "status": "prepared",
        "paper_status": paper_status,
        "go_no_go": "pending_human_audit",
        "source_name": args.source_name,
        "preferred_source_status": args.preferred_source_status,
        "candidate_universe": "external_iwildcam_candidate_universe.csv",
        "candidate_universe_sha256": sha256_file(candidate_path),
        "candidate_rows": int(len(universe)),
        "locations": int(universe["location_id"].nunique()),
        "blocks": int(universe["video_id"].nunique()),
        "calibration_audit_rows": int(len(calibration_blind)),
        "release_audit_rows": int(len(release_blind)),
        "raw_topk_audit_rows": int(len(raw_topk)),
        "selected_endpoint_for_release_audit_template": {
            "alpha": endpoint_alpha,
            "K": endpoint_K,
            "endpoint_status": endpoint_status,
        },
        "human_claim_rule": "Human FTR and flagship claims require filled human_* fields; proxy planning tables are not paper-facing human audit evidence.",
    }
    with (out_dir / "iwildcam_animal_human_audit_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(closeout, handle, indent=2)

    report = f"""# iWildCam Animal-Present Prospective Human-Audit Closeout

Status: prepared for prospective human audit.

Paper status: `{paper_status}`.

This package freezes a candidate-disjoint ecology-domain trial for animal-present
camera-trap detections. The preferred source is MegaDetector or another frozen
domain-specific animal detector; current local execution used:

`{args.source_name}`

Source note: {args.preferred_source_status}

Official labels are used only in proxy planning tables. They must not be
reported as human-audited FTR. The blind calibration and release templates are
the inputs for human review.

Prepared assets:

- calibration audit rows: {len(calibration_blind)}
- raw top-K audit rows: {len(raw_topk)}
- release audit template rows: {len(release_blind)}
- block definition: camera location x {args.temporal_chunks} temporal chunks
- blocks: {universe['video_id'].nunique()}

Go/no-go remains pending until human-confirmed calibration and release labels
are supplied and rerun through the same predeclared endpoint hierarchy.
"""
    (out_dir / "IWILDCAM_ANIMAL_HUMAN_AUDIT_CLOSEOUT.md").write_text(report, encoding="utf-8")
    print(json.dumps(closeout, indent=2), flush=True)


if __name__ == "__main__":
    main()
