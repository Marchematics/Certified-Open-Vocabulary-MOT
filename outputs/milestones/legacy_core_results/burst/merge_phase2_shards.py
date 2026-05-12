#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import pandas as pd

from parc_track.phase2 import AUDIT_COLUMNS, AUDIT_LABEL_COLUMNS, CANDIDATE_NODE_COLUMNS, CANDIDATE_SCORE_COLUMNS, CANDIDATE_UNIVERSE_COLUMNS


def _read_csvs(paths: list[Path], columns: list[str]) -> pd.DataFrame:
    frames = []
    for path in paths:
        if path.exists():
            frames.append(pd.read_csv(path))
    if not frames:
        return pd.DataFrame(columns=columns)
    frame = pd.concat(frames, ignore_index=True, sort=False)
    for column in columns:
        if column not in frame:
            frame[column] = ""
    return frame


def _select_audit_candidates(candidates: pd.DataFrame, total_samples: int, top_b_per_cell: int) -> pd.DataFrame:
    if candidates.empty:
        return candidates.reindex(columns=AUDIT_COLUMNS)
    frame = candidates.copy()
    frame["score_num"] = pd.to_numeric(frame.get("score", 0), errors="coerce").fillna(0.0)
    frame = frame.sort_values("score_num", ascending=False).drop_duplicates("path_id", keep="first")
    selected = []
    seen: set[str] = set()
    if "cell_id" in frame:
        for _, cell_rows in frame.groupby(frame["cell_id"].fillna("").astype(str), dropna=False):
            for _, row in cell_rows.sort_values("score_num", ascending=False).head(top_b_per_cell).iterrows():
                path_id = str(row["path_id"])
                if path_id not in seen:
                    selected.append(row)
                    seen.add(path_id)
    for _, row in frame.iterrows():
        if len(selected) >= total_samples:
            break
        path_id = str(row["path_id"])
        if path_id not in seen:
            selected.append(row)
            seen.add(path_id)
    if not selected:
        return pd.DataFrame(columns=AUDIT_COLUMNS)
    out = pd.DataFrame(selected).head(total_samples)
    for column in AUDIT_COLUMNS:
        if column not in out:
            out[column] = ""
    return out[AUDIT_COLUMNS]


def _write_index(viewer_dir: Path, candidates: pd.DataFrame) -> Path:
    viewer_dir.mkdir(parents=True, exist_ok=True)
    index = viewer_dir / "index.html"
    rows = []
    for _, row in candidates.iterrows():
        montage = str(row.get("montage_path", ""))
        link = f'<a href="{montage}">montage</a>' if montage else ""
        rows.append(
            "<tr>"
            f"<td>{row.get('dataset','')}</td>"
            f"<td>{row.get('video_id','')}</td>"
            f"<td>{row.get('path_id','')}</td>"
            f"<td>{row.get('query','')}</td>"
            f"<td>{row.get('score','')}</td>"
            f"<td>{link}</td>"
            "</tr>"
        )
    index.write_text(
        "<!doctype html><html><head><meta charset='utf-8'><title>BURST Audit</title>"
        "<style>body{font-family:Arial,sans-serif;margin:2rem}td,th{border:1px solid #ddd;padding:4px}"
        "table{border-collapse:collapse}</style></head><body>"
        "<h1>BURST Audit Candidates</h1>"
        "<table><thead><tr><th>dataset</th><th>video</th><th>path</th><th>query</th><th>score</th><th>media</th></tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table></body></html>",
        encoding="utf-8",
    )
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--shard-dir", action="append", required=True)
    parser.add_argument("--total-samples", type=int, default=200)
    parser.add_argument("--top-b-per-cell", type=int, default=10)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    shard_dirs = [Path(value) for value in args.shard_dir]

    universe = _read_csvs([path / "candidate_universe.csv" for path in shard_dirs], CANDIDATE_UNIVERSE_COLUMNS)
    if not universe.empty:
        universe["score_num"] = pd.to_numeric(universe.get("score", 0), errors="coerce").fillna(0.0)
        universe = universe.sort_values("score_num", ascending=False).drop_duplicates("path_id", keep="first")
        universe["candidate_rank"] = range(1, len(universe) + 1)
        universe = universe.drop(columns=["score_num"])
    universe[CANDIDATE_UNIVERSE_COLUMNS].to_csv(output_dir / "candidate_universe.csv", index=False)

    scores = _read_csvs([path / "candidate_scores.csv" for path in shard_dirs], CANDIDATE_SCORE_COLUMNS)
    if not scores.empty:
        scores = scores.drop_duplicates(["video_id", "path_id", "release_checkpoint"], keep="first")
    scores[CANDIDATE_SCORE_COLUMNS].to_csv(output_dir / "candidate_scores.csv", index=False)

    nodes = _read_csvs([path / "candidate_nodes.csv" for path in shard_dirs], CANDIDATE_NODE_COLUMNS)
    if not nodes.empty:
        nodes = nodes.drop_duplicates(["video_id", "path_id", "node_index"], keep="first")
    nodes[CANDIDATE_NODE_COLUMNS].to_csv(output_dir / "candidate_nodes.csv", index=False)

    shard_candidates = _read_csvs([path / "audit_candidates.csv" for path in shard_dirs], AUDIT_COLUMNS)
    candidates = _select_audit_candidates(shard_candidates, args.total_samples, args.top_b_per_cell)
    candidates.to_csv(output_dir / "audit_candidates.csv", index=False)

    labels_path = output_dir / "audit_labels.csv"
    with labels_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
        writer.writeheader()
        for _, row in candidates.iterrows():
            writer.writerow(
                {
                    "dataset": row.get("dataset", ""),
                    "video_id": row.get("video_id", ""),
                    "path_id": row.get("path_id", ""),
                    "label": "",
                    "reason": "",
                    "auditor": "",
                    "confidence": "",
                    "review_status": "",
                    "verified_positive_for_calibration": "",
                }
            )

    index = _write_index(output_dir / "audit_viewer", candidates)
    manifests: list[dict[str, Any]] = []
    for shard in shard_dirs:
        manifest_path = shard / "audit_manifest.json"
        if manifest_path.exists():
            with manifest_path.open("r", encoding="utf-8") as handle:
                manifests.append(json.load(handle))
    manifest = {
        "status": "completed",
        "merge_source": "phase2_propose_shards",
        "num_shards": len(shard_dirs),
        "num_videos_processed": int(sum(int(item.get("num_videos_processed", 0)) for item in manifests)),
        "num_frame_detections": int(sum(int(item.get("num_frame_detections", 0)) for item in manifests)),
        "num_paths": int(len(universe)),
        "num_unmatched_paths_in_shard_audit_pool": int(len(shard_candidates.drop_duplicates("path_id"))) if not shard_candidates.empty else 0,
        "num_exported_candidates": int(len(candidates)),
        "candidate_universe": {"csv": str(output_dir / "candidate_universe.csv"), "rows": int(len(universe))},
        "candidate_scores": {"csv": str(output_dir / "candidate_scores.csv"), "rows": int(len(scores))},
        "candidate_nodes": {"csv": str(output_dir / "candidate_nodes.csv"), "rows": int(len(nodes))},
        "candidate_csv": str(output_dir / "audit_candidates.csv"),
        "label_template_csv": str(labels_path),
        "viewer_index": str(index),
        "shards": manifests,
    }
    (output_dir / "audit_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
