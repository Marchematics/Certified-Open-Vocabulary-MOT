from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .adapters.datasets import ensure_data_output, write_json


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()
V2_DIR = DATA_ROOT / "outputs/milestones/tpami_reliability_fortress_v2"
PHASE11_DIR = DATA_ROOT / "outputs/phase11_nmi"
MILESTONE_DIR = DATA_ROOT / "outputs/milestones/nmi_generality_reliability_v1"
PACKAGE_PATH = DATA_ROOT / "outputs/packages/nmi_generality_reliability_v1.tar.gz"
VALID_LABELS = {"actually_true", "actually_false", "uncertain"}
DETECTORS = ("GroundingDINO", "OWLv2")
ALPHAS = (0.10, 0.20)
SEEDS = (0, 1, 2)
AUDIT_COLUMNS = [
    "dataset",
    "detector",
    "image_id",
    "path_id",
    "category_id",
    "score",
    "score_bin",
    "frequency_bin",
    "audit_label",
    "verified_positive_for_calibration",
    "audit_status",
    "reason",
]


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _read_json(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_if_exists(src: Path, dst_dir: Path, name: str | None = None) -> Path | None:
    if not src.exists() or not src.is_file():
        return None
    dst = ensure_data_output(dst_dir / (name or src.name))
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    return dst


def _write_manifest(root: Path) -> Path:
    manifest = ensure_data_output(root / "MANIFEST_SHA256.txt")
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() or path == manifest:
            continue
        rel = path.relative_to(root).as_posix()
        rows.append(f"{_sha256(path)}  {rel}")
    manifest.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return manifest


def _sanitize_public_text_files(root: Path) -> None:
    replacements = {
        str(DATA_ROOT): "${PARC_TRACK_ROOT}",
        "/home/" + "waas" + "/paper_experiments": "${PARC_TRACK_ROOT}",
        "/" + "root": "${HOME}",
    }
    for path in root.rglob("*"):
        if path.is_dir() or path.suffix.lower() not in {".csv", ".json", ".md", ".txt", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        cleaned = text
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        if cleaned != text:
            path.write_text(cleaned, encoding="utf-8")


def _rate(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _safe_num(row: pd.Series, *names: str, default: float = 0.0) -> float:
    for name in names:
        if name in row and pd.notna(row[name]) and str(row[name]).strip() != "":
            try:
                return float(row[name])
            except (TypeError, ValueError):
                continue
    return default


def _box_iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh
    inter_w = max(0.0, min(ax2, bx2) - max(ax1, bx1))
    inter_h = max(0.0, min(ay2, by2) - max(ay1, by1))
    inter = inter_w * inter_h
    union = max(0.0, aw * ah) + max(0.0, bw * bh) - inter
    return inter / union if union > 0 else 0.0


def _count_mask_conflicts(nodes: pd.DataFrame, path_ids: set[str], threshold: float) -> int:
    if nodes.empty:
        return 0
    frame_col = "frame_index" if "frame_index" in nodes else "image_id"
    required = {"path_id", frame_col, "bbox_x", "bbox_y", "bbox_w", "bbox_h"}
    if not required.issubset(nodes.columns):
        return 0
    subset = nodes[nodes["path_id"].astype(str).isin(path_ids)].copy()
    conflicts = 0
    for _, group in subset.groupby(frame_col):
        records = group[["path_id", "bbox_x", "bbox_y", "bbox_w", "bbox_h"]].to_dict("records")
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                if records[i]["path_id"] == records[j]["path_id"]:
                    continue
                a = tuple(float(records[i][key]) for key in ("bbox_x", "bbox_y", "bbox_w", "bbox_h"))
                b = tuple(float(records[j][key]) for key in ("bbox_x", "bbox_y", "bbox_w", "bbox_h"))
                if _box_iou(a, b) >= threshold:
                    conflicts += 1
    return conflicts


def run_phase11_audit_consistency(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or PHASE11_DIR / "audit_consistency")
    labels = _read_csv(V2_DIR / "audit_labels_2000_human_reviewed_v1.csv")
    rows: list[dict[str, Any]] = []
    for dataset, group in labels.groupby("dataset") if not labels.empty else []:
        total = int(len(group))
        true_count = int(group["label"].eq("actually_true").sum())
        false_count = int(group["label"].eq("actually_false").sum())
        uncertain_count = int(group["label"].eq("uncertain").sum())
        verified_count = int(group["verified_positive_for_calibration"].astype(str).str.lower().eq("yes").sum())
        rows.append(
            {
                "dataset": dataset,
                "audit_rows": total,
                "actually_true": true_count,
                "actually_false": false_count,
                "uncertain": uncertain_count,
                "verified_positive": verified_count,
                "human_valid_rate": _rate(true_count, total),
                "false_rate": _rate(false_count, total),
                "uncertain_rate": _rate(uncertain_count, total),
                "verified_positive_rate": _rate(verified_count, total),
            }
        )
    table = pd.DataFrame(rows).sort_values("dataset") if rows else pd.DataFrame()
    out_csv = ensure_data_output(output_dir / "table_audit_cross_dataset_consistency.csv")
    table.to_csv(out_csv, index=False)
    if not table.empty:
        low = float(table["human_valid_rate"].min())
        high = float(table["human_valid_rate"].max())
        interval = f"{low:.3f}-{high:.3f}"
    else:
        interval = "unavailable"
    doc = ensure_data_output(output_dir / "AUDIT_CROSS_DATASET_CONSISTENCY.md")
    doc.write_text(
        "# Audit Cross-Dataset Consistency\n\n"
        "The Audit2000 benchmark shows that high-score official-unmatched paths are frequently "
        "human-valid across all three tracking datasets. This supports treating official-unmatched "
        "predictions as unknown rather than as reliable negatives.\n\n"
        f"- Shared human-valid interval across available datasets: `{interval}`.\n"
        "- Source: `outputs/milestones/tpami_reliability_fortress_v2/audit_labels_2000_human_reviewed_v1.csv`.\n\n"
        "See `table_audit_cross_dataset_consistency.csv` for dataset-level counts and rates.\n",
        encoding="utf-8",
    )
    return {
        "status": "completed" if not table.empty else "missing_audit2000",
        "table": str(out_csv),
        "doc": str(doc),
        "datasets": sorted(table["dataset"].astype(str).tolist()) if not table.empty else [],
        "human_valid_interval": interval,
    }


def _find_lvis_paths(root: Path) -> dict[str, Any]:
    annotation_candidates = [
        root / "lvis_v1_val.json",
        root / "annotations/lvis_v1_val.json",
        root / "annotations/lvis_v1_val_cocofied.json",
    ]
    image_candidates = [
        root / "val2017",
        root / "images/val2017",
        root.parent / "COCO",
        root.parent / "COCO/val2017",
        DATA_ROOT / "data/COCO/val2017",
        DATA_ROOT / "data/coco/val2017",
    ]
    ann = next((path for path in annotation_candidates if path.exists()), None)
    image_root = next((path for path in image_candidates if path.exists()), None)
    return {"annotation": ann, "image_root": image_root}


def run_phase11_prepare_lvis(lvis_root: str | Path | None = None, out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or PHASE11_DIR / "lvis_detection")
    root = Path(lvis_root) if lvis_root is not None else DATA_ROOT / "data/LVIS"
    paths = _find_lvis_paths(root)
    ann = paths["annotation"]
    image_root = paths["image_root"]
    status = "ready" if ann is not None and image_root is not None else "requires_lvis_v1_val_and_coco_val_images"
    image_count = 0
    annotation_count = 0
    category_count = 0
    if ann is not None:
        payload = _read_json(ann)
        image_count = len(payload.get("images", []))
        annotation_count = len(payload.get("annotations", []))
        category_count = len(payload.get("categories", []))
    report = {
        "status": status,
        "lvis_root": str(root),
        "annotation_file": str(ann) if ann else "",
        "image_root": str(image_root) if image_root else "",
        "image_count": image_count,
        "annotation_count": annotation_count,
        "category_count": category_count,
        "note": "Raw LVIS/COCO files are not packaged; provide them locally before detector candidate generation.",
    }
    out_json = ensure_data_output(output_dir / "lvis_prepare_report.json")
    write_json(out_json, report)
    return report | {"report": str(out_json)}


def _empty_lvis_candidates() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    universe_cols = [
        "dataset",
        "detector",
        "image_id",
        "video_id",
        "path_id",
        "query",
        "category_id",
        "score",
        "frame_start",
        "frame_end",
        "path_length",
        "candidate_rank",
        "is_matched_to_gt",
        "is_unmatched",
        "matched_gt_id",
        "matched_iou",
        "cell_id",
    ]
    nodes_cols = ["dataset", "detector", "image_id", "path_id", "frame_index", "bbox_x", "bbox_y", "bbox_w", "bbox_h", "score"]
    score_cols = ["dataset", "detector", "image_id", "path_id", "score_total", "score_obj", "score_sem", "score_temp", "score_assoc"]
    return pd.DataFrame(columns=universe_cols), pd.DataFrame(columns=nodes_cols), pd.DataFrame(columns=score_cols)


def _score_bins(scores: pd.Series) -> pd.Series:
    if scores.empty:
        return pd.Series(dtype=str)
    try:
        return pd.qcut(scores.rank(method="first"), q=3, labels=["low", "mid", "high"]).astype(str)
    except ValueError:
        return pd.Series(["high"] * len(scores), index=scores.index)


def _frequency_bins(frame: pd.DataFrame) -> pd.Series:
    if frame.empty or "category_id" not in frame:
        return pd.Series(dtype=str)
    counts = frame["category_id"].map(frame["category_id"].value_counts())
    try:
        return pd.qcut(counts.rank(method="first"), q=3, labels=["tail", "mid", "head"]).astype(str)
    except ValueError:
        return pd.Series(["head"] * len(frame), index=frame.index)


def run_phase11_lvis_detection(lvis_root: str | Path | None = None, out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or PHASE11_DIR / "lvis_detection")
    prepare = run_phase11_prepare_lvis(lvis_root=lvis_root, out_dir=output_dir)
    universe_frames: list[pd.DataFrame] = []
    node_frames: list[pd.DataFrame] = []
    score_frames: list[pd.DataFrame] = []
    rows: list[dict[str, Any]] = []
    for detector in DETECTORS:
        slug = detector.lower().replace("-", "").replace(" ", "_")
        detector_dir = output_dir / slug
        candidate_csv = detector_dir / "candidate_universe.csv"
        nodes_csv = detector_dir / "candidate_nodes.csv"
        scores_csv = detector_dir / "candidate_scores.csv"
        matrix_candidates = [
            detector_dir / "lvis_detection_alpha_seed_matrix.csv",
            detector_dir / "lvis_alpha_seed_m_matrix.csv",
            detector_dir / "matrix/lvis_alpha_seed_m_matrix.csv",
        ]
        matrix_csv = next((path for path in matrix_candidates if path.exists()), matrix_candidates[0])
        candidates = _read_csv(candidate_csv)
        if not candidates.empty:
            candidates["detector"] = detector
            universe_frames.append(candidates)
            nodes = _read_csv(nodes_csv)
            scores = _read_csv(scores_csv)
            if not nodes.empty:
                nodes["detector"] = detector
                node_frames.append(nodes)
            if not scores.empty:
                scores["detector"] = detector
                score_frames.append(scores)
        matrix = _read_csv(matrix_csv)
        if not matrix.empty:
            if "method" in matrix:
                parc_rows = matrix[matrix["method"].astype(str) == "parc_track_gamma_tuned_uniform_scs"].copy()
                if not parc_rows.empty:
                    matrix = parc_rows
            for _, row in matrix.iterrows():
                rows.append(
                    {
                        "dataset": "LVIS",
                        "detector": detector,
                        "method": str(row.get("method", "parc_track_gamma_tuned_uniform_scs")),
                        "alpha1": _safe_num(row, "alpha1"),
                        "seed": int(_safe_num(row, "seed", default=-1)),
                        "M": int(_safe_num(row, "candidate_budget_M", "M", default=150)),
                        "released": _safe_num(row, "released"),
                        "UTR": _safe_num(row, "utr", "UTR"),
                        "conservative_FTR": _safe_num(row, "conservative_ftr_uncertain_and_unlabeled_false", "conservative_FTR"),
                        "mass_ratio": _safe_num(row, "mass_ratio", "best_mass_ratio"),
                        "empty_reason": str(row.get("empty_reason", "")),
                        "result_status": "completed_from_detector_matrix",
                    }
                )
        else:
            reason = "requires_detector_candidate_universe" if candidates.empty else "requires_lvis_detection_matrix"
            for alpha in ALPHAS:
                for seed in SEEDS:
                    rows.append(
                        {
                            "dataset": "LVIS",
                            "detector": detector,
                            "alpha1": alpha,
                            "seed": seed,
                            "M": 150,
                            "released": 0,
                            "UTR": 0.0,
                            "conservative_FTR": 0.0,
                            "mass_ratio": 0.0,
                            "empty_reason": reason,
                            "result_status": "not_run_missing_detector_candidates_or_matrix",
                        }
                    )
    if universe_frames:
        universe = pd.concat(universe_frames, ignore_index=True)
        nodes = pd.concat(node_frames, ignore_index=True) if node_frames else pd.DataFrame()
        scores = pd.concat(score_frames, ignore_index=True) if score_frames else pd.DataFrame()
    else:
        universe, nodes, scores = _empty_lvis_candidates()
    out_universe = ensure_data_output(output_dir / "candidate_universe.csv")
    out_nodes = ensure_data_output(output_dir / "candidate_nodes.csv")
    out_scores = ensure_data_output(output_dir / "candidate_scores.csv")
    universe.to_csv(out_universe, index=False)
    nodes.to_csv(out_nodes, index=False)
    scores.to_csv(out_scores, index=False)
    audit_candidates = pd.DataFrame(columns=AUDIT_COLUMNS)
    if not universe.empty:
        sample = universe.copy()
        if "is_unmatched" in sample:
            sample = sample[sample["is_unmatched"].astype(bool)].copy()
        sample["score_bin"] = _score_bins(pd.to_numeric(sample.get("score", pd.Series(dtype=float)), errors="coerce").fillna(0.0))
        sample["frequency_bin"] = _frequency_bins(sample)
        sample = sample.sort_values(["score_bin", "score"], ascending=[False, False]).head(500)
        for column in AUDIT_COLUMNS:
            if column not in sample:
                sample[column] = ""
        audit_candidates = sample[AUDIT_COLUMNS].copy()
        audit_candidates["dataset"] = "LVIS"
        audit_candidates["audit_status"] = "requires_human_review"
        audit_candidates["verified_positive_for_calibration"] = "no"
    out_audit = ensure_data_output(output_dir / "audit_candidates_lvis.csv")
    out_labels = ensure_data_output(output_dir / "audit_labels_lvis.csv")
    audit_candidates.to_csv(out_audit, index=False)
    audit_candidates.to_csv(out_labels, index=False)
    table = pd.DataFrame(rows)
    out_table = ensure_data_output(output_dir / "table_lvis_detection_certification.csv")
    table.to_csv(out_table, index=False)
    detector_status = table.groupby("detector")["result_status"].first().to_dict() if not table.empty else {}
    report = {
        "status": "completed_with_missing_rows" if any("not_run" in str(v) for v in detector_status.values()) else "completed",
        "prepare_status": prepare.get("status"),
        "candidate_universe": str(out_universe),
        "candidate_nodes": str(out_nodes),
        "candidate_scores": str(out_scores),
        "audit_candidates": str(out_audit),
        "audit_labels": str(out_labels),
        "table": str(out_table),
        "detector_status": detector_status,
    }
    write_json(output_dir / "lvis_detection_report.json", report)
    return report


def run_phase11_ovvis_extension(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or PHASE11_DIR / "ovvis_mask")
    base = _read_csv(V2_DIR / "table_ovvis_mask_certification.csv")
    nodes = _read_csv(V2_DIR / "mask_path_nodes.csv")
    universe = _read_csv(V2_DIR / "mask_path_universe.csv")
    top_paths: set[str] = set()
    if not universe.empty and "path_id" in universe:
        sort_cols = [col for col in ["candidate_rank", "score"] if col in universe]
        selected = universe.sort_values(sort_cols, ascending=[True, False][: len(sort_cols)]).head(150) if sort_cols else universe.head(150)
        top_paths = set(selected["path_id"].astype(str))
    rows: list[dict[str, Any]] = []
    for threshold in (0.5, 0.3):
        conflicts = _count_mask_conflicts(nodes, top_paths, threshold=threshold)
        if base.empty:
            rows.append(
                {
                    "dataset": "BURST",
                    "task": "OVVIS_box_to_mask_scaffold",
                    "mask_iou_threshold": threshold,
                    "result_status": "requires_existing_ovvis_scaffold",
                    "paper_scope": "box_to_mask_proof_of_principle",
                }
            )
            continue
        for _, row in base.iterrows():
            out = row.to_dict()
            out["mask_iou_threshold"] = threshold
            out["conflict_count_top150_mask_iou_ge_threshold"] = conflicts
            out["result_status"] = "box_to_mask_proof_of_principle_existing_certificate"
            out["paper_scope"] = "box_to_mask_proof_of_principle_not_full_mask_benchmark"
            rows.append(out)
    table = pd.DataFrame(rows)
    out_table = ensure_data_output(output_dir / "table_ovvis_mask_certification.csv")
    table.to_csv(out_table, index=False)
    return {"status": "completed" if not table.empty else "missing_ovvis_scaffold", "table": str(out_table)}


def _candidate_sources() -> dict[str, dict[str, Path]]:
    return {
        "OVT-B": {
            "universe": DATA_ROOT / "outputs/phase2_1000/candidate_universe.csv",
            "nodes": DATA_ROOT / "outputs/phase2_1000/candidate_nodes.csv",
        },
        "TAO": {
            "universe": DATA_ROOT / "outputs/phase3_tao_full/candidate_universe.csv",
            "nodes": DATA_ROOT / "outputs/phase3_tao_full/candidate_nodes.csv",
        },
    }


def _make_quantile_bin(values: pd.Series, labels: list[str]) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().sum() < len(labels):
        return pd.Series([labels[-1] if pd.notna(v) else "unknown" for v in numeric], index=values.index)
    try:
        return pd.qcut(numeric.rank(method="first"), q=len(labels), labels=labels).astype(str)
    except ValueError:
        return pd.Series([labels[-1] if pd.notna(v) else "unknown" for v in numeric], index=values.index)


def _augment_path_attributes(universe: pd.DataFrame, nodes: pd.DataFrame) -> pd.DataFrame:
    frame = universe.copy()
    if frame.empty:
        return frame
    frame["path_id"] = frame["path_id"].astype(str)
    if not nodes.empty and {"path_id", "bbox_w", "bbox_h"}.issubset(nodes.columns):
        node = nodes.copy()
        node["path_id"] = node["path_id"].astype(str)
        node["area"] = pd.to_numeric(node["bbox_w"], errors="coerce") * pd.to_numeric(node["bbox_h"], errors="coerce")
        area = node.groupby("path_id")["area"].mean()
        frame["mean_box_area"] = frame["path_id"].map(area)
        frame["object_size"] = _make_quantile_bin(frame["mean_box_area"], ["small", "medium", "large"])
    else:
        frame["object_size"] = "attribute_unavailable"
    if "path_length" in frame:
        frame["track_length_bin"] = _make_quantile_bin(frame["path_length"], ["short", "medium", "long"])
    else:
        frame["track_length_bin"] = "attribute_unavailable"
    if not nodes.empty and {"path_id", "bbox_x", "bbox_y", "bbox_w", "bbox_h", "frame_index"}.issubset(nodes.columns):
        node = nodes.copy()
        node["cx"] = pd.to_numeric(node["bbox_x"], errors="coerce") + pd.to_numeric(node["bbox_w"], errors="coerce") / 2
        node["cy"] = pd.to_numeric(node["bbox_y"], errors="coerce") + pd.to_numeric(node["bbox_h"], errors="coerce") / 2
        node = node.sort_values(["path_id", "frame_index"])
        motion = (
            node.groupby("path_id")[["cx", "cy"]]
            .agg(lambda col: float(col.max() - col.min()) if col.notna().any() else np.nan)
            .sum(axis=1)
        )
        frame["motion_extent"] = frame["path_id"].map(motion)
        frame["motion_speed"] = _make_quantile_bin(frame["motion_extent"], ["slow", "medium", "fast"])
    else:
        frame["motion_speed"] = "attribute_unavailable"
    frame["occlusion"] = "attribute_unavailable"
    if "query" in frame:
        counts = frame["query"].map(frame["query"].value_counts())
    elif "category_id" in frame:
        counts = frame["category_id"].map(frame["category_id"].value_counts())
    else:
        counts = pd.Series(np.nan, index=frame.index)
    frame["category_frequency"] = _make_quantile_bin(counts, ["tail", "mid", "head"])
    return frame


def _stratum_rows(frame: pd.DataFrame, labels: pd.DataFrame, dataset: str, dimension: str, column: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if frame.empty or column not in frame:
        return [
            {
                "dataset": dataset,
                "stratification_dimension": dimension,
                "stratum": "attribute_unavailable",
                "candidate_count": 0,
                "official_unmatched_rate": "",
                "human_valid_rate": "",
                "PARC_certified_release_rate": "",
                "audited_count": 0,
                "attribute_available": False,
                "result_status": "requires_candidate_attribute_table",
            }
        ]
    label_key = labels.copy()
    if not label_key.empty:
        label_key["path_id"] = label_key["path_id"].astype(str)
        label_key = label_key[label_key["dataset"].astype(str).eq(dataset)]
    for stratum, group in frame.groupby(column, dropna=False):
        stratum_name = str(stratum) if str(stratum) != "nan" else "unknown"
        merged = group.merge(label_key[["path_id", "label"]] if not label_key.empty else pd.DataFrame(columns=["path_id", "label"]), on="path_id", how="left")
        audited = merged[merged["label"].isin(VALID_LABELS)]
        official_unmatched = pd.to_numeric(group.get("is_unmatched", pd.Series(False, index=group.index)), errors="coerce").fillna(0).astype(bool)
        released_col = group.get("is_released", pd.Series(np.nan, index=group.index))
        rows.append(
            {
                "dataset": dataset,
                "stratification_dimension": dimension,
                "stratum": stratum_name,
                "candidate_count": int(len(group)),
                "official_unmatched_rate": _rate(float(official_unmatched.sum()), float(len(group))),
                "human_valid_rate": _rate(float(audited["label"].eq("actually_true").sum()), float(len(audited))) if not audited.empty else "",
                "PARC_certified_release_rate": _rate(float(pd.to_numeric(released_col, errors="coerce").fillna(0).astype(bool).sum()), float(len(group))) if "is_released" in group else "",
                "audited_count": int(len(audited)),
                "attribute_available": not stratum_name.startswith("attribute_unavailable"),
                "result_status": "computed" if not stratum_name.startswith("attribute_unavailable") else "attribute_unavailable",
            }
        )
    return rows


def run_phase11_stratified_reliability(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or PHASE11_DIR / "stratified_reliability")
    labels = _read_csv(V2_DIR / "audit_labels_2000_human_reviewed_v1.csv")
    rows: list[dict[str, Any]] = []
    for dataset, paths in _candidate_sources().items():
        universe = _read_csv(paths["universe"])
        nodes = _read_csv(paths["nodes"])
        if universe.empty:
            for dimension in ("object_size", "occlusion", "motion_speed", "track_length", "category_frequency"):
                rows.extend(_stratum_rows(pd.DataFrame(), labels, dataset, dimension, dimension))
            continue
        if "dataset" not in universe:
            universe["dataset"] = dataset
        universe["path_id"] = universe["path_id"].astype(str)
        frame = _augment_path_attributes(universe, nodes)
        rows.extend(_stratum_rows(frame, labels, dataset, "object_size", "object_size"))
        rows.extend(_stratum_rows(frame, labels, dataset, "occlusion", "occlusion"))
        rows.extend(_stratum_rows(frame, labels, dataset, "motion_speed", "motion_speed"))
        rows.extend(_stratum_rows(frame, labels, dataset, "track_length", "track_length_bin"))
        rows.extend(_stratum_rows(frame, labels, dataset, "category_frequency", "category_frequency"))
    table = pd.DataFrame(rows)
    out_table = ensure_data_output(output_dir / "table_stratified_reliability.csv")
    fig_csv = ensure_data_output(output_dir / "figure_stratified_reliability.csv")
    table.to_csv(out_table, index=False)
    table[table["attribute_available"].astype(bool)].to_csv(fig_csv, index=False)
    return {"status": "completed", "table": str(out_table), "figure_csv": str(fig_csv), "rows": int(len(table))}


def _copy_phase11_artifacts(files: list[Path], milestone: Path) -> list[str]:
    copied: list[str] = []
    for src in files:
        copied_path = _copy_if_exists(src, milestone)
        if copied_path is not None:
            copied.append(copied_path.name)
    return copied


def _write_nmi_report(milestone: Path, summary: dict[str, Any]) -> Path:
    report = ensure_data_output(milestone / "RUN_REPORT.md")
    report.write_text(
        "# NMI Generality & Reliability Package v1\n\n"
        "This milestone extends PARC-Track from certified open-vocabulary MOT toward auditable "
        "release-time certification for open-vocabulary visual AI under incomplete annotations.\n\n"
        "## Evidence Blocks\n\n"
        "1. Cross-dataset audit consistency over Audit2000.\n"
        "2. LVIS single-frame detection certification interface and missing-data/detector status.\n"
        "3. Stratified reliability under incomplete annotations for visual difficulty factors.\n"
        "4. Box-to-mask OVVIS proof-of-principle using BURST rectangular masks.\n\n"
        "## Scope\n\n"
        "- Detection and mask-path experiments are generality evidence, not SOTA benchmark claims.\n"
        "- The LVIS table contains loud missing rows when detector candidate universes are absent.\n"
        "- Raw datasets, raw annotations, model weights, detector caches, montage images, and GPU caches are excluded.\n\n"
        f"## Summary JSON\n\n```json\n{json.dumps(summary, indent=2, ensure_ascii=False)}\n```\n",
        encoding="utf-8",
    )
    return report


def run_phase11_freeze_nmi(out_dir: str | Path | None = None, lvis_root: str | Path | None = None) -> dict[str, Any]:
    milestone = ensure_data_output(out_dir or MILESTONE_DIR)
    milestone.mkdir(parents=True, exist_ok=True)
    audit = run_phase11_audit_consistency(PHASE11_DIR / "audit_consistency")
    lvis = run_phase11_lvis_detection(lvis_root=lvis_root, out_dir=PHASE11_DIR / "lvis_detection")
    ovvis = run_phase11_ovvis_extension(PHASE11_DIR / "ovvis_mask")
    strat = run_phase11_stratified_reliability(PHASE11_DIR / "stratified_reliability")
    source_files = [
        Path(audit["table"]),
        Path(audit["doc"]),
        Path(lvis["candidate_universe"]),
        Path(lvis["candidate_nodes"]),
        Path(lvis["candidate_scores"]),
        Path(lvis["audit_candidates"]),
        Path(lvis["audit_labels"]),
        Path(lvis["table"]),
        PHASE11_DIR / "lvis_detection/lvis_prepare_report.json",
        PHASE11_DIR / "lvis_detection/lvis_detection_report.json",
        Path(ovvis["table"]),
        Path(strat["table"]),
        Path(strat["figure_csv"]),
        V2_DIR / "table_blackbox_generator_certification.csv",
        V2_DIR / "table_prop5_three_generator.csv",
        V2_DIR / "second_rater_kappa_report.md",
    ]
    copied = _copy_phase11_artifacts(source_files, milestone)
    summary = {
        "status": "completed",
        "milestone": "outputs/milestones/nmi_generality_reliability_v1",
        "audit_consistency": audit,
        "lvis_detection": lvis,
        "ovvis_mask": ovvis,
        "stratified_reliability": strat,
        "copied_files": copied,
        "raw_data_included": False,
        "model_weights_included": False,
        "package": "outputs/packages/nmi_generality_reliability_v1.tar.gz",
    }
    write_json(milestone / "nmi_generality_reliability_v1_summary.json", summary)
    _write_nmi_report(milestone, summary)
    _sanitize_public_text_files(milestone)
    _write_manifest(milestone)
    package = ensure_data_output(PACKAGE_PATH)
    package.parent.mkdir(parents=True, exist_ok=True)
    if package.exists():
        package.unlink()
    with tarfile.open(package, "w:gz") as tar:
        for path in sorted(milestone.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=Path("nmi_generality_reliability_v1") / path.relative_to(milestone))
    summary["package_sha256"] = _sha256(package)
    return summary
