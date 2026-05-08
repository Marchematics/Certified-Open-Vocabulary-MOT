from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DATA_ROOT = Path("/home/waas/paper_experiments")


def _is_under_workspace(path: Path) -> bool:
    resolved = path.resolve()
    return resolved == DATA_ROOT or DATA_ROOT in resolved.parents


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _max_id(rows: list[dict[str, Any]]) -> int:
    values = [int(row["id"]) for row in rows if "id" in row]
    return max(values) if values else -1


def _offset_rows(rows: list[dict[str, Any]], offset: int, key: str = "id") -> tuple[list[dict[str, Any]], dict[int, int]]:
    mapping: dict[int, int] = {}
    out: list[dict[str, Any]] = []
    for row in rows:
        copied = dict(row)
        if key in copied:
            old = int(copied[key])
            new = old + offset
            copied[key] = new
            mapping[old] = new
        out.append(copied)
    return out, mapping


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", default=str(DATA_ROOT / "data" / "TAO" / "annotations" / "train.json"))
    parser.add_argument("--val", default=str(DATA_ROOT / "data" / "TAO" / "annotations" / "validation.json"))
    parser.add_argument("--out", default=str(DATA_ROOT / "data" / "TAO" / "annotations" / "trainval.json"))
    parser.add_argument(
        "--report",
        default=str(DATA_ROOT / "outputs" / "phase3_tao_full" / "tao_trainval_merge_report.json"),
    )
    args = parser.parse_args()

    train_path = Path(args.train)
    val_path = Path(args.val)
    out_path = Path(args.out).resolve()
    report_path = Path(args.report).resolve()
    if not _is_under_workspace(out_path) or not _is_under_workspace(report_path):
        raise SystemExit("Refusing to write outside /home/waas/paper_experiments")
    train = _load(train_path)
    val = _load(val_path)

    video_offset = _max_id(train.get("videos", [])) + 1
    image_offset = _max_id(train.get("images", [])) + 1
    ann_offset = _max_id(train.get("annotations", [])) + 1
    track_offset = _max_id(train.get("tracks", [])) + 1

    val_videos, video_map = _offset_rows(val.get("videos", []), video_offset)
    val_images, image_map = _offset_rows(val.get("images", []), image_offset)
    val_tracks, track_map = _offset_rows(val.get("tracks", []), track_offset)
    val_anns, _ = _offset_rows(val.get("annotations", []), ann_offset)

    for row in val_images:
        if "video_id" in row:
            row["video_id"] = video_map[int(row["video_id"])]
        row["source_split"] = "validation"
    for row in val_tracks:
        if "video_id" in row:
            row["video_id"] = video_map[int(row["video_id"])]
        row["source_split"] = "validation"
    for row in val_anns:
        if "image_id" in row:
            row["image_id"] = image_map[int(row["image_id"])]
        if "video_id" in row:
            row["video_id"] = video_map[int(row["video_id"])]
        if "track_id" in row:
            row["track_id"] = track_map[int(row["track_id"])]
        row["source_split"] = "validation"

    train_videos = [dict(row, source_split="train") for row in train.get("videos", [])]
    train_images = [dict(row, source_split="train") for row in train.get("images", [])]
    train_tracks = [dict(row, source_split="train") for row in train.get("tracks", [])]
    train_anns = [dict(row, source_split="train") for row in train.get("annotations", [])]

    merged = {
        "info": {
            "description": "TAO train+validation merged for PARC-Track full second-dataset scaffold.",
            "source_train": str(train_path),
            "source_validation": str(val_path),
        },
        "licenses": train.get("licenses", val.get("licenses", [])),
        "categories": train.get("categories", val.get("categories", [])),
        "videos": train_videos + val_videos,
        "images": train_images + val_images,
        "tracks": train_tracks + val_tracks,
        "annotations": train_anns + val_anns,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    report = {
        "status": "completed",
        "out": str(out_path),
        "train": {
            "videos": len(train.get("videos", [])),
            "images": len(train.get("images", [])),
            "annotations": len(train.get("annotations", [])),
            "tracks": len(train.get("tracks", [])),
        },
        "validation": {
            "videos": len(val.get("videos", [])),
            "images": len(val.get("images", [])),
            "annotations": len(val.get("annotations", [])),
            "tracks": len(val.get("tracks", [])),
        },
        "merged": {
            "videos": len(merged["videos"]),
            "images": len(merged["images"]),
            "annotations": len(merged["annotations"]),
            "tracks": len(merged["tracks"]),
            "categories": len(merged["categories"]),
        },
        "offsets": {
            "video_offset": video_offset,
            "image_offset": image_offset,
            "annotation_offset": ann_offset,
            "track_offset": track_offset,
        },
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
