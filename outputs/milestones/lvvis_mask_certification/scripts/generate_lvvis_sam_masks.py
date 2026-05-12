#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch
from pycocotools import mask as mask_utils


def _resolve_image(path_value: str, root: Path) -> Path:
    path = Path(str(path_value))
    if path.is_absolute():
        return path
    return root / path


def _rle_from_mask(mask: np.ndarray) -> dict[str, object]:
    encoded = mask_utils.encode(np.asfortranarray(mask.astype(np.uint8)))
    counts = encoded["counts"]
    if isinstance(counts, bytes):
        counts = counts.decode("ascii")
    encoded["counts"] = counts
    return encoded


def _mask_bbox_area(mask: np.ndarray) -> tuple[float, float, float, float, int]:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return 0.0, 0.0, 0.0, 0.0, 0
    x0, x1 = float(xs.min()), float(xs.max() + 1)
    y0, y1 = float(ys.min()), float(ys.max() + 1)
    return x0, y0, x1 - x0, y1 - y0, int(mask.sum())


def _load_sam(checkpoint: str, model_type: str, device: str):
    from segment_anything import SamPredictor, sam_model_registry

    sam = sam_model_registry[model_type](checkpoint=checkpoint)
    sam.to(device=device)
    sam.eval()
    return SamPredictor(sam)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SAM masks for LVVIS candidate nodes.")
    parser.add_argument("--nodes", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--root", default=os.environ.get("PARC_TRACK_ROOT", "."))
    parser.add_argument(
        "--checkpoint",
        default=str(Path(os.environ.get("PUBLIC_DATASETS_ROOT", ".")) / "ComfyUI/models/sams/sam_vit_b_01ec64.pth"),
    )
    parser.add_argument("--model-type", default="vit_b")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-images", type=int, default=0)
    parser.add_argument("--progress-every", type=int, default=100)
    args = parser.parse_args()

    if args.shard_index < 0 or args.shard_index >= args.shard_count:
        raise ValueError("--shard-index must be in [0, shard-count)")
    root = Path(args.root)
    nodes_path = Path(args.nodes)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    nodes = pd.read_csv(nodes_path)
    required = {"video_id", "path_id", "node_index", "image_id", "frame_index", "image_path", "bbox_x", "bbox_y", "bbox_w", "bbox_h"}
    missing = sorted(required - set(nodes.columns))
    if missing:
        raise ValueError(f"nodes CSV missing required columns: {missing}")

    image_keys = (
        nodes[["image_id", "image_path"]]
        .drop_duplicates()
        .sort_values(["image_id", "image_path"])
        .reset_index(drop=True)
    )
    image_keys = image_keys.iloc[[idx for idx in range(len(image_keys)) if idx % args.shard_count == args.shard_index]]
    if args.max_images > 0:
        image_keys = image_keys.head(args.max_images)
    image_id_set = set(image_keys["image_id"].tolist())
    shard_nodes = nodes[nodes["image_id"].isin(image_id_set)].copy()

    predictor = _load_sam(args.checkpoint, args.model_type, args.device)
    rows: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    processed_images = 0
    processed_nodes = 0

    with torch.inference_mode():
        for image_pos, (_, image_row) in enumerate(image_keys.iterrows(), start=1):
            image_id = image_row["image_id"]
            image_path_value = str(image_row["image_path"])
            image_path = _resolve_image(image_path_value, root)
            image_nodes = shard_nodes[shard_nodes["image_id"] == image_id].copy()
            if image_nodes.empty:
                continue
            image = cv2.imread(str(image_path))
            if image is None:
                failures.append({"image_id": image_id, "image_path": image_path_value, "reason": "image_read_failed"})
                continue
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width = image_rgb.shape[:2]
            predictor.set_image(image_rgb)
            boxes_xyxy = []
            valid_indices = []
            for idx, row in image_nodes.iterrows():
                x = float(row["bbox_x"])
                y = float(row["bbox_y"])
                w = max(1.0, float(row["bbox_w"]))
                h = max(1.0, float(row["bbox_h"]))
                x0 = max(0.0, min(float(width - 1), x))
                y0 = max(0.0, min(float(height - 1), y))
                x1 = max(1.0, min(float(width), x + w))
                y1 = max(1.0, min(float(height), y + h))
                if x1 <= x0 or y1 <= y0:
                    failures.append({"image_id": image_id, "path_id": row["path_id"], "node_index": row["node_index"], "reason": "invalid_box"})
                    continue
                boxes_xyxy.append([x0, y0, x1, y1])
                valid_indices.append(idx)
            if not boxes_xyxy:
                continue
            for start in range(0, len(boxes_xyxy), args.batch_size):
                chunk_boxes = torch.as_tensor(boxes_xyxy[start : start + args.batch_size], dtype=torch.float32, device=args.device)
                transformed = predictor.transform.apply_boxes_torch(chunk_boxes, image_rgb.shape[:2])
                masks, scores, logits = predictor.predict_torch(
                    point_coords=None,
                    point_labels=None,
                    boxes=transformed,
                    multimask_output=False,
                )
                masks_np = masks[:, 0].detach().cpu().numpy().astype(bool)
                scores_np = scores[:, 0].detach().cpu().numpy()
                for local_idx, mask in enumerate(masks_np):
                    src_idx = valid_indices[start + local_idx]
                    node = image_nodes.loc[src_idx]
                    rle = _rle_from_mask(mask)
                    mx, my, mw, mh, marea = _mask_bbox_area(mask)
                    counts = str(rle["counts"])
                    rows.append(
                        {
                            "video_id": node["video_id"],
                            "path_id": node["path_id"],
                            "node_index": int(node["node_index"]),
                            "image_id": node["image_id"],
                            "frame_index": node["frame_index"],
                            "image_path": image_path_value,
                            "image_height": int(height),
                            "image_width": int(width),
                            "bbox_x": float(node["bbox_x"]),
                            "bbox_y": float(node["bbox_y"]),
                            "bbox_w": float(node["bbox_w"]),
                            "bbox_h": float(node["bbox_h"]),
                            "sam_score": float(scores_np[local_idx]),
                            "mask_area": int(marea),
                            "mask_bbox_x": mx,
                            "mask_bbox_y": my,
                            "mask_bbox_w": mw,
                            "mask_bbox_h": mh,
                            "mask_rle_size": json.dumps(rle["size"]),
                            "mask_rle_counts": counts,
                            "mask_hash": hashlib.sha256(counts.encode("utf-8")).hexdigest(),
                            "mask_source": f"sam_{args.model_type}_box_prompt",
                        }
                    )
                    processed_nodes += 1
            processed_images += 1
            if processed_images % args.progress_every == 0:
                print(
                    json.dumps(
                        {
                            "status": "progress",
                            "shard": f"{args.shard_index}/{args.shard_count}",
                            "processed_images": processed_images,
                            "total_images": int(len(image_keys)),
                            "processed_nodes": processed_nodes,
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    out = pd.DataFrame(rows)
    out.to_csv(out_path, index=False)
    report = {
        "status": "completed",
        "nodes": str(nodes_path),
        "out": str(out_path),
        "shard_count": args.shard_count,
        "shard_index": args.shard_index,
        "input_node_rows": int(len(nodes)),
        "shard_image_count": int(len(image_keys)),
        "output_mask_rows": int(len(out)),
        "failures": failures[:100],
        "num_failures": int(len(failures)),
        "checkpoint": args.checkpoint,
        "model_type": args.model_type,
        "device": args.device,
    }
    out_path.with_suffix(".manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
