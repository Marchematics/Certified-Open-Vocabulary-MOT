#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import tifffile


FRAME_RE = re.compile(r"(?:man_seg|man_track)(\d+)\.tif$")


@dataclass(frozen=True)
class Obj:
    dataset: str
    sequence: str
    frame: int
    label: int
    area: int
    cx: float
    cy: float
    x0: int
    y0: int
    x1: int
    y1: int
    gt_label: int
    gt_purity: float


def frame_index(path: Path) -> int:
    match = FRAME_RE.search(path.name)
    if not match:
        raise ValueError(f"cannot parse frame index from {path}")
    return int(match.group(1))


def bbox_iou(a: Obj, b: Obj) -> float:
    ix0 = max(a.x0, b.x0)
    iy0 = max(a.y0, b.y0)
    ix1 = min(a.x1, b.x1)
    iy1 = min(a.y1, b.y1)
    iw = max(0, ix1 - ix0 + 1)
    ih = max(0, iy1 - iy0 + 1)
    inter = iw * ih
    union = (a.x1 - a.x0 + 1) * (a.y1 - a.y0 + 1) + (b.x1 - b.x0 + 1) * (b.y1 - b.y0 + 1) - inter
    return float(inter / union) if union else 0.0


def read_lineage(track_txt: Path) -> dict[int, dict[str, int]]:
    rows: dict[int, dict[str, int]] = {}
    if not track_txt.exists():
        return rows
    with track_txt.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.strip().split()
            if len(parts) != 4:
                continue
            cell_id, start, end, parent = (int(part) for part in parts)
            rows[cell_id] = {"start": start, "end": end, "parent": parent}
    return rows


def extract_objects(dataset: str, sequence: str, frame: int, seg_mask: np.ndarray, tra_mask: np.ndarray) -> list[Obj]:
    objects: list[Obj] = []
    labels = np.unique(seg_mask)
    labels = labels[labels > 0]
    for label_value in labels.tolist():
        ys, xs = np.nonzero(seg_mask == int(label_value))
        if len(xs) == 0:
            continue
        gt_values = tra_mask[ys, xs]
        gt_values = gt_values[gt_values > 0]
        gt_label = 0
        gt_purity = 0.0
        if len(gt_values):
            gt_labels, gt_counts = np.unique(gt_values, return_counts=True)
            best = int(np.argmax(gt_counts))
            gt_label = int(gt_labels[best])
            gt_purity = float(gt_counts[best] / len(xs))
        objects.append(
            Obj(
                dataset=dataset,
                sequence=sequence,
                frame=frame,
                label=int(label_value),
                area=int(len(xs)),
                cx=float(xs.mean()),
                cy=float(ys.mean()),
                x0=int(xs.min()),
                y0=int(ys.min()),
                x1=int(xs.max()),
                y1=int(ys.max()),
                gt_label=gt_label,
                gt_purity=gt_purity,
            )
        )
    return objects


def load_sequence(
    root: Path,
    dataset: str,
    sequence: str,
    node_source: str,
) -> tuple[dict[int, list[Obj]], dict[int, dict[str, int]]]:
    seq_root = root / dataset
    tra_dir = seq_root / f"{sequence}_GT" / "TRA"
    if node_source == "gt_tra":
        node_dir = tra_dir
        node_prefix = "man_track"
    else:
        node_dir = seq_root / f"{sequence}_ST" / "SEG"
        node_prefix = "man_seg"
    lineage = read_lineage(tra_dir / "man_track.txt")
    node_paths = {frame_index(path): path for path in node_dir.glob(f"{node_prefix}*.tif")}
    tra_paths = {frame_index(path): path for path in tra_dir.glob("man_track*.tif")}
    common = sorted(set(node_paths) & set(tra_paths))
    by_frame: dict[int, list[Obj]] = {}
    for frame in common:
        seg_mask = tifffile.imread(node_paths[frame])
        tra_mask = tifffile.imread(tra_paths[frame])
        by_frame[frame] = extract_objects(dataset, sequence, frame, seg_mask, tra_mask)
    return by_frame, lineage


def is_true_link(source: Obj, target: Obj, lineage: dict[int, dict[str, int]], min_gt_purity: float) -> bool:
    if source.gt_label <= 0 or target.gt_label <= 0:
        return False
    if source.gt_purity < min_gt_purity or target.gt_purity < min_gt_purity:
        return False
    if source.gt_label == target.gt_label:
        return True
    target_info = lineage.get(target.gt_label, {})
    return int(target_info.get("parent", 0)) == int(source.gt_label)


def link_score(source: Obj, target: Obj) -> tuple[float, float, float, float]:
    dist = math.hypot(float(source.cx - target.cx), float(source.cy - target.cy))
    size_norm = math.sqrt(max(source.area, 1)) + math.sqrt(max(target.area, 1))
    dist_score = 1.0 / (1.0 + dist / max(size_norm, 1.0))
    iou = bbox_iou(source, target)
    area_ratio = min(source.area, target.area) / max(source.area, target.area)
    score = 0.68 * dist_score + 0.22 * iou + 0.10 * area_ratio
    return float(score), float(dist_score), float(iou), float(area_ratio)


def stable_unit_interval(value: str) -> float:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(16**12 - 1)


def build_universe(
    root: Path,
    datasets: list[str],
    out_dir: Path,
    topk_per_source: int,
    frame_window: int,
    min_gt_purity: float,
    node_source: str,
    noisy_linker_weight: float,
) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    universe_rows: list[dict[str, object]] = []
    node_rows: list[dict[str, object]] = []
    score_rows: list[dict[str, object]] = []
    ann_images: list[dict[str, object]] = []
    ann_rows: list[dict[str, object]] = []
    dataset_reports: list[dict[str, object]] = []
    video_id_map: dict[tuple[str, str, int], int] = {}
    next_video_id = 1
    ann_id = 1

    for dataset in datasets:
        dataset_root = root / dataset
        if not dataset_root.exists():
            raise FileNotFoundError(dataset_root)
        for sequence in ("01", "02"):
            print(f"[ctc-link] loading {dataset}/{sequence}", flush=True)
            by_frame, lineage = load_sequence(root, dataset, sequence, node_source=node_source)
            frames = sorted(by_frame)
            candidate_count = 0
            supported_count = 0
            for frame in frames[:-1]:
                if frame + 1 not in by_frame:
                    continue
                window = frame // frame_window
                key = (dataset, sequence, window)
                if key not in video_id_map:
                    video_id_map[key] = next_video_id
                    next_video_id += 1
                video_id = video_id_map[key]
                sources = by_frame[frame]
                targets = by_frame[frame + 1]
                if not sources or not targets:
                    continue
                target_xy = np.asarray([(target.cx, target.cy) for target in targets], dtype=float)
                tree = cKDTree(target_xy)
                ann_images.append(
                    {
                        "id": f"{dataset}_{sequence}_{frame:03d}_{frame + 1:03d}",
                        "video_id": video_id,
                        "file_name": f"{dataset}/{sequence}/frame_pair_{frame:03d}_{frame + 1:03d}",
                        "frame_index": frame,
                    }
                )
                for source in sources:
                    k = min(int(topk_per_source), len(targets))
                    distances, indices = tree.query((source.cx, source.cy), k=k)
                    indices_array = np.atleast_1d(indices)
                    scored_targets = []
                    for target_idx in indices_array.tolist():
                        target = targets[int(target_idx)]
                        score, dist_score, iou, area_ratio = link_score(source, target)
                        scored_targets.append((score, dist_score, iou, area_ratio, target))
                    scored_targets.sort(key=lambda item: item[0], reverse=True)
                    for score, dist_score, iou, area_ratio, target in scored_targets:
                        true_link = is_true_link(source, target, lineage, min_gt_purity)
                        matched_gt_id = (
                            f"{dataset}:{sequence}:gt{source.gt_label}->gt{target.gt_label}:f{frame:03d}"
                            if true_link
                            else ""
                        )
                        path_id = (
                            f"ctc_{dataset}_{sequence}_f{frame:03d}_s{source.label}"
                            f"_to_f{frame + 1:03d}_t{target.label}"
                        )
                        if noisy_linker_weight > 0:
                            noise = stable_unit_interval(path_id)
                            score = (1.0 - noisy_linker_weight) * score + noisy_linker_weight * noise
                            score = max(0.0, min(1.0, score))
                        candidate_count += 1
                        supported_count += int(true_link)
                        universe_rows.append(
                            {
                                "dataset": "CTC",
                                "ctc_dataset": dataset,
                                "sequence_id": sequence,
                                "frame_pair": f"{frame:03d}-{frame + 1:03d}",
                                "video_id": video_id,
                                "path_id": path_id,
                                "split": "",
                                "query": "cell_link",
                                "category_id": 1,
                                "score": score,
                                "objectness": dist_score,
                                "semantic_margin": area_ratio,
                                "temporal_stability": iou,
                                "association_score": score,
                                "frame_start": frame,
                                "frame_end": frame + 1,
                                "path_length": 2,
                                "candidate_rank": 0,
                                "is_dummy": False,
                                "matched_gt_id": matched_gt_id,
                                "matched_iou": min(source.gt_purity, target.gt_purity) if true_link else 0.0,
                                "temporal_overlap": 1.0 if true_link else 0.0,
                                "matched_frames": 2 if true_link else 0,
                                "is_matched_to_gt": bool(true_link),
                                "is_unmatched": not bool(true_link),
                                "audit_label": "",
                                "verified_positive_for_calibration": "no",
                                "cell_id": f"cell_link/{dataset}",
                                "novelty_bin": dataset,
                                "query_cluster": "cell_link",
                                "occ_bin": "microscopy",
                                "domain_bin": f"{dataset}:{sequence}",
                                "fallback_level": "ctc_link",
                                "score_source": (
                                    f"{node_source}_distance_bbox_iou_area_link_score"
                                    if noisy_linker_weight <= 0
                                    else f"{node_source}_noisy_geometric_linker_w{noisy_linker_weight:g}"
                                ),
                                "source_gt_label": source.gt_label,
                                "target_gt_label": target.gt_label,
                                "source_gt_purity": source.gt_purity,
                                "target_gt_purity": target.gt_purity,
                                "source_area": source.area,
                                "target_area": target.area,
                                "link_distance_score": dist_score,
                                "bbox_iou": iou,
                                "area_ratio": area_ratio,
                            }
                        )
                        node_rows.extend(
                            [
                                {
                                    "video_id": video_id,
                                    "path_id": path_id,
                                    "node_index": 0,
                                    "image_id": f"{dataset}_{sequence}_{frame:03d}",
                                    "frame_index": frame,
                                    "image_path": f"{dataset}/{sequence}/t{frame:03d}",
                                    "bbox_x": source.x0,
                                    "bbox_y": source.y0,
                                    "bbox_w": source.x1 - source.x0 + 1,
                                    "bbox_h": source.y1 - source.y0 + 1,
                                    "score": score,
                                },
                                {
                                    "video_id": video_id,
                                    "path_id": path_id,
                                    "node_index": 1,
                                    "image_id": f"{dataset}_{sequence}_{frame + 1:03d}",
                                    "frame_index": frame + 1,
                                    "image_path": f"{dataset}/{sequence}/t{frame + 1:03d}",
                                    "bbox_x": target.x0,
                                    "bbox_y": target.y0,
                                    "bbox_w": target.x1 - target.x0 + 1,
                                    "bbox_h": target.y1 - target.y0 + 1,
                                    "score": score,
                                },
                            ]
                        )
                        score_rows.append(
                            {
                                "video_id": video_id,
                                "path_id": path_id,
                                "release_checkpoint": "final",
                                "score_total": score,
                                "score_obj": dist_score,
                                "score_sem": area_ratio,
                                "score_temp": iou,
                                "score_assoc": score,
                            }
                        )
                        if true_link:
                            ann_rows.append(
                                {
                                    "id": ann_id,
                                    "video_id": video_id,
                                    "image_id": f"{dataset}_{sequence}_{frame:03d}_{frame + 1:03d}",
                                    "category_id": 1,
                                    "track_id": int(source.gt_label),
                                    "bbox": [source.x0, source.y0, source.x1 - source.x0 + 1, source.y1 - source.y0 + 1],
                                    "linked_track_id": int(target.gt_label),
                                    "frame_pair": f"{frame:03d}-{frame + 1:03d}",
                                }
                            )
                            ann_id += 1
            dataset_reports.append(
                {
                    "ctc_dataset": dataset,
                    "sequence_id": sequence,
                    "frames": len(frames),
                    "candidate_links": candidate_count,
                    "gold_supported_candidate_links": supported_count,
                    "unsupported_candidate_links": candidate_count - supported_count,
                }
            )
            print(
                f"[ctc-link] {dataset}/{sequence}: frames={len(frames)} candidates={candidate_count} "
                f"supported={supported_count}",
                flush=True,
            )

    universe = pd.DataFrame(universe_rows)
    if universe.empty:
        raise RuntimeError("CTC link candidate universe is empty")
    universe = universe.sort_values("score", ascending=False).reset_index(drop=True)
    universe["candidate_rank"] = np.arange(1, len(universe) + 1)
    # Keep the public candidate schema columns first while preserving CTC-specific diagnostics.
    public_cols = [
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
    ]
    extra_cols = [col for col in universe.columns if col not in public_cols]
    universe[public_cols + extra_cols].to_csv(out_dir / "candidate_universe.csv", index=False)
    pd.DataFrame(node_rows).to_csv(out_dir / "candidate_nodes.csv", index=False)
    pd.DataFrame(score_rows).to_csv(out_dir / "candidate_scores.csv", index=False)
    labels = universe[["dataset", "video_id", "path_id", "query", "category_id", "score"]].copy()
    labels["label"] = ""
    labels["reason"] = ""
    labels["auditor"] = ""
    labels["confidence"] = ""
    labels["review_status"] = ""
    labels["verified_positive_for_calibration"] = "no"
    labels.to_csv(out_dir / "audit_labels.csv", index=False)
    pseudo_ann = {
        "datasets": datasets,
        "support_semantics": "ctc_stseg_links_supported_by_gt_tracking_truth",
        "videos": [
            {"id": video_id, "name": f"{dataset}:{sequence}:window{window}"}
            for (dataset, sequence, window), video_id in sorted(video_id_map.items(), key=lambda item: item[1])
        ],
        "images": ann_images,
        "annotations": ann_rows,
        "categories": [{"id": 1, "name": "cell_link"}],
    }
    with (out_dir / "ctc_link_pseudo_annotations.json").open("w", encoding="utf-8") as handle:
        json.dump(pseudo_ann, handle, indent=2)
    report = {
        "status": "completed",
        "ctc_root": str(root),
        "datasets": datasets,
        "topk_per_source": topk_per_source,
        "frame_window": frame_window,
        "min_gt_purity": min_gt_purity,
        "node_source": node_source,
        "noisy_linker_weight": noisy_linker_weight,
        "candidate_universe": str(out_dir / "candidate_universe.csv"),
        "candidate_nodes": str(out_dir / "candidate_nodes.csv"),
        "candidate_scores": str(out_dir / "candidate_scores.csv"),
        "audit_labels": str(out_dir / "audit_labels.csv"),
        "pseudo_annotations": str(out_dir / "ctc_link_pseudo_annotations.json"),
        "candidate_rows": int(len(universe)),
        "video_blocks": int(universe["video_id"].nunique()),
        "official_supported_candidate_rows": int((~universe["is_unmatched"].astype(bool)).sum()),
        "unsupported_candidate_rows": int(universe["is_unmatched"].astype(bool).sum()),
        "dataset_reports": dataset_reports,
    }
    pd.DataFrame(dataset_reports).to_csv(out_dir / "ctc_link_dataset_report.csv", index=False)
    with (out_dir / "CTC_LINK_UNIVERSE_REPORT.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ctc-root", default="data/CTC/training")
    parser.add_argument("--out-dir", default="outputs/ctc_link_certification/universe")
    parser.add_argument(
        "--datasets",
        default="DIC-C2DH-HeLa,Fluo-N2DH-GOWT1,Fluo-N2DL-HeLa,PhC-C2DH-U373",
    )
    parser.add_argument("--topk-per-source", type=int, default=5)
    parser.add_argument("--frame-window", type=int, default=10)
    parser.add_argument("--min-gt-purity", type=float, default=0.5)
    parser.add_argument("--node-source", choices=["st_seg", "gt_tra"], default="gt_tra")
    parser.add_argument("--noisy-linker-weight", type=float, default=0.0)
    args = parser.parse_args()
    datasets = [item.strip() for item in args.datasets.split(",") if item.strip()]
    report = build_universe(
        root=Path(args.ctc_root),
        datasets=datasets,
        out_dir=Path(args.out_dir),
        topk_per_source=int(args.topk_per_source),
        frame_window=int(args.frame_window),
        min_gt_purity=float(args.min_gt_purity),
        node_source=str(args.node_source),
        noisy_linker_weight=float(args.noisy_linker_weight),
    )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
