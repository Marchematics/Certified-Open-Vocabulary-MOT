from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .adapters.datasets import ensure_data_output, write_json
from .phase2 import (
    CANDIDATE_NODE_COLUMNS,
    CANDIDATE_SCORE_COLUMNS,
    CANDIDATE_UNIVERSE_COLUMNS,
    iou_xywh,
)


DATA_ROOT = Path("<PARC_ROOT>")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _prediction_rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        for key in ("annotations", "predictions", "results", "detections"):
            value = data.get(key)
            if isinstance(value, list):
                rows = value
                break
        else:
            raise ValueError("prediction JSON must be a list or contain annotations/predictions/results/detections")
    else:
        raise ValueError("prediction JSON must be a list or dict")
    return [dict(row) for row in rows if isinstance(row, dict)]


def _frame_path(root: Path, frame_subdir: str, file_name: str) -> str:
    path = Path(file_name)
    if path.is_absolute():
        return str(path)
    base = root / frame_subdir if frame_subdir else root
    return str(base / file_name)


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _empty_report(out_dir: Path, status: str, reason: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    report = {"status": status, "reason": reason}
    if extra:
        report.update(extra)
    write_json(ensure_data_output(out_dir / "ovtrack_conversion_report.json"), report)
    return report


def inspect_ovtrack_public_outputs(output_dir: str | Path | None = None) -> dict[str, Any]:
    """Record whether cloned OVTrack/OVT-B repos contain public prediction files."""
    out_dir = ensure_data_output(output_dir or DATA_ROOT / "outputs/phase7_ovtrack_ovtb")
    repos = {
        "SysCV/ovtrack": DATA_ROOT / "repos/ovtrack",
        "Coo1Sea/OVT-B-Dataset": DATA_ROOT / "repos/OVT-B-Dataset",
        "siyuanliii/TETA": DATA_ROOT / "repos/TETA",
    }
    candidate_names = []
    for repo, path in repos.items():
        if not path.exists():
            candidate_names.append({"repo": repo, "status": "missing_local_clone", "path": str(path)})
            continue
        files = []
        for child in path.rglob("*"):
            if not child.is_file():
                continue
            name = child.name.lower()
            rel = str(child.relative_to(path))
            if any(token in name or token in rel.lower() for token in ("pred", "result", "ovtrack_teta_results")):
                if child.suffix.lower() in {".json", ".pkl", ".pickle", ".txt", ".zip"}:
                    files.append(rel)
        candidate_names.append({"repo": repo, "status": "checked", "path": str(path), "candidate_files": files[:200]})
    report = {
        "status": "requires_external_ovtrack_prediction_file",
        "target_dataset": "OVT-B",
        "checked_repositories": candidate_names,
        "finding": "The public repositories expose OVT-B/OVTrack configs and model/download instructions, but no ready-to-use OVT-B prediction JSON/PKL was found in the cloned file trees.",
        "expected_prediction_format": "TAO/TETA COCO-VID JSON list with image_id, video_id, track_id, category_id, bbox, score.",
        "converter_command": "python -m parc_track.cli phase7 ovtrack-convert --pred PATH_TO_OVTRACK_JSON --ann <PARC_ROOT>/data/OVT-B/ovtb_ann.json --out-dir <PARC_ROOT>/outputs/phase7_ovtrack_ovtb",
        "sources": [
            "https://github.com/SysCV/ovtrack",
            "https://github.com/Coo1Sea/OVT-B-Dataset",
            "https://github.com/siyuanliii/TETA",
        ],
    }
    write_json(ensure_data_output(out_dir / "ovtrack_public_output_report.json"), report)
    return report


def convert_ovtrack_predictions(
    pred_path: str | Path,
    ann_file: str | Path,
    out_dir: str | Path,
    *,
    dataset_name: str = "OVT-B",
    dataset_root: str | Path = DATA_ROOT / "data/OVT-B",
    frame_subdir: str = "OVT-B",
    iou_threshold: float = 0.5,
    temporal_overlap_threshold: float = 0.3,
) -> dict[str, Any]:
    """Convert TAO/TETA-style OVTrack predictions into PARC candidate files."""
    pred_path = Path(pred_path)
    ann_file = Path(ann_file)
    out_dir = ensure_data_output(out_dir)
    if not pred_path.exists():
        return _empty_report(out_dir, "requires_ovtrack_prediction_file", f"prediction file missing: {pred_path}")
    if pred_path.suffix.lower() != ".json":
        return _empty_report(
            out_dir,
            "unsupported_prediction_format",
            "Only TAO/TETA COCO-VID JSON prediction files are supported by this converter.",
            {"prediction_file": str(pred_path)},
        )
    ann = _load_json(ann_file)
    pred_rows = _prediction_rows(_load_json(pred_path))
    if not pred_rows:
        return _empty_report(out_dir, "empty_prediction_file", "prediction JSON contains no rows", {"prediction_file": str(pred_path)})

    categories = {int(cat["id"]): str(cat.get("name", cat["id"])).replace("_", " ") for cat in ann.get("categories", [])}
    images = {int(img["id"]): img for img in ann.get("images", [])}
    anns_by_image: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for gt in ann.get("annotations", []):
        anns_by_image[int(gt["image_id"])].append(gt)

    grouped: dict[tuple[int, int, int], list[dict[str, Any]]] = defaultdict(list)
    skipped = Counter()
    for row in pred_rows:
        try:
            image_id = int(row["image_id"])
            image = images.get(image_id)
            video_id = int(row.get("video_id", image.get("video_id") if image else -1))
            category_id = int(row["category_id"])
            track_id = int(row.get("track_id", row.get("id", -1)))
            bbox = [float(v) for v in row["bbox"][:4]]
            score = float(row.get("score", row.get("confidence", 1.0)))
        except Exception:
            skipped["malformed_row"] += 1
            continue
        if image is None or video_id < 0 or track_id < 0:
            skipped["missing_image_or_track"] += 1
            continue
        frame_index = int(image.get("frame_index", image.get("frame_id", 0)))
        file_name = str(image.get("file_name", ""))
        grouped[(video_id, track_id, category_id)].append(
            {
                "image_id": image_id,
                "video_id": video_id,
                "frame_index": frame_index,
                "image_path": _frame_path(Path(dataset_root), frame_subdir, file_name),
                "bbox": bbox,
                "score": score,
            }
        )

    universe_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    node_rows: list[dict[str, Any]] = []
    for idx, ((video_id, track_id, category_id), dets) in enumerate(sorted(grouped.items()), start=0):
        dets = sorted(dets, key=lambda det: (int(det["frame_index"]), int(det["image_id"])))
        if not dets:
            continue
        matches = []
        best_iou = 0.0
        best_gt = ""
        for det in dets:
            frame_best = (0.0, "")
            for gt in anns_by_image.get(int(det["image_id"]), []):
                if int(gt.get("category_id", -1)) != category_id:
                    continue
                overlap = iou_xywh(tuple(det["bbox"]), tuple(float(v) for v in gt["bbox"]))
                if overlap > frame_best[0]:
                    frame_best = (overlap, str(gt.get("track_id", "")))
            if frame_best[0] >= iou_threshold:
                matches.append(frame_best[1])
            if frame_best[0] > best_iou:
                best_iou, best_gt = frame_best
        temporal_overlap = len(matches) / max(1, len(dets))
        is_unmatched = temporal_overlap < temporal_overlap_threshold
        score = sum(float(det["score"]) for det in dets) / max(1, len(dets))
        path_id = f"ovtrack_v{video_id}_t{track_id}_c{category_id}_p{idx:06d}"
        row = {
            "dataset": dataset_name,
            "video_id": video_id,
            "path_id": path_id,
            "split": "",
            "query": categories.get(category_id, str(category_id)),
            "category_id": category_id,
            "score": score,
            "objectness": score,
            "semantic_margin": score,
            "temporal_stability": len(dets),
            "association_score": max(0.0, min(1.0, (len(dets) - 1) / max(1, len(dets)))),
            "frame_start": min(int(det["frame_index"]) for det in dets),
            "frame_end": max(int(det["frame_index"]) for det in dets),
            "path_length": len(dets),
            "candidate_rank": 0,
            "is_dummy": False,
            "matched_gt_id": best_gt,
            "matched_iou": best_iou,
            "temporal_overlap": temporal_overlap,
            "matched_frames": len(matches),
            "is_matched_to_gt": not is_unmatched,
            "is_unmatched": is_unmatched,
            "audit_label": "",
            "verified_positive_for_calibration": "no",
            "cell_id": f"cat:{category_id}",
            "novelty_bin": "unknown",
            "query_cluster": categories.get(category_id, str(category_id)),
            "occ_bin": "unknown",
            "domain_bin": "global",
            "fallback_level": 0,
            "score_source": "ovtrack_public_prediction",
        }
        universe_rows.append(row)
        score_rows.append(
            {
                "video_id": video_id,
                "path_id": path_id,
                "release_checkpoint": "final",
                "score_total": score,
                "score_obj": score,
                "score_sem": score,
                "score_temp": len(dets),
                "score_assoc": row["association_score"],
            }
        )
        for node_index, det in enumerate(dets):
            bbox = det["bbox"]
            node_rows.append(
                {
                    "video_id": video_id,
                    "path_id": path_id,
                    "node_index": node_index,
                    "image_id": int(det["image_id"]),
                    "frame_index": int(det["frame_index"]),
                    "image_path": det["image_path"],
                    "bbox_x": float(bbox[0]),
                    "bbox_y": float(bbox[1]),
                    "bbox_w": float(bbox[2]),
                    "bbox_h": float(bbox[3]),
                    "score": float(det["score"]),
                }
            )

    universe_rows.sort(key=lambda item: float(item["score"]), reverse=True)
    for rank, row in enumerate(universe_rows, start=1):
        row["candidate_rank"] = rank
    universe = pd.DataFrame(universe_rows, columns=CANDIDATE_UNIVERSE_COLUMNS)
    scores = pd.DataFrame(score_rows, columns=CANDIDATE_SCORE_COLUMNS)
    nodes = pd.DataFrame(node_rows, columns=CANDIDATE_NODE_COLUMNS)
    universe.to_csv(ensure_data_output(out_dir / "candidate_universe.csv"), index=False)
    scores.to_csv(ensure_data_output(out_dir / "candidate_scores.csv"), index=False)
    nodes.to_csv(ensure_data_output(out_dir / "candidate_nodes.csv"), index=False)
    labels = universe[["dataset", "video_id", "path_id"]].copy()
    labels["label"] = ""
    labels["reason"] = ""
    labels["auditor"] = ""
    labels["confidence"] = ""
    labels["review_status"] = ""
    labels["verified_positive_for_calibration"] = ""
    labels.to_csv(ensure_data_output(out_dir / "audit_labels.csv"), index=False)

    summary = {
        "status": "completed",
        "dataset": dataset_name,
        "prediction_file": str(pred_path),
        "ann_file": str(ann_file),
        "candidate_universe": str(out_dir / "candidate_universe.csv"),
        "candidate_scores": str(out_dir / "candidate_scores.csv"),
        "candidate_nodes": str(out_dir / "candidate_nodes.csv"),
        "audit_labels": str(out_dir / "audit_labels.csv"),
        "num_prediction_rows": int(len(pred_rows)),
        "num_candidate_paths": int(len(universe)),
        "num_candidate_nodes": int(len(nodes)),
        "num_matched_paths": int((~universe["is_unmatched"].map(_as_bool)).sum()) if not universe.empty else 0,
        "num_unmatched_paths": int(universe["is_unmatched"].map(_as_bool).sum()) if not universe.empty else 0,
        "skipped_rows": dict(skipped),
        "format": "TAO/TETA COCO-VID JSON",
    }
    write_json(ensure_data_output(out_dir / "ovtrack_conversion_report.json"), summary)
    return summary


def write_ovtrack_matrix_config(
    out_dir: str | Path,
    config_path: str | Path | None = None,
    *,
    ann_file: str | Path = DATA_ROOT / "data/OVT-B/ovtb_ann.json",
) -> dict[str, Any]:
    out_dir = Path(out_dir)
    cfg_path = Path(config_path or DATA_ROOT / "configs/phase7_ovtrack_ovtb_matrix.yaml")
    cfg = {
        "dataset": {
            "name": "OVT-B",
            "root": str(DATA_ROOT / "data/OVT-B"),
            "ann_file": str(ann_file),
            "format_hint": "tao_or_coco_video",
        },
        "splits": {"tune_ratio": 0.10, "cal_ratio": 0.50, "test_ratio": 0.40, "seed": 0},
        "risk": {"alpha1": 0.10},
        "release_grid": {"times_sec": [2.0], "weights": "uniform"},
        "calibration": {"empty_block_policy": "coverage_conditional", "use_verified_positive_for_calibration": True},
        "e_calibrator": {
            "type": "power",
            "gamma_selection": "effective_finite_resolution_tuned",
            "gamma_candidates": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.50],
        },
        "selector": {"type": "uniform_scs_greedy", "candidate_budget_sweep": [150]},
        "matrix": {"alpha1": [0.10, 0.20], "seeds": [0, 1, 2], "candidate_budget_M": [150]},
        "tune_selection": {"internal_cal_ratio": 0.50, "fallback_M": 150, "out": str(out_dir / "tuned_m_selection.csv")},
        "input": {
            "candidate_universe": str(out_dir / "candidate_universe.csv"),
            "audit_labels": str(out_dir / "audit_labels.csv"),
        },
        "output": {
            "output_dir": str(out_dir),
            "candidate_nodes": str(out_dir / "candidate_nodes.csv"),
        },
    }
    ensure_data_output(cfg_path).write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    return {"status": "completed", "config": str(cfg_path)}
