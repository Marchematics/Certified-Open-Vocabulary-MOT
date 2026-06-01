#!/usr/bin/env python3
"""Build Phase91 image-based strong-model surrogate labels for CTC audit packets.

This milestone replaces the pending manual pass operationally with a
deterministic image-based surrogate annotator over the Phase84 blinded CTC
packets.  It reads raw CTC frames and SEG masks, computes local image-template
and geometry evidence, and writes human-label-compatible CSV files.

It is deliberately scoped as model-surrogate evidence, not external human audit
evidence, expert microscopy adjudication, official CTC ground truth, or a
completed real-audit PARC-A result.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = Path("/home/waas/paper_experiments/data/CTC/training")
PHASE84 = ROOT / "outputs/milestones/ncs_phase84_real_audit_parc_a_replication"
PHASE81 = ROOT / "outputs/milestones/ncs_phase81_ctc_external_blind_audit_mini_study"
OUT = ROOT / "outputs/milestones/ncs_phase91_ctc_strong_model_annotation"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

MODEL_ID = "phase91_ctc_image_template_segmentation_surrogate_v1"
SCOPE = (
    "ctc_strong_model_annotation;"
    "image_template_segmentation_surrogate;"
    "model_surrogate_labels_only;"
    "replaces_manual_review_operationally_not_evidentially;"
    "not_external_human_audit;"
    "not_expert_microscopy_adjudication;"
    "not_CTC_ground_truth;"
    "not_completed_real_audit_positive_evidence;"
    "not_materials_or_DFT_evidence"
)

BLIND_COLUMNS = [
    "audit_item_id",
    "ctc_dataset",
    "sequence_id",
    "frame_start",
    "frame_end",
    "source_image_path",
    "source_frame_index",
    "source_bbox_x",
    "source_bbox_y",
    "source_bbox_w",
    "source_bbox_h",
    "target_image_path",
    "target_frame_index",
    "target_bbox_x",
    "target_bbox_y",
    "target_bbox_w",
    "target_bbox_h",
]
FORBIDDEN_INPUT_COLUMNS = {
    "intended_arm",
    "source_audit_id",
    "path_id",
    "candidate_rank",
    "score",
    "human_label",
    "human_verified_positive_for_calibration",
    "queue_membership",
    "queue_calibration",
    "queue_simulated_strict_release",
    "queue_raw_topK_reference",
}
PACKETS = {
    "phase84_calibration_audit_blind_template.csv": "calibration_audit",
    "phase84_release_audit_blind_template.csv": "release_audit",
    "phase84_random_same_budget_control_blind_template.csv": "random_same_budget_control",
    "phase84_raw_overlap_diagnostic_blind_template.csv": "raw_overlap_diagnostic",
    "phase84_hard_negative_or_uncertain_control_blind_template.csv": "hard_negative_or_uncertain_control",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def resolve_image_path(image_path: str) -> Path:
    return DATA_ROOT / f"{image_path}.tif"


def resolve_mask_path(row: pd.Series, prefix: str) -> Path:
    dataset = str(row["ctc_dataset"])
    seq = f"{int(row['sequence_id']):02d}"
    frame = int(row[f"{prefix}_frame_index"])
    return DATA_ROOT / dataset / f"{seq}_ERR_SEG" / f"mask{frame:03d}.tif"


def load_gray(path: Path) -> np.ndarray:
    image = np.asarray(Image.open(path), dtype=np.float32)
    if image.ndim == 3:
        image = image.mean(axis=2)
    lo, hi = np.percentile(image, [1, 99])
    if hi <= lo:
        return np.zeros_like(image, dtype=np.float32)
    image = np.clip((image - lo) / (hi - lo), 0.0, 1.0)
    return image.astype(np.float32)


def crop(image: np.ndarray, x: float, y: float, w: float, h: float, pad: int) -> np.ndarray:
    height, width = image.shape[:2]
    x0 = max(0, int(math.floor(x - pad)))
    y0 = max(0, int(math.floor(y - pad)))
    x1 = min(width, int(math.ceil(x + w + pad)))
    y1 = min(height, int(math.ceil(y + h + pad)))
    return image[y0:y1, x0:x1]


def resize_like(target: np.ndarray, reference: np.ndarray) -> np.ndarray:
    if target.shape == reference.shape:
        return target
    return cv2.resize(target, (reference.shape[1], reference.shape[0]), interpolation=cv2.INTER_LINEAR)


def normalized_corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 0.0
    b = resize_like(b, a)
    av = a.astype(np.float32).ravel()
    bv = b.astype(np.float32).ravel()
    av = av - float(av.mean())
    bv = bv - float(bv.mean())
    denom = float(np.linalg.norm(av) * np.linalg.norm(bv))
    if denom <= 1e-8:
        return 0.0
    return float(np.dot(av, bv) / denom)


def center(row: pd.Series, prefix: str) -> tuple[float, float]:
    return (
        float(row[f"{prefix}_bbox_x"]) + 0.5 * float(row[f"{prefix}_bbox_w"]),
        float(row[f"{prefix}_bbox_y"]) + 0.5 * float(row[f"{prefix}_bbox_h"]),
    )


def mask_center_positive(row: pd.Series, prefix: str) -> bool:
    path = resolve_mask_path(row, prefix)
    if not path.exists():
        return False
    mask = np.asarray(Image.open(path))
    cx, cy = center(row, prefix)
    x = min(max(int(round(cx)), 0), mask.shape[1] - 1)
    y = min(max(int(round(cy)), 0), mask.shape[0] - 1)
    return bool(mask[y, x] > 0)


def template_match_features(source: np.ndarray, target: np.ndarray, row: pd.Series) -> tuple[float, float]:
    sx, sy = center(row, "source")
    tx, ty = center(row, "target")
    w = max(float(row["source_bbox_w"]), float(row["target_bbox_w"]), 1.0)
    h = max(float(row["source_bbox_h"]), float(row["target_bbox_h"]), 1.0)
    template_pad = max(4, int(max(w, h) * 1.5))
    search_pad = max(24, int(max(w, h) * 8.0))

    tmpl = crop(source, float(row["source_bbox_x"]), float(row["source_bbox_y"]), w, h, template_pad)
    search = crop(target, tx - 0.5 * w, ty - 0.5 * h, w, h, search_pad)
    if tmpl.size == 0 or search.size == 0 or search.shape[0] < tmpl.shape[0] or search.shape[1] < tmpl.shape[1]:
        return 0.0, float("inf")
    result = cv2.matchTemplate(search, tmpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    pred_x = tx - 0.5 * w - search_pad + max_loc[0] + 0.5 * tmpl.shape[1]
    pred_y = ty - 0.5 * h - search_pad + max_loc[1] + 0.5 * tmpl.shape[0]
    pred_dist = math.hypot(pred_x - tx, pred_y - ty)
    return float(max_val if np.isfinite(max_val) else 0.0), float(pred_dist)


def label_row(row: pd.Series) -> dict[str, object]:
    source_path = resolve_image_path(str(row["source_image_path"]))
    target_path = resolve_image_path(str(row["target_image_path"]))
    image_pair_available = source_path.exists() and target_path.exists()

    sx, sy = center(row, "source")
    tx, ty = center(row, "target")
    dx = tx - sx
    dy = ty - sy
    distance = math.hypot(dx, dy)
    source_diag = math.hypot(float(row["source_bbox_w"]), float(row["source_bbox_h"]))
    target_diag = math.hypot(float(row["target_bbox_w"]), float(row["target_bbox_h"]))
    scale = max((source_diag + target_diag) / 2.0, 1.0)
    normalized_distance = distance / scale
    source_area = max(float(row["source_bbox_w"]) * float(row["source_bbox_h"]), 1.0)
    target_area = max(float(row["target_bbox_w"]) * float(row["target_bbox_h"]), 1.0)
    area_ratio = min(source_area, target_area) / max(source_area, target_area)
    frame_gap = int(row["target_frame_index"]) - int(row["source_frame_index"])

    crop_ncc = 0.0
    template_best_ncc = 0.0
    template_pred_target_distance_px = float("inf")
    source_center_segmented = False
    target_center_segmented = False
    if image_pair_available:
        source = load_gray(source_path)
        target = load_gray(target_path)
        pad = max(8, int(max(float(row["source_bbox_w"]), float(row["source_bbox_h"]), 1.0) * 4))
        source_crop = crop(source, float(row["source_bbox_x"]), float(row["source_bbox_y"]), float(row["source_bbox_w"]), float(row["source_bbox_h"]), pad)
        target_crop = crop(target, float(row["target_bbox_x"]), float(row["target_bbox_y"]), float(row["target_bbox_w"]), float(row["target_bbox_h"]), pad)
        crop_ncc = normalized_corr(source_crop, target_crop)
        template_best_ncc, template_pred_target_distance_px = template_match_features(source, target, row)
        source_center_segmented = mask_center_positive(row, "source")
        target_center_segmented = mask_center_positive(row, "target")

    geometry_score = math.exp(-min(normalized_distance, 10.0))
    crop_score = max(0.0, min((crop_ncc + 1.0) / 2.0, 1.0))
    template_score = max(0.0, min((template_best_ncc + 1.0) / 2.0, 1.0))
    template_location_score = math.exp(-min(template_pred_target_distance_px / scale, 10.0)) if np.isfinite(template_pred_target_distance_px) else 0.0
    segmentation_score = 1.0 if source_center_segmented and target_center_segmented else 0.0
    frame_score = 1.0 if frame_gap == 1 else 0.0
    support_score = (
        0.22 * geometry_score
        + 0.24 * crop_score
        + 0.22 * template_score
        + 0.17 * template_location_score
        + 0.10 * area_ratio
        + 0.05 * segmentation_score
    ) * frame_score

    if not image_pair_available:
        label = "uncertain"
        confidence = "low"
        reason = "raw CTC frame pair unavailable"
    elif support_score >= 0.74 and normalized_distance <= 2.5:
        label = "same_cell_supported"
        confidence = "high" if support_score >= 0.84 else "medium"
        reason = "image-template, local-crop and geometry evidence support adjacent-frame same-cell link"
    elif support_score <= 0.42 or normalized_distance > 6.0:
        label = "unsupported"
        confidence = "high" if support_score <= 0.25 else "medium"
        reason = "image-template or geometry evidence does not support the proposed adjacent-frame link"
    else:
        label = "uncertain"
        confidence = "medium"
        reason = "mixed image-template and geometry evidence; route to human adjudication if used evidentially"

    return {
        "audit_item_id": row["audit_item_id"],
        "packet": row["packet"],
        "strong_model_id": MODEL_ID,
        "strong_model_label": label,
        "strong_model_confidence": confidence,
        "strong_model_support_score": round(float(support_score), 6),
        "model_reason": reason,
        "image_pair_available": image_pair_available,
        "source_image_sha256": sha256_file(source_path) if source_path.exists() else "",
        "target_image_sha256": sha256_file(target_path) if target_path.exists() else "",
        "center_distance_px": round(distance, 6),
        "normalized_distance": round(normalized_distance, 6),
        "bbox_area_ratio": round(area_ratio, 6),
        "crop_ncc": round(float(crop_ncc), 6),
        "template_best_ncc": round(float(template_best_ncc), 6),
        "template_pred_target_distance_px": round(float(template_pred_target_distance_px), 6) if np.isfinite(template_pred_target_distance_px) else "",
        "source_center_segmented": source_center_segmented,
        "target_center_segmented": target_center_segmented,
        "frame_gap": frame_gap,
        "evidence_scope": SCOPE,
    }


def load_phase84_blind_packets() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for filename, packet in PACKETS.items():
        path = PHASE84 / filename
        if not path.exists():
            raise FileNotFoundError(f"missing Phase84 packet: {rel(path)}")
        table = pd.read_csv(path)
        leaks = sorted(FORBIDDEN_INPUT_COLUMNS.intersection(table.columns))
        if leaks:
            raise ValueError(f"strong-model input contains forbidden columns in {filename}: {leaks}")
        missing = sorted(set(BLIND_COLUMNS).difference(table.columns))
        if missing:
            raise ValueError(f"strong-model input missing required columns in {filename}: {missing}")
        table = table[BLIND_COLUMNS].copy()
        table["packet"] = packet
        frames.append(table)
    return pd.concat(frames, ignore_index=True)


def write_outputs(blind: pd.DataFrame, labels: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    labels.to_csv(OUT / "table_phase91_ctc_strong_model_annotations.csv", index=False)

    replacement = blind[BLIND_COLUMNS + ["packet"]].merge(
        labels[
            [
                "audit_item_id",
                "strong_model_label",
                "strong_model_confidence",
                "strong_model_support_score",
                "model_reason",
                "strong_model_id",
            ]
        ],
        on="audit_item_id",
        how="left",
    )
    replacement["auditor_id"] = MODEL_ID
    replacement["human_label"] = replacement["strong_model_label"]
    replacement["human_confidence"] = replacement["strong_model_confidence"]
    replacement["human_notes"] = (
        "model-surrogate replacement label; not external human evidence; "
        + replacement["model_reason"].astype(str)
    )
    replacement["human_accepts_ai_label"] = "model_surrogate_not_human"
    replacement["evidence_scope"] = SCOPE
    replacement.to_csv(OUT / "phase91_model_surrogate_human_label_replacement.csv", index=False)

    by_packet = (
        labels.groupby(["packet", "strong_model_label", "strong_model_confidence"], dropna=False)
        .agg(
            rows=("audit_item_id", "count"),
            mean_support_score=("strong_model_support_score", "mean"),
            image_pairs_available=("image_pair_available", "sum"),
        )
        .reset_index()
    )
    by_packet["evidence_scope"] = SCOPE
    by_packet.to_csv(OUT / "table_phase91_strong_model_by_packet_summary.csv", index=False)

    registry = pd.read_csv(PHASE81 / "table_ctc_external_blind_audit_packet_registry.csv")
    diagnostic = registry[["audit_item_id", "intended_arm"]].merge(
        labels[["audit_item_id", "strong_model_label", "strong_model_support_score"]],
        on="audit_item_id",
        how="left",
    )
    by_arm = (
        diagnostic.groupby(["intended_arm", "strong_model_label"], dropna=False)
        .agg(rows=("audit_item_id", "count"), mean_support_score=("strong_model_support_score", "mean"))
        .reset_index()
    )
    by_arm["diagnostic_scope"] = "hidden_arm_diagnostic_after_annotation_not_used_as_model_input"
    by_arm["evidence_scope"] = SCOPE
    by_arm.to_csv(OUT / "table_phase91_strong_model_by_hidden_arm_diagnostic.csv", index=False)

    input_audit = pd.DataFrame(
        [
            {
                "check": "input_templates_have_no_arm_score_rank_prior_label_or_gt_columns",
                "passes": True,
                "strong_model_id": MODEL_ID,
                "evidence_scope": SCOPE,
            },
            {
                "check": "raw_ctc_images_available_for_all_rows",
                "passes": bool(labels["image_pair_available"].all()),
                "strong_model_id": MODEL_ID,
                "evidence_scope": SCOPE,
            },
            {
                "check": "model_surrogate_not_human_evidence",
                "passes": True,
                "strong_model_id": MODEL_ID,
                "evidence_scope": SCOPE,
            },
        ]
    )
    input_audit.to_csv(OUT / "table_phase91_input_audit.csv", index=False)

    claim_gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase91_ctc_strong_model_annotation",
                "status": "strong_model_surrogate_annotations_completed_not_human_evidence",
                "positive_evidence": "no",
                "packet_rows": len(labels),
                "image_pair_available_rows": int(labels["image_pair_available"].sum()),
                "strong_model_id": MODEL_ID,
                "allowed_current_claim": "A deterministic image-based strong-model surrogate annotated the frozen Phase84 CTC audit packets and produced human-label-compatible replacement CSVs.",
                "forbidden_current_claim": "Do not claim external human audit success, expert microscopy adjudication, official CTC ground truth, completed real-audit PARC-A replication, or materials/DFT evidence from Phase91 labels.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    claim_gate.to_csv(OUT / "table_phase91_claim_gate.csv", index=False)

    figure = pd.DataFrame(
        [
            {
                "panel": "A",
                "quantity": "annotated_rows",
                "value": len(labels),
                "label": "model-surrogate annotated Phase84 rows",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "B",
                "quantity": "same_cell_supported_rows",
                "value": int(labels["strong_model_label"].eq("same_cell_supported").sum()),
                "label": "model-surrogate same-cell-supported labels",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "C",
                "quantity": "human_evidence_rows",
                "value": 0,
                "label": "external human evidence not produced by this milestone",
                "evidence_scope": SCOPE,
            },
        ]
    )
    figure.to_csv(OUT / "figure_phase91_strong_model_annotation_inputs.csv", index=False)


def write_docs(labels: pd.DataFrame) -> None:
    readme = f"""# Phase91 CTC Strong-Model Surrogate Annotation

Status: `strong_model_surrogate_annotations_completed_not_human_evidence`.

Phase91 annotates the frozen Phase84 CTC blind-audit packets with a local
image-based surrogate model.  It reads adjacent CTC frames and SEG masks,
computes crop/template/geometry evidence, and emits human-label-compatible
CSV files that can operationally replace manual labels for downstream dry
runs.

Scope boundary:

- allowed: strong-model surrogate annotations and replacement-label CSVs;
- forbidden: external human audit success, expert microscopy adjudication,
  official CTC ground truth, completed real-audit PARC-A replication, or
  materials/DFT evidence;
- shorthand boundary: not external human evidence.

All `{len(labels)}` packet rows have image-pair availability status recorded.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = f"""# Phase91 Protocol: CTC Strong-Model Surrogate Annotation

Model id: `{MODEL_ID}`.

Inputs:

- Phase84 blinded packet templates;
- local CTC raw training frames under the configured data root;
- CTC `*_ERR_SEG` masks where available.

Forbidden inputs:

- intended arm;
- PARC status;
- score/rank;
- prior human labels;
- official GT labels.

Algorithm:

1. Resolve source and target adjacent frames.
2. Extract local bbox-context crops.
3. Compute crop normalized correlation.
4. Match the source crop template in the target-frame neighborhood.
5. Combine image-template, geometry, bbox-area, frame-gap and segmentation
   center evidence into a deterministic support score.
6. Emit `same_cell_supported`, `unsupported` or `uncertain`.

The output can replace manual labels operationally for dry runs, but it is not
external human evidence.
"""
    (OUT / "PHASE91_CTC_STRONG_MODEL_ANNOTATION_PROTOCOL.md").write_text(protocol, encoding="utf-8")


def write_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def update_artifact_index() -> None:
    row = {
        "milestone": "ncs_phase91_ctc_strong_model_annotation",
        "path": "outputs/milestones/ncs_phase91_ctc_strong_model_annotation/",
        "evidence_state": "strong_model_surrogate_annotations_completed_not_human_evidence",
        "manifest": "outputs/milestones/ncs_phase91_ctc_strong_model_annotation/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase91_ctc_strong_model_annotation",
        "notes": "CTC image-based model-surrogate replacement labels; not external human evidence.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row]).reindex(columns=df.columns)], ignore_index=True).to_csv(ARTIFACT_INDEX, index=False)


def update_ledger() -> None:
    row = {
        "claim_id": "CTC-PHASE91-STRONG-MODEL-ANNOTATION-001",
        "claim_text": "Phase91 produces deterministic image-based strong-model surrogate annotations for the frozen CTC Phase84 packets.",
        "evidence_type": "model_surrogate_annotation_artifact",
        "positive_evidence": "no",
        "scope": "model_surrogate_labels_only;not_human_audit",
        "artifact_path": "outputs/milestones/ncs_phase91_ctc_strong_model_annotation/table_phase91_claim_gate.csv",
        "hash": sha256_file(OUT / "table_phase91_claim_gate.csv"),
        "validation_command": "make reproduce-ncs-phase91-ctc-strong-model-annotation",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_external_human_audit_success_expert_adjudication_or_ground_truth_from_model_surrogate_labels",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """\n## Phase91 CTC Strong-Model Surrogate Annotation\n\nStatus: `strong_model_surrogate_annotations_completed_not_human_evidence`.\n\nPhase91 uses a deterministic image-based surrogate annotator over the frozen\nPhase84 CTC blind-audit packets and writes human-label-compatible replacement\nCSVs. It can replace manual labeling operationally for dry runs, but it is not external human audit evidence and not external human evidence. It is also not\nexpert microscopy adjudication, official CTC ground truth, completed real-audit\nPARC-A replication, or materials/DFT evidence.\n"""
    marker = "## Phase91 CTC Strong-Model Surrogate Annotation"
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    if marker in text:
        before = text.split(marker)[0].rstrip()
        after = text.split(marker, 1)[1]
        next_idx = after.find("\n## ")
        text = before + "\n" + section + (after[next_idx:] if next_idx >= 0 else "")
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    blind = load_phase84_blind_packets()
    labels = pd.DataFrame([label_row(row) for _, row in blind.iterrows()])
    write_outputs(blind, labels)
    write_docs(labels)
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase91-ctc] wrote {rel(OUT)}")
    print("[phase91-ctc] status=strong_model_surrogate_annotations_completed_not_human_evidence")


if __name__ == "__main__":
    main()
