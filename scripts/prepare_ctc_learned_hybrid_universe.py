#!/usr/bin/env python3
"""Prepare an AI-assisted learned-hybrid CTC link candidate universe.

The existing CTC positive result uses a structured/geometric linker.  This
script freezes a lightweight learned scorer on sequence-disjoint CTC training
links and writes a held-out candidate universe for PARC certification.  The
learned score uses both geometric link features and local image/crop appearance
statistics, while the held-out full labels are retained only for downstream
actual-FTR evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import tifffile
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


GEOMETRY_FEATURES = [
    "link_distance_score",
    "bbox_iou",
    "area_ratio",
    "source_area",
    "target_area",
    "path_length",
    "frame_start",
]

LEAKAGE_COLUMNS = {
    "matched_gt_id",
    "matched_iou",
    "temporal_overlap",
    "matched_frames",
    "is_matched_to_gt",
    "is_unmatched",
    "audit_label",
    "verified_positive_for_calibration",
    "source_gt_label",
    "target_gt_label",
    "source_gt_purity",
    "target_gt_purity",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


@lru_cache(maxsize=256)
def load_normalized_image(path_string: str) -> np.ndarray:
    image = tifffile.imread(path_string).astype(np.float32)
    if image.ndim == 3:
        image = image.mean(axis=-1)
    lo, hi = np.percentile(image, [1.0, 99.0])
    if not np.isfinite(hi - lo) or hi <= lo:
        hi = float(image.max()) if image.size else 1.0
        lo = float(image.min()) if image.size else 0.0
    denom = max(hi - lo, 1e-6)
    return np.clip((image - lo) / denom, 0.0, 1.0)


def resolve_image_path(ctc_root: Path, relative: str) -> Path:
    path = ctc_root / relative
    if path.suffix:
        return path
    for suffix in [".tif", ".tiff", ".png"]:
        candidate = path.with_suffix(suffix)
        if candidate.exists():
            return candidate
    return path.with_suffix(".tif")


def resized_crop_vector(crop: np.ndarray, size: int = 16) -> np.ndarray:
    if crop.size == 0:
        return np.zeros(size * size, dtype=np.float32)
    h, w = crop.shape[:2]
    ys = np.linspace(0, max(h - 1, 0), size).round().astype(int)
    xs = np.linspace(0, max(w - 1, 0), size).round().astype(int)
    return crop[np.ix_(ys, xs)].astype(np.float32).reshape(-1)


def crop_stats(row: pd.Series, ctc_root: Path) -> dict:
    image_path = resolve_image_path(ctc_root, str(row["image_path"]))
    image = load_normalized_image(str(image_path))
    x = int(max(0, row["bbox_x"]))
    y = int(max(0, row["bbox_y"]))
    w = int(max(1, row["bbox_w"]))
    h = int(max(1, row["bbox_h"]))
    y2 = min(image.shape[0], y + h)
    x2 = min(image.shape[1], x + w)
    crop = image[y:y2, x:x2]
    if crop.size == 0:
        crop = image[max(0, min(y, image.shape[0] - 1)) : max(0, min(y, image.shape[0] - 1)) + 1,
                     max(0, min(x, image.shape[1] - 1)) : max(0, min(x, image.shape[1] - 1)) + 1]
    vec = resized_crop_vector(crop)
    return {
        "node_key": row["node_key"],
        "crop_mean": float(np.mean(crop)),
        "crop_std": float(np.std(crop)),
        "crop_p10": float(np.percentile(crop, 10.0)),
        "crop_p90": float(np.percentile(crop, 90.0)),
        "crop_vec": vec,
    }


def make_node_features(nodes: pd.DataFrame, ctc_root: Path) -> tuple[pd.DataFrame, dict[str, np.ndarray]]:
    key_cols = ["image_path", "bbox_x", "bbox_y", "bbox_w", "bbox_h"]
    unique = nodes[key_cols].drop_duplicates().copy()
    unique["node_key"] = unique[key_cols].astype(str).agg("|".join, axis=1)
    records: list[dict] = []
    vectors: dict[str, np.ndarray] = {}
    for _, row in unique.iterrows():
        record = crop_stats(row, ctc_root)
        vectors[str(record["node_key"])] = record.pop("crop_vec")
        records.append(record)
    node_features = pd.DataFrame(records)
    return node_features, vectors


def safe_corr(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    aa = vec_a.astype(np.float32) - float(np.mean(vec_a))
    bb = vec_b.astype(np.float32) - float(np.mean(vec_b))
    denom = float(np.linalg.norm(aa) * np.linalg.norm(bb))
    if denom <= 1e-8:
        return 0.0
    return float(np.dot(aa, bb) / denom)


def build_feature_table(universe: pd.DataFrame, nodes: pd.DataFrame, ctc_root: Path) -> pd.DataFrame:
    key_cols = ["image_path", "bbox_x", "bbox_y", "bbox_w", "bbox_h"]
    nodes = nodes.copy()
    nodes["node_key"] = nodes[key_cols].astype(str).agg("|".join, axis=1)
    node_features, vectors = make_node_features(nodes, ctc_root)
    enriched = nodes.merge(node_features, on="node_key", how="left")
    node0 = enriched[enriched["node_index"] == 0].copy()
    node1 = enriched[enriched["node_index"] == 1].copy()
    keep = ["path_id", "node_key", "crop_mean", "crop_std", "crop_p10", "crop_p90"]
    feat = universe[["path_id", "ctc_dataset"] + GEOMETRY_FEATURES].copy()
    feat = feat.merge(node0[keep].rename(columns={c: f"src_{c}" for c in keep if c != "path_id"}), on="path_id", how="left")
    feat = feat.merge(node1[keep].rename(columns={c: f"tgt_{c}" for c in keep if c != "path_id"}), on="path_id", how="left")
    for stat in ["crop_mean", "crop_std", "crop_p10", "crop_p90"]:
        feat[f"absdiff_{stat}"] = (feat[f"src_{stat}"] - feat[f"tgt_{stat}"]).abs()
    node_keys = feat[["src_node_key", "tgt_node_key"]].fillna("").astype(str).to_numpy()
    feat["appearance_crop_corr"] = [
        safe_corr(vectors.get(src, np.zeros(256, dtype=np.float32)), vectors.get(tgt, np.zeros(256, dtype=np.float32)))
        for src, tgt in node_keys
    ]
    feat["log_source_area"] = np.log1p(pd.to_numeric(feat["source_area"], errors="coerce").fillna(0.0))
    feat["log_target_area"] = np.log1p(pd.to_numeric(feat["target_area"], errors="coerce").fillna(0.0))
    feat["abs_log_area_diff"] = (feat["log_source_area"] - feat["log_target_area"]).abs()
    numeric = [c for c in feat.columns if c not in {"path_id", "ctc_dataset", "src_node_key", "tgt_node_key"}]
    feat[numeric] = feat[numeric].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(0.0)
    dataset_dummies = pd.get_dummies(feat["ctc_dataset"], prefix="dataset", dtype=float)
    feat = pd.concat([feat, dataset_dummies], axis=1)
    return feat


def choose_feature_columns(features: pd.DataFrame) -> list[str]:
    skip = {"path_id", "ctc_dataset", "src_node_key", "tgt_node_key"}
    return [c for c in features.columns if c not in skip]


def score_universe(args: argparse.Namespace) -> dict:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    candidate_universe_path = Path(args.candidate_universe)
    candidate_nodes_path = Path(args.candidate_nodes)
    ctc_root = Path(args.ctc_root)

    universe = pd.read_csv(candidate_universe_path)
    nodes = pd.read_csv(candidate_nodes_path)
    universe["sequence_id"] = universe["sequence_id"].astype(int)
    universe["_full_true"] = ~bool_series(universe["is_unmatched"])

    used_path_ids = set(universe["path_id"].astype(str))
    nodes = nodes[nodes["path_id"].astype(str).isin(used_path_ids)].copy()
    feature_table = build_feature_table(universe, nodes, ctc_root)
    feature_cols = choose_feature_columns(feature_table)
    merged = universe[["path_id", "sequence_id", "_full_true"]].merge(feature_table[["path_id"] + feature_cols], on="path_id", how="left")
    merged[feature_cols] = merged[feature_cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)

    train_mask = merged["sequence_id"].isin(args.train_sequences)
    eval_mask = merged["sequence_id"].isin(args.eval_sequences)
    if train_mask.sum() == 0 or eval_mask.sum() == 0:
        raise RuntimeError("Train/eval sequence split produced an empty side.")
    X_train = merged.loc[train_mask, feature_cols].to_numpy(dtype=np.float32)
    y_train = merged.loc[train_mask, "_full_true"].to_numpy(dtype=bool)
    X_eval = merged.loc[eval_mask, feature_cols].to_numpy(dtype=np.float32)
    y_eval = merged.loc[eval_mask, "_full_true"].to_numpy(dtype=bool)

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(max_iter=1000, class_weight="balanced", solver="lbfgs", n_jobs=1),
    )
    model.fit(X_train, y_train)
    eval_score = model.predict_proba(X_eval)[:, 1]
    train_score = model.predict_proba(X_train)[:, 1]
    universe_eval = universe.loc[eval_mask].copy()
    universe_eval["score"] = eval_score
    universe_eval["association_score"] = eval_score
    universe_eval["objectness"] = pd.Series(eval_score).rank(pct=True).to_numpy()
    universe_eval["score_source"] = "ctc_learned_hybrid_appearance_sequence_disjoint"
    if args.eval_frame_window > 0:
        dataset_codes = {name: idx for idx, name in enumerate(sorted(universe_eval["ctc_dataset"].unique()))}
        universe_eval["video_id"] = (
            universe_eval["ctc_dataset"].map(dataset_codes).astype(int) * 100000
            + universe_eval["sequence_id"].astype(int) * 10000
            + (universe_eval["frame_start"].astype(int) // int(args.eval_frame_window))
        )
    universe_eval = universe_eval.sort_values(["score", "path_id"], ascending=[False, True]).reset_index(drop=True)
    universe_eval["candidate_rank"] = np.arange(1, len(universe_eval) + 1)
    universe_eval = universe_eval.drop(columns=["_full_true"], errors="ignore")

    eval_path_ids = set(universe_eval["path_id"].astype(str))
    nodes_eval = nodes[nodes["path_id"].astype(str).isin(eval_path_ids)].copy()
    nodes_eval = nodes_eval.merge(universe_eval[["path_id", "video_id", "score"]], on="path_id", how="left", suffixes=("", "_learned"))
    nodes_eval["video_id"] = nodes_eval["video_id_learned"].astype(int)
    nodes_eval["score"] = nodes_eval["score_learned"].astype(float)
    nodes_eval = nodes_eval.drop(columns=["video_id_learned", "score_learned"], errors="ignore")

    universe_out = out_dir / "candidate_universe.csv"
    nodes_out = out_dir / "candidate_nodes.csv"
    scores_out = out_dir / "candidate_scores.csv"
    universe_eval.to_csv(universe_out, index=False)
    nodes_eval.to_csv(nodes_out, index=False)
    universe_eval[["path_id", "score", "objectness", "semantic_margin", "temporal_stability", "association_score", "score_source"]].to_csv(scores_out, index=False)

    def metric_or_none(fn, y, s):
        try:
            return float(fn(y, s))
        except Exception:
            return None

    report = {
        "status": "completed",
        "source": "ctc_learned_hybrid_appearance_sequence_disjoint",
        "train_sequences": args.train_sequences,
        "eval_sequences": args.eval_sequences,
        "eval_frame_window": args.eval_frame_window,
        "candidate_universe_input_sha256": sha256_file(candidate_universe_path),
        "candidate_nodes_input_sha256": sha256_file(candidate_nodes_path),
        "rows_train": int(train_mask.sum()),
        "rows_eval": int(eval_mask.sum()),
        "train_positive_rate": float(y_train.mean()),
        "eval_positive_rate": float(y_eval.mean()),
        "train_auc": metric_or_none(roc_auc_score, y_train, train_score),
        "eval_auc": metric_or_none(roc_auc_score, y_eval, eval_score),
        "train_average_precision": metric_or_none(average_precision_score, y_train, train_score),
        "eval_average_precision": metric_or_none(average_precision_score, y_eval, eval_score),
        "feature_count": len(feature_cols),
        "features_used": [c for c in feature_cols if c not in LEAKAGE_COLUMNS],
        "forbidden_leakage_columns_not_used": sorted(LEAKAGE_COLUMNS.intersection(feature_cols)) == [],
        "outputs": {
            "candidate_universe": str(universe_out),
            "candidate_nodes": str(nodes_out),
            "candidate_scores": str(scores_out),
        },
        "output_sha256": {
            "candidate_universe": sha256_file(universe_out),
            "candidate_nodes": sha256_file(nodes_out),
            "candidate_scores": sha256_file(scores_out),
        },
    }
    with (out_dir / "CTC_LEARNED_HYBRID_UNIVERSE_REPORT.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    pd.DataFrame([report]).drop(columns=["features_used", "outputs", "output_sha256"], errors="ignore").to_csv(
        out_dir / "table_ctc_learned_model_report.csv", index=False
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-universe", required=True)
    parser.add_argument("--candidate-nodes", required=True)
    parser.add_argument("--ctc-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--train-sequences", type=int, nargs="+", default=[1])
    parser.add_argument("--eval-sequences", type=int, nargs="+", default=[2])
    parser.add_argument("--eval-frame-window", type=int, default=5)
    args = parser.parse_args()
    report = score_universe(args)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
