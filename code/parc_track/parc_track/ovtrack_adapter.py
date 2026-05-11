from __future__ import annotations

import json
import hashlib
import pickle
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


DATA_ROOT = Path(".")

PUBLISHED_TRACKERS: dict[str, dict[str, Any]] = {
    "ovtrack": {
        "display_name": "OVTrack",
        "repo": "https://github.com/SysCV/ovtrack",
        "score_source": "ovtrack_public_prediction",
    },
    "ovtb_baseline": {
        "display_name": "OVT-B baseline",
        "repo": "https://github.com/Coo1Sea/OVT-B-Dataset",
        "score_source": "ovtb_baseline_public_prediction",
    },
    "ovtr": {
        "display_name": "OVTR",
        "repo": "https://github.com/jinyanglii/OVTR",
        "score_source": "ovtr_public_prediction",
    },
}

PUBLISHED_DATASETS: dict[str, dict[str, Any]] = {
    "ovtb": {
        "display_name": "OVT-B",
        "root": DATA_ROOT / "data/OVT-B",
        "ann_file": DATA_ROOT / "data/OVT-B/ovtb_ann.json",
        "frame_subdir": "OVT-B",
        "format_hint": "tao_or_coco_video",
    },
    "tao": {
        "display_name": "TAO",
        "root": DATA_ROOT / "data/TAO",
        "ann_file": DATA_ROOT / "data/TAO/annotations/trainval.json",
        "frame_subdir": "",
        "format_hint": "tao",
    },
}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _safe_slug(value: Any) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_") or "tracker"


def _sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _prediction_rows_from_file(path: Path) -> tuple[list[dict[str, Any]], str]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _prediction_rows(_load_json(path)), "TAO/TETA COCO-VID JSON"
    if suffix in {".pkl", ".pickle"}:
        with path.open("rb") as handle:
            data = pickle.load(handle)
        try:
            rows = _prediction_rows(data)
        except Exception as exc:
            raise ValueError(
                "unsupported MMTracking PKL object; expected a list of COCO-VID rows "
                "or a dict containing annotations/predictions/results/detections"
            ) from exc
        return rows, "PKL containing TAO/TETA COCO-VID rows"
    raise ValueError("unsupported prediction format; expected .json, .pkl, or .pickle")


def _frame_path(root: Path, frame_subdir: str, file_name: str) -> str:
    path = Path(file_name)
    if path.is_absolute():
        return str(path)
    base = root / frame_subdir if frame_subdir else root
    return str(base / file_name)


def _as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _empty_report(
    out_dir: Path,
    status: str,
    reason: str,
    extra: dict[str, Any] | None = None,
    *,
    report_name: str = "ovtrack_conversion_report.json",
) -> dict[str, Any]:
    report = {"status": status, "reason": reason}
    if extra:
        report.update(extra)
    write_json(ensure_data_output(out_dir / report_name), report)
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
        "converter_command": "python -m parc_track.cli phase7 ovtrack-convert --pred PATH_TO_OVTRACK_JSON --ann ./data/OVT-B/ovtb_ann.json --out-dir ./outputs/phase7_ovtrack_ovtb",
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
    tracker_name: str = "ovtrack",
    tracker_display_name: str | None = None,
    report_filename: str = "ovtrack_conversion_report.json",
) -> dict[str, Any]:
    """Convert TAO/TETA-style tracker predictions into PARC candidate files.

    The historical name is kept for backward compatibility with existing OVTrack
    scripts.  ``tracker_name`` makes the converter usable for OVTrack, the
    OVT-B author baseline, OVTR, and future published tracker outputs that can
    be represented as COCO-VID rows.
    """
    pred_path = Path(pred_path)
    ann_file = Path(ann_file)
    out_dir = ensure_data_output(out_dir)
    tracker_slug = _safe_slug(tracker_name)
    tracker_spec = PUBLISHED_TRACKERS.get(tracker_slug, {})
    tracker_display = tracker_display_name or tracker_spec.get("display_name", tracker_name)
    prediction_hash = _sha256_file(pred_path)
    if not pred_path.exists():
        return _empty_report(
            out_dir,
            "requires_prediction_file",
            f"prediction file missing: {pred_path}",
            {"tracker_name": tracker_slug, "tracker_display_name": tracker_display},
            report_name=report_filename,
        )
    try:
        pred_rows, format_name = _prediction_rows_from_file(pred_path)
    except Exception as exc:
        return _empty_report(
            out_dir,
            "unsupported_prediction_format",
            str(exc),
            {
                "prediction_file": str(pred_path),
                "prediction_sha256": prediction_hash,
                "tracker_name": tracker_slug,
                "tracker_display_name": tracker_display,
                "expected_prediction_format": "TAO/TETA COCO-VID rows with image_id, video_id, track_id, category_id, bbox, score.",
            },
            report_name=report_filename,
        )
    ann = _load_json(ann_file)
    if not pred_rows:
        return _empty_report(
            out_dir,
            "empty_prediction_file",
            "prediction file contains no rows",
            {"prediction_file": str(pred_path), "prediction_sha256": prediction_hash, "tracker_name": tracker_slug},
            report_name=report_filename,
        )

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
        path_id = f"{tracker_slug}_v{video_id}_t{track_id}_c{category_id}_p{idx:06d}"
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
            "score_source": tracker_spec.get("score_source", f"{tracker_slug}_public_prediction"),
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
        "tracker_name": tracker_slug,
        "tracker_display_name": tracker_display,
        "dataset": dataset_name,
        "prediction_file": str(pred_path),
        "prediction_sha256": prediction_hash,
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
        "format": format_name,
        "canonical_prediction_format": "TAO/TETA COCO-VID rows",
    }
    write_json(ensure_data_output(out_dir / report_filename), summary)
    if report_filename != "ovtrack_conversion_report.json":
        write_json(ensure_data_output(out_dir / "ovtrack_conversion_report.json"), summary)
    return summary


def convert_published_tracker_predictions(
    pred_path: str | Path,
    ann_file: str | Path,
    out_dir: str | Path,
    *,
    tracker_name: str,
    dataset_name: str,
    dataset_root: str | Path,
    frame_subdir: str = "",
    iou_threshold: float = 0.5,
    temporal_overlap_threshold: float = 0.3,
) -> dict[str, Any]:
    """Generic published-tracker wrapper around :func:`convert_ovtrack_predictions`."""
    tracker_slug = _safe_slug(tracker_name)
    tracker_spec = PUBLISHED_TRACKERS.get(tracker_slug, {})
    return convert_ovtrack_predictions(
        pred_path=pred_path,
        ann_file=ann_file,
        out_dir=out_dir,
        dataset_name=dataset_name,
        dataset_root=dataset_root,
        frame_subdir=frame_subdir,
        iou_threshold=iou_threshold,
        temporal_overlap_threshold=temporal_overlap_threshold,
        tracker_name=tracker_slug,
        tracker_display_name=tracker_spec.get("display_name", tracker_name),
        report_filename="published_tracker_conversion_report.json",
    )


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
