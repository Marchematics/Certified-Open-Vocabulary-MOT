#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract the OVIS subset from an OVT-B-format annotation file.")
    parser.add_argument("--ann", required=True, help="Input OVT-B annotation JSON.")
    parser.add_argument("--out", required=True, help="Output OVIS-only annotation JSON.")
    parser.add_argument("--prefix", default="OVIS/", help="Video name prefix to keep.")
    args = parser.parse_args()

    ann_path = Path(args.ann)
    out_path = Path(args.out)
    with ann_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    videos = [video for video in payload.get("videos", []) if str(video.get("name", "")).startswith(args.prefix)]
    video_ids = {int(video["id"]) for video in videos}
    images = [image for image in payload.get("images", []) if int(image.get("video_id", -1)) in video_ids]
    image_ids = {int(image["id"]) for image in images}
    annotations = [
        ann
        for ann in payload.get("annotations", [])
        if int(ann.get("video_id", -1)) in video_ids and int(ann.get("image_id", -1)) in image_ids
    ]
    track_ids = {int(ann.get("track_id", -1)) for ann in annotations}
    tracks = [track for track in payload.get("tracks", []) if int(track.get("id", -1)) in track_ids]
    category_ids = {int(item.get("category_id", -1)) for item in annotations}
    categories = [cat for cat in payload.get("categories", []) if int(cat.get("id", -1)) in category_ids]

    subset = {
        "images": images,
        "videos": videos,
        "tracks": tracks,
        "annotations": annotations,
        "categories": categories,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(subset, handle, ensure_ascii=False)
    summary_path = out_path.with_suffix(".summary.json")
    summary = {
        "source_annotation": str(ann_path),
        "output_annotation": str(out_path),
        "video_prefix": args.prefix,
        "videos": len(videos),
        "images": len(images),
        "tracks": len(tracks),
        "annotations": len(annotations),
        "categories": len(categories),
    }
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
