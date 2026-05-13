#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import pandas as pd


CANDIDATE_UNIVERSE_COLUMNS = [
    "dataset",
    "video_id",
    "path_id",
    "split",
    "query",
    "category_id",
    "score",
    "objectness",
    "semantic_margin",
    "temporal_stability",
    "association_score",
    "frame_start",
    "frame_end",
    "path_length",
    "candidate_rank",
    "is_dummy",
    "matched_gt_id",
    "matched_iou",
    "temporal_overlap",
    "matched_frames",
    "is_matched_to_gt",
    "is_unmatched",
    "audit_label",
    "verified_positive_for_calibration",
    "cell_id",
    "novelty_bin",
    "query_cluster",
    "occ_bin",
    "domain_bin",
    "fallback_level",
    "score_source",
    "location_id",
    "support_semantics",
]

CANDIDATE_SCORE_COLUMNS = [
    "video_id",
    "path_id",
    "release_checkpoint",
    "score_total",
    "score_obj",
    "score_sem",
    "score_temp",
    "score_assoc",
]

CANDIDATE_NODE_COLUMNS = [
    "video_id",
    "path_id",
    "node_index",
    "image_id",
    "frame_index",
    "image_path",
    "bbox_x",
    "bbox_y",
    "bbox_w",
    "bbox_h",
    "score",
]

AUDIT_LABEL_COLUMNS = [
    "dataset",
    "video_id",
    "path_id",
    "label",
    "reason",
    "auditor",
    "confidence",
    "review_status",
    "verified_positive_for_calibration",
]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_name(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    return out or "unknown"


def patch_groundingdino_transformers() -> None:
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    try:
        import torch
        from transformers import BertModel

        def _param_dtype(module):
            try:
                return next(module.parameters()).dtype
            except Exception:
                return torch.float32

        def _legacy_get_extended_attention_mask(self, attention_mask, input_shape, device=None, dtype=None):
            if dtype is None or isinstance(dtype, torch.device):
                dtype = _param_dtype(self)
            if device is None or isinstance(device, torch.dtype):
                device = attention_mask.device
            if attention_mask.dim() == 3:
                extended_attention_mask = attention_mask[:, None, :, :]
            elif attention_mask.dim() == 2:
                extended_attention_mask = attention_mask[:, None, None, :]
            else:
                raise ValueError(f"Wrong shape for attention_mask: {tuple(attention_mask.shape)}")
            extended_attention_mask = extended_attention_mask.to(device=device, dtype=dtype)
            return (1.0 - extended_attention_mask) * torch.finfo(dtype).min

        BertModel.get_extended_attention_mask = _legacy_get_extended_attention_mask  # type: ignore[method-assign]
        if not hasattr(BertModel, "get_head_mask"):

            def _legacy_get_head_mask(self, head_mask, num_hidden_layers, is_attention_chunked=False):
                if head_mask is None:
                    return [None] * num_hidden_layers
                if head_mask.dim() == 1:
                    head_mask = head_mask.unsqueeze(0).unsqueeze(0).unsqueeze(-1).unsqueeze(-1)
                    head_mask = head_mask.expand(num_hidden_layers, -1, -1, -1, -1)
                elif head_mask.dim() == 2:
                    head_mask = head_mask.unsqueeze(1).unsqueeze(-1).unsqueeze(-1)
                if is_attention_chunked:
                    head_mask = head_mask.unsqueeze(-1)
                return head_mask.to(dtype=_param_dtype(self))

            BertModel.get_head_mask = _legacy_get_head_mask  # type: ignore[attr-defined]
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--annotations", required=True)
    parser.add_argument("--image-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--groundingdino-root", default="/home/waas/paper_experiments/third_party/GroundingDINO")
    parser.add_argument("--config", default="/datasets/ComfyUI/models/grounding-dino/GroundingDINO_SwinT_OGC.cfg.py")
    parser.add_argument("--weights", default="/datasets/ComfyUI/models/grounding-dino/groundingdino_swint_ogc.pth")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--prompt", default="animal")
    parser.add_argument("--category-id", type=int, default=1)
    parser.add_argument("--box-threshold", type=float, default=0.18)
    parser.add_argument("--text-threshold", type=float, default=0.20)
    parser.add_argument("--max-images", type=int, default=0)
    parser.add_argument("--max-det-per-image", type=int, default=20)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--progress-every", type=int, default=50)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("PYTHONPATH", args.groundingdino_root)
    import sys

    if args.groundingdino_root not in sys.path:
        sys.path.insert(0, args.groundingdino_root)
    patch_groundingdino_transformers()
    from groundingdino.util.inference import Model

    manifest = pd.read_csv(args.manifest)
    annotations = load_json(Path(args.annotations))
    image_root = Path(args.image_root)

    labels_by_image: dict[str, set[int]] = defaultdict(set)
    for ann in annotations.get("annotations", []):
        labels_by_image[str(ann["image_id"])].add(int(ann["category_id"]))

    rows = manifest.to_dict("records")
    if args.num_shards > 1:
        rows = [row for idx, row in enumerate(rows) if idx % int(args.num_shards) == int(args.shard_index)]
    if args.max_images and args.max_images > 0:
        rows = rows[: int(args.max_images)]

    model = Model(
        model_config_path=args.config,
        model_checkpoint_path=args.weights,
        device=args.device,
    )

    prompt = str(args.prompt).strip()
    category_id = int(args.category_id)
    support_semantics = "image_level_animal_presence_support"
    universe_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []
    node_rows: list[dict[str, Any]] = []
    pseudo_images: list[dict[str, Any]] = []
    pseudo_annotations: list[dict[str, Any]] = []
    image_int_by_uuid: dict[str, int] = {}
    frame_idx_by_location: dict[int, int] = defaultdict(int)
    videos_seen: set[int] = set()
    failures: list[dict[str, Any]] = []

    for pos, row in enumerate(rows, start=1):
        image_uuid = str(row["image_id"])
        image_path = Path(str(row.get("local_path", "")))
        if not image_path.is_absolute():
            image_path = Path("/home/waas/paper_experiments") / image_path
        if not image_path.exists():
            image_path = image_root / f"{image_uuid}.jpg"
        if not image_path.exists():
            failures.append({"image_id": image_uuid, "reason": "missing_image"})
            continue
        location_id = int(row.get("location", row.get("location_id")))
        split = str(row["split"])
        width = int(row.get("width", 0) or 0)
        height = int(row.get("height", 0) or 0)
        official_labels = labels_by_image.get(image_uuid, set())
        animal_present = any(int(cat_id) != 0 for cat_id in official_labels)
        videos_seen.add(location_id)
        image_int = image_int_by_uuid.setdefault(image_uuid, len(image_int_by_uuid) + 1)
        frame_index = frame_idx_by_location[location_id]
        frame_idx_by_location[location_id] += 1
        pseudo_images.append(
            {
                "id": image_int,
                "file_name": image_path.name,
                "video_id": location_id,
                "frame_index": frame_index,
                "width": width,
                "height": height,
                "original_image_id": image_uuid,
                "split": split,
            }
        )
        if animal_present:
            pseudo_annotations.append(
                {
                    "id": len(pseudo_annotations) + 1,
                    "image_id": image_int,
                    "video_id": location_id,
                    "frame_index": frame_index,
                    "category_id": category_id,
                    "track_id": f"loc{location_id}_img{image_int}_animal",
                    "bbox": [0.0, 0.0, float(width), float(height)],
                    "support_type": support_semantics,
                }
            )
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            failures.append({"image_id": image_uuid, "reason": "cv2_read_failed"})
            continue
        try:
            pred = model.predict_with_classes(
                image=bgr,
                classes=[prompt],
                box_threshold=float(args.box_threshold),
                text_threshold=float(args.text_threshold),
            )
        except Exception as exc:
            failures.append({"image_id": image_uuid, "reason": f"inference_failed:{type(exc).__name__}:{exc}"})
            continue

        xyxy = getattr(pred, "xyxy", [])
        confidence = getattr(pred, "confidence", None)
        class_ids = getattr(pred, "class_id", None)
        if confidence is None or class_ids is None:
            continue
        dets: list[dict[str, Any]] = []
        for det_idx in range(len(xyxy)):
            raw_class = class_ids[det_idx]
            if raw_class is None or (isinstance(raw_class, float) and math.isnan(raw_class)):
                continue
            score = float(confidence[det_idx])
            x1, y1, x2, y2 = [float(v) for v in xyxy[det_idx]]
            dets.append(
                {
                    "score": score,
                    "bbox": [max(0.0, x1), max(0.0, y1), max(0.0, x2 - x1), max(0.0, y2 - y1)],
                }
            )
        dets.sort(key=lambda item: item["score"], reverse=True)
        for det_rank, det in enumerate(dets[: int(args.max_det_per_image)], start=1):
            bbox_x, bbox_y, bbox_w, bbox_h = det["bbox"]
            path_id = f"iwildcam_l{location_id}_img{image_int}_d{det_rank:03d}_{safe_name(prompt)}"
            universe_rows.append(
                {
                    "dataset": "iWildCam2022",
                    "video_id": location_id,
                    "path_id": path_id,
                    "split": split,
                    "query": prompt,
                    "category_id": category_id,
                    "score": det["score"],
                    "objectness": det["score"],
                    "semantic_margin": det["score"],
                    "temporal_stability": 1.0,
                    "association_score": 0.0,
                    "frame_start": frame_index,
                    "frame_end": frame_index,
                    "path_length": 1,
                    "candidate_rank": 0,
                    "is_dummy": False,
                    "matched_gt_id": f"image_level_animal:{image_uuid}" if animal_present else "",
                    "matched_iou": 1.0 if animal_present else 0.0,
                    "temporal_overlap": 1.0 if animal_present else 0.0,
                    "matched_frames": 1 if animal_present else 0,
                    "is_matched_to_gt": bool(animal_present),
                    "is_unmatched": not bool(animal_present),
                    "audit_label": "",
                    "verified_positive_for_calibration": "no",
                    "cell_id": "animal_present",
                    "novelty_bin": "coarse_animal",
                    "query_cluster": "animal",
                    "occ_bin": "unknown",
                    "domain_bin": f"location:{location_id}",
                    "fallback_level": 0,
                    "score_source": "groundingdino_swint_animal_present",
                    "location_id": location_id,
                    "support_semantics": support_semantics,
                }
            )
            score_rows.append(
                {
                    "video_id": location_id,
                    "path_id": path_id,
                    "release_checkpoint": "final",
                    "score_total": det["score"],
                    "score_obj": det["score"],
                    "score_sem": det["score"],
                    "score_temp": 1.0,
                    "score_assoc": 0.0,
                }
            )
            node_rows.append(
                {
                    "video_id": location_id,
                    "path_id": path_id,
                    "node_index": 0,
                    "image_id": image_int,
                    "frame_index": frame_index,
                    "image_path": str(image_path),
                    "bbox_x": bbox_x,
                    "bbox_y": bbox_y,
                    "bbox_w": bbox_w,
                    "bbox_h": bbox_h,
                    "score": det["score"],
                }
            )
        if int(args.progress_every) > 0 and (pos == 1 or pos % int(args.progress_every) == 0 or pos == len(rows)):
            print(f"[iwildcam-animal-gdino] {pos}/{len(rows)} images, candidates={len(universe_rows)}", flush=True)

    universe = pd.DataFrame(universe_rows, columns=CANDIDATE_UNIVERSE_COLUMNS)
    if not universe.empty:
        universe = universe.sort_values(["score"], ascending=[False]).reset_index(drop=True)
        universe["candidate_rank"] = universe.index + 1
        universe = universe.sort_values(["video_id", "frame_start", "candidate_rank"]).reset_index(drop=True)
    write_csv(out_dir / "candidate_universe.csv", universe.to_dict("records"), CANDIDATE_UNIVERSE_COLUMNS)
    write_csv(out_dir / "candidate_scores.csv", score_rows, CANDIDATE_SCORE_COLUMNS)
    write_csv(out_dir / "candidate_nodes.csv", node_rows, CANDIDATE_NODE_COLUMNS)
    audit_labels = [
        {
            "dataset": row["dataset"],
            "video_id": row["video_id"],
            "path_id": row["path_id"],
            "label": "",
            "reason": "",
            "auditor": "",
            "confidence": "",
            "review_status": "",
            "verified_positive_for_calibration": "no",
        }
        for row in universe_rows
        if row["is_unmatched"]
    ]
    write_csv(out_dir / "audit_labels.csv", audit_labels, AUDIT_LABEL_COLUMNS)
    pseudo_annotation = {
        "videos": [{"id": int(video_id), "name": f"location_{video_id}"} for video_id in sorted(videos_seen)],
        "images": pseudo_images,
        "annotations": pseudo_annotations,
        "categories": [{"id": category_id, "name": "animal"}],
        "metadata": {
            "dataset": "iWildCam2022",
            "support_semantics": support_semantics,
            "target": "coarse animal-present release; official support is image-level animal presence",
        },
    }
    with (out_dir / "iwildcam_pseudo_tracking_annotations.json").open("w", encoding="utf-8") as handle:
        json.dump(pseudo_annotation, handle, indent=2)
    pd.DataFrame(failures).to_csv(out_dir / "inference_failures.csv", index=False)
    summary = {
        "dataset": "iWildCam2022",
        "generator": "GroundingDINO-SwinT",
        "target": "animal_present",
        "support_semantics": support_semantics,
        "prompt": prompt,
        "input_images": len(rows),
        "images_with_failures": len(failures),
        "candidate_rows": int(len(universe)),
        "candidate_nodes": len(node_rows),
        "selected_locations": int(len(videos_seen)),
        "animal_supported_candidate_rows": int((~universe.get("is_unmatched", pd.Series(dtype=bool)).astype(bool)).sum()) if not universe.empty else 0,
        "unsupported_candidate_rows": int(universe.get("is_unmatched", pd.Series(dtype=bool)).astype(bool).sum()) if not universe.empty else 0,
        "box_threshold": args.box_threshold,
        "text_threshold": args.text_threshold,
        "max_det_per_image": args.max_det_per_image,
        "shard_index": int(args.shard_index),
        "num_shards": int(args.num_shards),
    }
    with (out_dir / "candidate_generation_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
