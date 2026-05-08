#!/usr/bin/env python3
"""Merge sharded audit-sample outputs into one Phase-2/3 candidate universe."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pandas as pd

from parc_track.phase2 import (
    AUDIT_COLUMNS,
    AUDIT_LABEL_COLUMNS,
    CANDIDATE_NODE_COLUMNS,
    CANDIDATE_SCORE_COLUMNS,
    CANDIDATE_UNIVERSE_COLUMNS,
)


def _read_csvs(paths: list[Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        if path.exists() and path.stat().st_size > 0:
            try:
                frames.append(pd.read_csv(path))
            except pd.errors.EmptyDataError:
                pass
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _write_frame(frame: pd.DataFrame, path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for column in columns:
        if column not in out:
            out[column] = ""
    out = out[columns]
    out.to_csv(path, index=False)


def _write_labels_template(labels_path: Path, selected: pd.DataFrame) -> None:
    should_write = True
    if labels_path.exists():
        try:
            existing = pd.read_csv(labels_path)
            label_col = existing.get("label", pd.Series(dtype=str))
            should_write = existing.empty or not label_col.fillna("").astype(str).str.strip().any()
        except Exception:
            should_write = True
    if not should_write:
        return
    labels_path.parent.mkdir(parents=True, exist_ok=True)
    with labels_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
        writer.writeheader()
        for _, row in selected.iterrows():
            writer.writerow(
                {
                    "dataset": row.get("dataset", ""),
                    "video_id": row.get("video_id", ""),
                    "path_id": row.get("path_id", ""),
                    "label": "",
                    "reason": "",
                    "auditor": "",
                    "confidence": "",
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--total-samples", type=int, default=500)
    parser.add_argument("--top-b-per-cell", type=int, default=15)
    args = parser.parse_args()

    shard_root = Path(args.shard_root)
    out_dir = Path(args.out_dir)
    shard_dirs = sorted(path for path in shard_root.glob("shard_*") if path.is_dir())
    manifests = []
    for shard_dir in shard_dirs:
        manifest_path = shard_dir / "audit_manifest.json"
        if manifest_path.exists():
            with manifest_path.open("r", encoding="utf-8") as handle:
                manifests.append(json.load(handle))

    universe = _read_csvs([path / "candidate_universe.csv" for path in shard_dirs])
    scores = _read_csvs([path / "candidate_scores.csv" for path in shard_dirs])
    nodes = _read_csvs([path / "candidate_nodes.csv" for path in shard_dirs])
    candidates = _read_csvs([path / "audit_candidates.csv" for path in shard_dirs])

    if not universe.empty:
        universe = universe.drop_duplicates(["dataset", "video_id", "path_id"], keep="first")
        universe = universe.sort_values("score", ascending=False).reset_index(drop=True)
        universe["candidate_rank"] = range(1, len(universe) + 1)
    if not scores.empty:
        scores = scores.drop_duplicates(["video_id", "path_id", "release_checkpoint"], keep="first")
    if not nodes.empty:
        nodes = nodes.drop_duplicates(["video_id", "path_id", "node_index", "image_id"], keep="first")
    if not candidates.empty:
        candidates = candidates.drop_duplicates(["dataset", "video_id", "path_id"], keep="first")
        candidates = candidates.sort_values("score", ascending=False)
        selected = []
        seen: set[str] = set()
        if "cell_id" in candidates:
            for _, group in candidates.groupby(candidates["cell_id"].astype(str), sort=False):
                for _, row in group.head(args.top_b_per_cell).iterrows():
                    selected.append(row)
                    seen.add(str(row["path_id"]))
        for _, row in candidates.iterrows():
            if len(selected) >= args.total_samples:
                break
            path_id = str(row["path_id"])
            if path_id not in seen:
                selected.append(row)
                seen.add(path_id)
        candidates = pd.DataFrame(selected[: args.total_samples]) if selected else candidates.head(0)

    _write_frame(universe, out_dir / "candidate_universe.csv", CANDIDATE_UNIVERSE_COLUMNS)
    _write_frame(scores, out_dir / "candidate_scores.csv", CANDIDATE_SCORE_COLUMNS)
    _write_frame(nodes, out_dir / "candidate_nodes.csv", CANDIDATE_NODE_COLUMNS)
    _write_frame(candidates, out_dir / "audit_candidates.csv", AUDIT_COLUMNS)
    _write_labels_template(out_dir / "audit_labels.csv", candidates)

    manifest = {
        "status": "completed",
        "mode": "merged_shards",
        "shard_root": str(shard_root),
        "num_shards": len(shard_dirs),
        "num_completed_shards": len(manifests),
        "num_videos_processed": int(sum(int(item.get("num_videos_processed", 0)) for item in manifests)),
        "num_frame_detections": int(sum(int(item.get("num_frame_detections", 0)) for item in manifests)),
        "num_paths": int(len(universe)),
        "num_unmatched_paths": int(len(candidates)) if candidates.empty else int(_read_csvs([path / "audit_candidates.csv" for path in shard_dirs]).drop_duplicates(["dataset", "video_id", "path_id"], keep="first").shape[0]),
        "num_exported_candidates": int(len(candidates)),
        "candidate_csv": str(out_dir / "audit_candidates.csv"),
        "label_template_csv": str(out_dir / "audit_labels.csv"),
        "candidate_universe": {"csv": str(out_dir / "candidate_universe.csv")},
        "candidate_scores": {"csv": str(out_dir / "candidate_scores.csv")},
        "candidate_nodes": {"csv": str(out_dir / "candidate_nodes.csv")},
        "shards": manifests,
    }
    with (out_dir / "audit_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    print(json.dumps(manifest, indent=2)[:4000])


if __name__ == "__main__":
    main()
