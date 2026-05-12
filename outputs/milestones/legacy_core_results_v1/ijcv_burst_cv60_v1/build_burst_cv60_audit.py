#!/usr/bin/env python3
"""Build a 60-path BURST audit cross-validation packet.

The packet is intentionally split into a blind relabel template and a
reference-label file. The reference labels come from the existing
model-assisted BURST audit and must not be shown to an independent rater.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_BURST_DIR = Path("<PARC_ROOT>/outputs/phase7_burst")
DEFAULT_OUT_DIR = Path("<PARC_ROOT>/outputs/phase7_burst_cv60")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_yes(value: object) -> str:
    text = str(value).strip().lower()
    return "yes" if text in {"yes", "true", "1", "y"} else "no"


def assign_query_segments(universe: pd.DataFrame) -> dict[str, str]:
    counts = universe["query"].fillna("unknown").value_counts()
    queries = counts.index.tolist()
    n = len(queries)
    head_cut = max(1, math.ceil(0.20 * n))
    mid_cut = max(head_cut, math.ceil(0.50 * n))
    segments: dict[str, str] = {}
    for rank, query in enumerate(queries, start=1):
        if rank <= head_cut:
            segment = "head"
        elif rank <= mid_cut:
            segment = "mid"
        else:
            segment = "tail"
        segments[str(query)] = segment
    return segments


def stratified_sample(
    pool: pd.DataFrame,
    n: int,
    *,
    seed: int,
    strata_col: str = "query_segment",
) -> pd.DataFrame:
    if n <= 0 or pool.empty:
        return pool.head(0)
    n = min(n, len(pool))
    groups = [(name, group) for name, group in pool.groupby(strata_col, dropna=False)]
    groups.sort(key=lambda item: str(item[0]))
    base = n // max(1, len(groups))
    rem = n % max(1, len(groups))

    picked_parts = []
    picked_indices: set[int] = set()
    for idx, (_, group) in enumerate(groups):
        quota = base + (1 if idx < rem else 0)
        quota = min(quota, len(group))
        if quota <= 0:
            continue
        sampled = group.sample(n=quota, random_state=seed + idx)
        picked_parts.append(sampled)
        picked_indices.update(sampled.index.tolist())

    picked = pd.concat(picked_parts, ignore_index=False) if picked_parts else pool.head(0)
    if len(picked) < n:
        remaining = pool.loc[~pool.index.isin(picked_indices)]
        fill = remaining.sample(n=n - len(picked), random_state=seed + 997)
        picked = pd.concat([picked, fill], ignore_index=False)
    return picked


def copy_montages(sample: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    montage_dir = out_dir / "montages"
    montage_dir.mkdir(parents=True, exist_ok=True)
    cv_paths = []
    for _, row in sample.iterrows():
        src_text = str(row.get("audit200_montage_path", "")).strip()
        cv_id = str(row["cv_id"])
        if not src_text or src_text.lower() == "nan":
            cv_paths.append("")
            continue
        src = Path(src_text)
        if not src.exists():
            cv_paths.append("")
            continue
        dst = montage_dir / f"{cv_id}_{src.name}"
        shutil.copy2(src, dst)
        cv_paths.append(str(dst))
    sample = sample.copy()
    sample["cv_montage_path"] = cv_paths
    return sample


def write_index(blind: pd.DataFrame, out_dir: Path) -> Path:
    rows = []
    for _, row in blind.iterrows():
        img = row.get("cv_montage_path", "")
        label = f"{row['cv_id']} | {row['video_id']} | {row['path_id']} | {row['query']} | {row['query_segment']} | {row['audit_source']}"
        img_html = f'<img src="{Path(img).relative_to(out_dir)}" alt="{row["cv_id"]}" loading="lazy">' if img else "<div>No montage</div>"
        rows.append(f"<section><h3>{label}</h3>{img_html}</section>")
    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>BURST CV60 Blind Audit</title>
  <style>
    body { font-family: sans-serif; margin: 24px; color: #111; }
    section { border-top: 1px solid #ddd; padding: 16px 0; }
    img { max-width: 960px; width: 100%; height: auto; border: 1px solid #ccc; }
    h3 { font-size: 14px; font-weight: 600; }
  </style>
</head>
<body>
  <h1>BURST CV60 Blind Audit</h1>
  <p>Fill labels in burst_cv60_blind_labels_template.csv. Reference labels are stored separately and must not be used during blind relabeling.</p>
""" + "\n".join(rows) + "\n</body>\n</html>\n"
    path = out_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    return path


def build_packet(burst_dir: Path, out_dir: Path, seed: int) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = burst_dir / "burst_audit200_with_release_coverage_candidates.csv"
    labels_path = burst_dir / "burst_audit200_with_release_coverage_labels.csv"
    universe_path = burst_dir / "candidate_universe.csv"

    candidates = pd.read_csv(candidates_path)
    labels = pd.read_csv(labels_path)
    universe = pd.read_csv(universe_path, usecols=lambda c: c in {"query", "video_id", "path_id", "score", "category_id"})
    merged = candidates.merge(labels, on=["dataset", "video_id", "path_id"], how="left", suffixes=("", "_ref"))
    merged = merged.drop_duplicates(subset=["dataset", "video_id", "path_id"]).copy()
    merged["query_segment"] = merged["query"].fillna("unknown").map(assign_query_segments(universe)).fillna("tail")
    merged["label"] = merged["label"].fillna("unlabeled")
    merged["verified_positive_for_calibration_ref"] = merged["verified_positive_for_calibration_ref"].map(normalize_yes)

    selected_indices: set[int] = set()
    parts: list[pd.DataFrame] = []

    released = merged[merged["audit_source"].eq("released_unsupported")]
    released = released.sort_values(["video_id", "path_id"]).head(15)
    parts.append(released)
    selected_indices.update(released.index.tolist())

    false_pool = merged[(merged["label"].eq("actually_false")) & (~merged.index.isin(selected_indices))]
    false_rows = false_pool.sort_values(["score", "video_id", "path_id"], ascending=[False, True, True])
    parts.append(false_rows)
    selected_indices.update(false_rows.index.tolist())

    uncertain_pool = merged[(merged["label"].eq("uncertain")) & (~merged.index.isin(selected_indices))]
    uncertain_rows = stratified_sample(uncertain_pool, 18, seed=seed + 100)
    parts.append(uncertain_rows)
    selected_indices.update(uncertain_rows.index.tolist())

    current = sum(len(p) for p in parts)
    true_needed = max(0, 60 - current)
    true_pool = merged[(merged["label"].eq("actually_true")) & (~merged.index.isin(selected_indices))]
    true_rows = stratified_sample(true_pool, true_needed, seed=seed + 200)
    parts.append(true_rows)

    sample = pd.concat(parts, ignore_index=False).drop_duplicates(subset=["dataset", "video_id", "path_id"])
    if len(sample) < 60:
        fill_pool = merged.loc[~merged.index.isin(sample.index)]
        fill = stratified_sample(fill_pool, 60 - len(sample), seed=seed + 300)
        sample = pd.concat([sample, fill], ignore_index=False)
    sample = sample.sort_values(["audit_source", "label", "query_segment", "score"], ascending=[True, True, True, False]).head(60)
    sample = sample.reset_index(drop=True)
    sample.insert(0, "cv_id", [f"burst_cv60_{i:03d}" for i in range(1, len(sample) + 1)])
    sample = copy_montages(sample, out_dir)

    blind_cols = [
        "cv_id", "dataset", "video_id", "path_id", "query", "category_id", "query_segment",
        "audit_source", "score", "objectness", "semantic_margin", "temporal_stability",
        "association_score", "matched_gt_id", "matched_iou", "temporal_overlap",
        "is_unmatched", "cell_id", "frame_start", "frame_end", "audit200_montage_path",
        "cv_montage_path",
    ]
    blind = sample[[c for c in blind_cols if c in sample.columns]].copy()
    blind["second_rater_label"] = ""
    blind["second_rater_verified_positive_for_calibration"] = ""
    blind["second_rater_reason"] = ""
    blind["second_rater_confidence"] = ""
    blind["second_rater"] = ""
    blind["second_rater_notes"] = ""

    ref = sample[[
        "cv_id", "dataset", "video_id", "path_id", "query", "category_id", "query_segment",
        "audit_source", "label", "reason", "auditor", "confidence", "review_status",
        "verified_positive_for_calibration_ref", "score", "cv_montage_path",
    ]].copy()
    ref = ref.rename(columns={
        "label": "first_rater_label",
        "reason": "first_rater_reason",
        "auditor": "first_rater",
        "confidence": "first_rater_confidence",
        "review_status": "first_review_status",
        "verified_positive_for_calibration_ref": "first_verified_positive_for_calibration",
    })

    candidates_out = out_dir / "burst_cv60_candidates_blind.csv"
    template_out = out_dir / "burst_cv60_blind_labels_template.csv"
    reference_out = out_dir / "burst_cv60_reference_labels.csv"
    blind.drop(columns=[
        "second_rater_label", "second_rater_verified_positive_for_calibration",
        "second_rater_reason", "second_rater_confidence", "second_rater",
        "second_rater_notes",
    ]).to_csv(candidates_out, index=False)
    blind.to_csv(template_out, index=False)
    ref.to_csv(reference_out, index=False)
    index_path = write_index(blind, out_dir)

    counts = {
        "total": int(len(sample)),
        "by_reference_label": {str(k): int(v) for k, v in ref["first_rater_label"].value_counts().to_dict().items()},
        "by_audit_source": {str(k): int(v) for k, v in blind["audit_source"].value_counts().to_dict().items()},
        "by_query_segment": {str(k): int(v) for k, v in blind["query_segment"].value_counts().to_dict().items()},
        "verified_positive_reference": int((ref["first_verified_positive_for_calibration"] == "yes").sum()),
        "unique_queries": int(blind["query"].nunique()),
    }
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": "BURST",
        "status": "requires_independent_cross_validation_labels",
        "sample_size": int(len(sample)),
        "sampling_protocol": "include all released-unsupported audit200 paths, include all actually_false paths, stratified sample uncertain paths, fill remaining actually_true paths by query-segment strata",
        "random_seed": seed,
        "source_candidates": str(candidates_path),
        "source_labels": str(labels_path),
        "outputs": {
            "blind_candidates": str(candidates_out),
            "blind_label_template": str(template_out),
            "reference_labels": str(reference_out),
            "index_html": str(index_path),
        },
        "counts": counts,
        "hashes": {
            candidates_out.name: sha256_file(candidates_out),
            template_out.name: sha256_file(template_out),
            reference_out.name: sha256_file(reference_out),
            index_path.name: sha256_file(index_path),
        },
        "integrity_note": "Reference labels are model-assisted first-pass labels and are not independent second-rater labels.",
    }
    (out_dir / "burst_cv60_sample_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "RUN_REPORT.md").write_text(
        "# BURST CV60 Audit Cross-Validation Packet\n\n"
        f"Created: {manifest['created_utc']}\n\n"
        "Status: `requires_independent_cross_validation_labels`.\n\n"
        "This packet contains a blind relabel template and separate reference labels from the existing "
        "model-assisted BURST audit. It does not contain independent second-rater labels yet.\n\n"
        f"Counts: `{counts}`\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--burst-dir", type=Path, default=DEFAULT_BURST_DIR)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    build_packet(args.burst_dir, args.out_dir, args.seed)


if __name__ == "__main__":
    main()
