#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import yaml


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False)


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def build_pseudo_tracking_lvis(lvis_ann: Path, out_ann: Path, coco_val_root: Path) -> dict[str, Any]:
    payload = _load_json(lvis_ann)
    images = []
    missing_images = 0
    for image in payload.get("images", []):
        image_id = int(image["id"])
        coco_url = str(image.get("coco_url", ""))
        basename = coco_url.rsplit("/", 1)[-1] or str(image.get("file_name", "")) or f"{image_id:012d}.jpg"
        split = "val2017" if "/val2017/" in coco_url else "train2017" if "/train2017/" in coco_url else ""
        file_name = f"{split}/{basename}" if split else basename
        if not file_name:
            file_name = f"{image_id:012d}.jpg"
        image_path = coco_val_root / file_name
        if not image_path.exists():
            missing_images += 1
        images.append(
            {
                "id": image_id,
                "video_id": image_id,
                "frame_index": 0,
                "frame_id": 0,
                "file_name": file_name,
                "width": image.get("width", 0),
                "height": image.get("height", 0),
            }
        )
    annotations = []
    for idx, ann in enumerate(payload.get("annotations", []), start=1):
        image_id = int(ann["image_id"])
        annotations.append(
            {
                "id": int(ann.get("id", idx)),
                "image_id": image_id,
                "video_id": image_id,
                "track_id": int(ann.get("id", idx)),
                "category_id": int(ann["category_id"]),
                "bbox": ann["bbox"],
                "area": ann.get("area", 0),
                "iscrowd": ann.get("iscrowd", 0),
            }
        )
    out = {
        "info": payload.get("info", {}),
        "licenses": payload.get("licenses", []),
        "images": images,
        "annotations": annotations,
        "categories": payload.get("categories", []),
        "not_exhaustive_category_ids": payload.get("not_exhaustive_category_ids", []),
        "neg_category_ids": payload.get("neg_category_ids", []),
    }
    _write_json(out_ann, out)
    return {
        "pseudo_annotation": str(out_ann),
        "images": len(images),
        "annotations": len(annotations),
        "categories": len(payload.get("categories", [])),
        "missing_images": missing_images,
    }


def _base_proposal_config(
    *,
    detector: str,
    root: Path,
    ann_file: Path,
    output_root: Path,
    video_stride: int,
    video_offset: int,
    device: str,
) -> dict[str, Any]:
    detector_slug = detector.lower()
    out = output_root / detector_slug / f"shard_{video_offset}"
    cfg: dict[str, Any] = {
        "dataset": {
            "name": "LVIS",
            "root": str(root),
            "ann_file": str(ann_file),
            "format_hint": "lvis_pseudo_tracking",
            "frame_subdir": "",
        },
        "proposal": {
            "backend": "groundingdino" if detector_slug == "groundingdino" else "owlv2_hf",
            "backbone": "groundingdino_audit_generator" if detector_slug == "groundingdino" else "owlv2_hf",
            "max_videos": 50000,
            "frames_per_video": 1,
            "classes_per_video": 3,
            "max_paths_per_video": 200,
            "candidate_budget_M": 5000,
            "min_path_length": 1,
            "link_iou_threshold": 0.0,
            "max_frame_gap": 0,
            "max_detections_per_frame": 30,
            "video_stride": video_stride,
            "video_offset": video_offset,
            "progress_every": 250,
            "cache_dir": str(out / "cache"),
        },
        "matching": {
            "iou_threshold": 0.5,
            "temporal_overlap_threshold": 0.5,
            "unmatched_only": True,
        },
        "sampling": {
            "strategy": "stratified_by_mondrian_cell",
            "total_samples": 500,
            "top_b_per_cell": 15,
            "min_score_percentile": 80,
        },
        "mondrian": {
            "use_novelty": True,
            "use_query_cluster": True,
            "use_occlusion": False,
            "use_domain": False,
            "fallback_min_videos": 100,
        },
        "audit_export": {
            "make_montages": False,
            "frames_per_path": 1,
            "output_viewer": str(out / "audit_viewer"),
            "montage_dir": str(out / "audit_viewer/montages"),
            "clip_dir": str(out / "audit_viewer/clips"),
        },
        "output": {
            "candidates": str(out / "audit_candidates.csv"),
            "labels": str(out / "audit_labels.csv"),
            "manifest": str(out / "audit_manifest.json"),
            "summary": str(out / "audit_summary.csv"),
            "candidate_universe": str(out / "candidate_universe.csv"),
            "candidate_scores": str(out / "candidate_scores.csv"),
            "candidate_nodes": str(out / "candidate_nodes.csv"),
        },
    }
    if detector_slug == "groundingdino":
        gd_root = Path(os.environ.get("GROUNDINGDINO_MODEL_ROOT", "./models/grounding-dino"))
        cfg["groundingdino"] = {
            "config": str(gd_root / "GroundingDINO_SwinT_OGC.cfg.py"),
            "weights": str(gd_root / "groundingdino_swint_ogc.pth"),
            "local_text_encoder": "./cache/huggingface/manual/bert-base-uncased",
            "device": device,
            "text_threshold": 0.25,
            "box_threshold": 0.30,
        }
    else:
        cfg["owlv2"] = {
            "model": "google/owlv2-base-patch16-ensemble",
            "device": device,
            "cache_dir": str(Path(os.environ.get("PARC_TRACK_ROOT", ".")) / "cache/huggingface"),
            "threshold": 0.10,
            "max_detections_per_class": 10,
        }
    return cfg


def write_configs(config_dir: Path, root: Path, ann_file: Path, output_root: Path, shards: int) -> dict[str, Any]:
    written: list[str] = []
    for detector in ("groundingdino", "owlv2"):
        for offset in range(shards):
            cfg = _base_proposal_config(
                detector=detector,
                root=root,
                ann_file=ann_file,
                output_root=output_root,
                video_stride=shards,
                video_offset=offset,
                # Keep the in-process device ordinal stable. Multi-GPU sharding
                # should be done by launching each shard with CUDA_VISIBLE_DEVICES
                # set to one physical GPU; inside that process cuda:0 is valid.
                device="cuda:0",
            )
            path = config_dir / f"phase11_lvis_{detector}_shard{offset}.yaml"
            _write_yaml(path, cfg)
            written.append(str(path))
    return {"configs": written, "shards": shards}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare LVIS pseudo-tracking scaffold and shard configs.")
    raw_root = Path(os.environ.get("PARC_RAW_DATA_ROOT", "./data"))
    track_root = Path(os.environ.get("PARC_TRACK_ROOT", "."))
    repo_root = Path(os.environ.get("PARC_REPO_ROOT", "."))
    parser.add_argument("--lvis-ann", default=str(raw_root / "LVIS/annotations/lvis_v1_val.json"))
    parser.add_argument("--coco-val-root", default=str(raw_root / "COCO"))
    parser.add_argument("--out-ann", default=str(track_root / "outputs/phase11_release/lvis_detection/lvis_pseudo_tracking_ann.json"))
    parser.add_argument("--config-dir", default=str(repo_root / "configs"))
    parser.add_argument("--output-root", default=str(track_root / "outputs/phase11_release/lvis_detection"))
    parser.add_argument("--shards", type=int, default=4)
    args = parser.parse_args()

    ann = Path(args.lvis_ann)
    coco = Path(args.coco_val_root)
    out_ann = Path(args.out_ann)
    config_dir = Path(args.config_dir)
    output_root = Path(args.output_root)
    summary = build_pseudo_tracking_lvis(ann, out_ann, coco)
    summary.update(write_configs(config_dir, coco, out_ann, output_root, args.shards))
    report = output_root / "lvis_scaffold_prepare_report.json"
    _write_json(report, summary)
    print(json.dumps(summary | {"report": str(report)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
