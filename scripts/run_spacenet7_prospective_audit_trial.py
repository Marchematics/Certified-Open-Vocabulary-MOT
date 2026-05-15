#!/usr/bin/env python3
"""Prepare a prospective SpaceNet 7 human-audit release trial.

This script freezes a candidate-disjoint prospective audit package.  It trains
a lightweight learned-geometry scorer on AOIs disjoint from the certification
AOIs, generates blind calibration/release/raw-audit sheets, and writes proxy
planning tables.  Human labels are intentionally blank; official labels are
used only for planning diagnostics and must not be reported as human audit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


FEATURES = [
    "bbox_iou",
    "centroid_distance_score",
    "area_ratio",
    "base_geometry_score",
    "deterministic_noise",
    "frame_start",
    "frame_end",
]

FORBIDDEN = {
    "source_building_id",
    "target_building_id",
    "matched_gt",
    "is_matched_to_gt",
    "is_unmatched",
    "human_label",
    "human_verified_positive_for_calibration",
    "released",
}


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


def compute_evalues(scores: np.ndarray, block_ids: np.ndarray, cal_null_mask: np.ndarray, test_indices: np.ndarray, cal_blocks: list[int], alpha: float) -> tuple[np.ndarray, dict]:
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


def blind_columns(frame: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "audit_id",
        "sample_set",
        "aoi",
        "video_id",
        "source_year",
        "source_month",
        "target_year",
        "target_month",
        "bbox_iou",
        "centroid_distance_score",
        "area_ratio",
        "base_geometry_score",
        "score",
        "path_id",
    ]
    return add_human_fields(frame[keep].copy())


def official_proxy_initial(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_human_fields(frame.copy())
    same = ~bool_array(out["is_unmatched"])
    out["official_proxy_label_for_planning_only"] = np.where(same, "same_building", "not_same_building")
    out["official_proxy_verified_positive_for_planning_only"] = np.where(same, "yes", "no")
    out["official_proxy_note"] = "planning proxy only; human fields control paper-facing real audit"
    return out


def run_parc_with_observed(df: pd.DataFrame, observed_ranks: set[int], alphas: list[float], budgets: list[int], seeds: list[int]) -> tuple[pd.DataFrame, dict[tuple[float, int, int], np.ndarray]]:
    df = df.sort_values(["candidate_rank", "score"], ascending=[True, False]).reset_index(drop=True)
    block_ids = df["video_id"].astype(int).to_numpy()
    scores = df["score"].astype(float).to_numpy()
    ranks = df["candidate_rank"].astype(int).to_numpy()
    full_false = bool_array(df["is_unmatched"])
    observed = np.isin(ranks, np.asarray(sorted(observed_ranks), dtype=int))
    partial_null = ~observed
    rows = []
    selected_by_setting: dict[tuple[float, int, int], np.ndarray] = {}
    for seed in seeds:
        cal_mask, test_mask, cal_blocks = split_blocks(block_ids, seed)
        test_indices = np.flatnonzero(test_mask)
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
                        "M": M,
                        "released": int(released),
                        "official_proxy_FTR": official_ftr,
                        "partial_UTR_seen_by_PARC": partial_utr,
                        "raw_topM_official_proxy_FTR": raw_ftr,
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


def choose_endpoint(seed_results: pd.DataFrame) -> tuple[float, int, str]:
    hierarchy = [
        (0.10, 50, "strict_primary"),
        (0.10, 25, "strict_fallback"),
        (0.20, 50, "operational_primary"),
    ]
    for alpha, M, status in hierarchy:
        row = seed_results[(seed_results["alpha"] == alpha) & (seed_results["M"] == M)]
        if not row.empty and int((row["released"] > 0).sum()) >= 18:
            return alpha, M, status
    available = (
        seed_results.groupby(["alpha", "M"], as_index=False)
        .agg(nonempty=("released", lambda s: int((s > 0).sum())), mean_release=("released", "mean"))
        .query("nonempty > 0")
    )
    if available.empty:
        return 0.20, 50, "none_available"
    chosen = available.sort_values(["nonempty", "mean_release", "alpha", "M"], ascending=[False, False, True, True]).iloc[0]
    return float(chosen["alpha"]), int(chosen["M"]), "diagnostic_only_not_primary"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-universe", default="/home/waas/paper_experiments/outputs/spacenet7_building_links/universe_geometry_w35_aoi20/candidate_universe.csv")
    parser.add_argument("--old-audit-manifest", default="outputs/spacenet7_real_audit/audit_manifest.csv")
    parser.add_argument("--out-dir", default="outputs/spacenet7_prospective_audit")
    parser.add_argument("--calibration-n", type=int, default=1200)
    parser.add_argument("--release-audit-n", type=int, default=300)
    parser.add_argument("--raw-topk-audit-n", type=int, default=250)
    parser.add_argument("--train-aoi-count", type=int, default=10)
    parser.add_argument("--train-sample-per-class", type=int, default=250000)
    parser.add_argument("--alphas", default="0.10,0.20")
    parser.add_argument("--budgets", default="25,50,100")
    parser.add_argument("--seeds", default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = Path(args.candidate_universe)
    usecols = sorted(set(FEATURES + [
        "dataset",
        "domain",
        "generator",
        "aoi",
        "video_id",
        "path_id",
        "source_building_id",
        "target_building_id",
        "source_year",
        "source_month",
        "target_year",
        "target_month",
        "score",
        "candidate_rank",
        "is_unmatched",
    ]))
    df = pd.read_csv(candidate_path, usecols=usecols)
    df = df.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    old_paths = set()
    old_manifest = Path(args.old_audit_manifest)
    if old_manifest.exists():
        old_paths = set(pd.read_csv(old_manifest, usecols=["path_id"])["path_id"].astype(str))

    aois = sorted(df["aoi"].astype(str).unique())
    train_aois = set(aois[: args.train_aoi_count])
    eval_aois = set(aois[args.train_aoi_count :])
    train = df[df["aoi"].isin(train_aois)].copy()
    eval_df = df[df["aoi"].isin(eval_aois)].copy()
    if train.empty or eval_df.empty:
        raise RuntimeError("AOI split produced an empty side.")

    train["_true"] = ~bool_array(train["is_unmatched"])
    eval_df["_true"] = ~bool_array(eval_df["is_unmatched"])
    rng = np.random.default_rng(20260515)
    pos_idx = np.flatnonzero(train["_true"].to_numpy())
    neg_idx = np.flatnonzero(~train["_true"].to_numpy())
    n_pos = min(len(pos_idx), args.train_sample_per_class)
    n_neg = min(len(neg_idx), args.train_sample_per_class)
    chosen = np.concatenate([
        rng.choice(pos_idx, n_pos, replace=False),
        rng.choice(neg_idx, n_neg, replace=False),
    ])
    rng.shuffle(chosen)
    X_train = train.iloc[chosen][FEATURES].to_numpy(dtype=np.float32)
    y_train = train.iloc[chosen]["_true"].to_numpy(dtype=bool)
    X_eval = eval_df[FEATURES].to_numpy(dtype=np.float32)
    y_eval = eval_df["_true"].to_numpy(dtype=bool)

    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs"))
    model.fit(X_train, y_train)
    train_scores = model.predict_proba(X_train)[:, 1]
    eval_scores = model.predict_proba(X_eval)[:, 1]
    eval_df["score"] = eval_scores
    eval_df["generator"] = "spacenet7_learned_geometry"
    eval_df = eval_df.sort_values(["score", "path_id"], ascending=[False, True]).reset_index(drop=True)
    eval_df["candidate_rank"] = np.arange(1, len(eval_df) + 1)

    candidate_universe_out = out_dir / "candidate_universe_learned_geometry_eval.csv"
    eval_df.drop(columns=["_true"], errors="ignore").to_csv(candidate_universe_out, index=False)

    review_pool = eval_df[~eval_df["path_id"].astype(str).isin(old_paths)].copy()
    per_block_cap = max(1, int(math.ceil(args.calibration_n / max(1, review_pool["video_id"].nunique()))) + 4)
    calibration = round_robin_by_block(review_pool, args.calibration_n, per_block_cap)
    calibration.insert(0, "audit_id", [make_audit_id("SPCAL", i + 1) for i in range(len(calibration))])
    calibration.insert(1, "sample_set", "prospective_calibration_audit")
    calibration_blind = blind_columns(calibration)
    calibration_initial = official_proxy_initial(calibration)
    calibration_blind.to_csv(out_dir / "calibration_audit_blind_template.csv", index=False)
    calibration_initial.to_csv(out_dir / "calibration_audit_official_proxy_initial_review.csv", index=False)

    observed_ranks = set(calibration.loc[~bool_array(calibration["is_unmatched"]), "candidate_rank"].astype(int).tolist())
    alphas = parse_list(args.alphas, float)
    budgets = parse_list(args.budgets, int)
    seeds = parse_list(args.seeds, int)
    seed_results, selected = run_parc_with_observed(eval_df, observed_ranks, alphas, budgets, seeds)
    seed_results.to_csv(out_dir / "table_spacenet7_prospective_proxy_seed_results.csv", index=False)

    release_alpha, release_M, endpoint_status = choose_endpoint(seed_results)
    unique_indices = []
    for seed in seeds:
        unique_indices.extend(selected.get((release_alpha, release_M, seed), np.asarray([], dtype=int)).tolist())
    unique_indices = sorted(set(unique_indices), key=lambda idx: int(eval_df.iloc[idx]["candidate_rank"]))
    release = eval_df.iloc[unique_indices].copy()
    release = release[~release["path_id"].astype(str).isin(old_paths)]
    release = release.head(args.release_audit_n).reset_index(drop=True)
    release.insert(0, "audit_id", [make_audit_id("SPREL", i + 1) for i in range(len(release))])
    release.insert(1, "sample_set", "prospective_release_audit")
    blind_columns(release).to_csv(out_dir / "release_audit_blind_template.csv", index=False)
    official_proxy_initial(release).to_csv(out_dir / "release_audit_official_proxy_initial_review.csv", index=False)

    used_paths = set(calibration["path_id"].astype(str)) | set(release["path_id"].astype(str)) | old_paths
    raw = eval_df[~eval_df["path_id"].astype(str).isin(used_paths)].head(args.raw_topk_audit_n).copy().reset_index(drop=True)
    raw.insert(0, "audit_id", [make_audit_id("SPRAW", i + 1) for i in range(len(raw))])
    raw.insert(1, "sample_set", "prospective_raw_topk_audit")
    blind_columns(raw).to_csv(out_dir / "raw_topk_audit_blind_template.csv", index=False)
    official_proxy_initial(raw).to_csv(out_dir / "raw_topk_audit_official_proxy_initial_review.csv", index=False)

    manifest = pd.concat(
        [
            calibration.assign(audit_role="calibration"),
            release.assign(audit_role="release"),
            raw.assign(audit_role="raw_topk"),
        ],
        ignore_index=True,
    )
    manifest.drop(columns=["is_unmatched"], errors="ignore").to_csv(out_dir / "audit_manifest.csv", index=False)

    grouped = seed_results.groupby(["alpha", "M"], as_index=False).agg(
        non_empty_seeds=("released", lambda s: int((s > 0).sum())),
        mean_release=("released", "mean"),
        official_proxy_FTR=("official_proxy_FTR", "mean"),
        raw_topM_official_proxy_FTR=("raw_topM_official_proxy_FTR", "mean"),
        mean_mass_ratio=("best_mass_ratio", "mean"),
        mean_max_observed_e=("max_observed_e", "mean"),
        required_e=("required_emax", "mean"),
    )
    grouped["paper_status"] = "proxy_planning_only_requires_human_confirmation"
    grouped.to_csv(out_dir / "table_spacenet7_prospective_proxy_primary_results.csv", index=False)

    leakage = pd.DataFrame(
        [
            {
                "check_name": "aoi_disjoint_learned_geometry_split",
                "status": "passed",
                "train_aois": len(train_aois),
                "eval_aois": len(eval_aois),
                "train_eval_overlap": "none",
                "features_used": ",".join(FEATURES),
                "forbidden_fields_used": "no",
                "normalization_fit_scope": "training_AOIs_only",
                "human_labels_used_for_training": "no",
                "held_out_labels_used": "planning_proxy_and_later_FTR_only",
                "train_auc_sample": float(roc_auc_score(y_train, train_scores)),
                "eval_auc": float(roc_auc_score(y_eval, eval_scores)),
                "train_average_precision_sample": float(average_precision_score(y_train, train_scores)),
                "eval_average_precision": float(average_precision_score(y_eval, eval_scores)),
            }
        ]
    )
    leakage.to_csv(out_dir / "table_spacenet7_prospective_leakage_audit.csv", index=False)

    summary = {
        "status": "review_ready_requires_human_confirmation",
        "protocol": "docs/spacenet7_prospective_audit_flagship_protocol.md",
        "candidate_universe_sha256": sha256_file(candidate_path),
        "learned_eval_candidate_universe_sha256": sha256_file(candidate_universe_out),
        "old_audit_candidate_exclusion_count": len(old_paths),
        "train_aois": sorted(train_aois),
        "eval_aois": sorted(eval_aois),
        "eval_rows": int(len(eval_df)),
        "calibration_audit_rows": int(len(calibration)),
        "release_audit_rows": int(len(release)),
        "raw_topk_audit_rows": int(len(raw)),
        "release_audit_endpoint_alpha": release_alpha,
        "release_audit_endpoint_M": release_M,
        "release_audit_endpoint_status": endpoint_status,
        "paper_status": "not_a_human_audited_flagship_until_human_fields_are_confirmed",
    }
    (out_dir / "spacenet7_prospective_audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pd.DataFrame([summary]).drop(columns=["train_aois", "eval_aois"], errors="ignore").to_csv(out_dir / "table_protocol_summary.csv", index=False)
    (out_dir / "RUN_REPORT.md").write_text(
        "# SpaceNet 7 Prospective Audit Trial\n\n"
        "Status: review-ready. Human labels are blank and must be filled before any human-audited FTR claim.\n\n"
        f"- Train AOIs: {len(train_aois)}\n"
        f"- Evaluation AOIs: {len(eval_aois)}\n"
        f"- Calibration audit rows: {len(calibration)}\n"
        f"- Release audit rows: {len(release)}\n"
        f"- Raw top-K audit rows: {len(raw)}\n"
        f"- Proxy release-audit endpoint: alpha={release_alpha}, K={release_M}, status={endpoint_status}\n\n"
        "The `official_proxy_*` files are only planning aids. Paper-facing real-audit evidence must be computed from the `human_*` fields after review.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
