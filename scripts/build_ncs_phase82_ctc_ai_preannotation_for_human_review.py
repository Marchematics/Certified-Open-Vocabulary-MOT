#!/usr/bin/env python3
"""Build Phase82 AI preannotations for the Phase81 CTC blind audit packet.

The AI annotator is a deterministic geometry-only assistant over the blinded
Phase81 review sheet.  It does not use PARC arm membership, score/rank,
official GT, previous human labels, or source audit labels.  The generated
labels are review aids only; human adjudication remains the evidence source.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE81 = ROOT / "outputs/milestones/ncs_phase81_ctc_external_blind_audit_mini_study"
SOURCE_LABELS = ROOT / "outputs/milestones/ctc_strict_human_audit/ctc_strict_audit_human_confirmed_labels.csv"
OUT = ROOT / "outputs/milestones/ncs_phase82_ctc_ai_preannotation_for_human_review"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "ctc_ai_preannotation_for_human_review;"
    "ai_assistive_labels_only;"
    "geometry_only_no_arm_score_rank_or_prior_label_inputs;"
    "human_review_pending;"
    "not_completed_positive_evidence;"
    "not_CTC_ground_truth;"
    "not_materials_or_DFT_evidence"
)

AI_MODEL_ID = "phase82_geometry_only_rule_v1"
ALLOWED_AI_INPUT_COLUMNS = (
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
)
FORBIDDEN_AI_INPUT_COLUMNS = {
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def center(row: pd.Series, prefix: str) -> tuple[float, float]:
    return (
        float(row[f"{prefix}_bbox_x"]) + 0.5 * float(row[f"{prefix}_bbox_w"]),
        float(row[f"{prefix}_bbox_y"]) + 0.5 * float(row[f"{prefix}_bbox_h"]),
    )


def ai_label_row(row: pd.Series) -> dict[str, object]:
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

    if frame_gap != 1:
        ai_label = "uncertain"
        confidence = "low"
        score = 0.40
        reason = "non-adjacent frame gap; geometry-only assistant declines support"
    elif normalized_distance <= 0.55 and area_ratio >= 0.70:
        ai_label = "same_cell_supported"
        confidence = "high"
        score = 0.95
        reason = "near-zero adjacent-frame displacement with similar bbox size"
    elif normalized_distance <= 1.25 and area_ratio >= 0.55:
        ai_label = "same_cell_supported"
        confidence = "medium"
        score = 0.78
        reason = "adjacent-frame displacement is within about one cell diameter"
    elif normalized_distance <= 2.50 and area_ratio >= 0.35:
        ai_label = "uncertain"
        confidence = "medium"
        score = 0.50
        reason = "geometry is plausible but displacement or size change needs human review"
    else:
        ai_label = "unsupported"
        confidence = "medium"
        score = 0.20
        reason = "large normalized displacement or substantial bbox-size change"

    return {
        "audit_item_id": row["audit_item_id"],
        "ai_model_id": AI_MODEL_ID,
        "ai_label": ai_label,
        "ai_confidence": confidence,
        "ai_support_score": score,
        "ai_reason": reason,
        "center_dx": dx,
        "center_dy": dy,
        "center_distance_px": distance,
        "normalized_distance": normalized_distance,
        "bbox_area_ratio": area_ratio,
        "frame_gap": frame_gap,
        "evidence_scope": SCOPE,
    }


def load_blind_template() -> pd.DataFrame:
    template = pd.read_csv(PHASE81 / "external_blind_auditor_A_template.csv")
    input_cols = set(template.columns)
    leaks = sorted(FORBIDDEN_AI_INPUT_COLUMNS.intersection(input_cols))
    if leaks:
        raise ValueError(f"AI input template contains forbidden columns: {leaks}")
    missing = sorted(set(ALLOWED_AI_INPUT_COLUMNS).difference(input_cols))
    if missing:
        raise ValueError(f"AI input template missing required columns: {missing}")
    return template[list(ALLOWED_AI_INPUT_COLUMNS)].copy()


def write_outputs(blind: pd.DataFrame, pre: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pre.to_csv(OUT / "table_ctc_ai_preannotations.csv", index=False)

    review = blind.merge(
        pre[
            [
                "audit_item_id",
                "ai_label",
                "ai_confidence",
                "ai_support_score",
                "ai_reason",
            ]
        ],
        on="audit_item_id",
        how="left",
    )
    review["human_label"] = ""
    review["human_confidence"] = ""
    review["human_notes"] = ""
    review["human_accepts_ai_label"] = ""
    review.to_csv(OUT / "ai_assisted_human_review_template.csv", index=False)

    # Keep a clean non-assisted template beside the AI-assisted sheet for a
    # bias-control review option.
    blind_template = pd.read_csv(PHASE81 / "external_blind_auditor_A_template.csv")
    blind_template.to_csv(OUT / "human_review_without_ai_template.csv", index=False)

    summary = (
        pre.groupby(["ai_label", "ai_confidence"], dropna=False)
        .agg(rows=("audit_item_id", "count"), mean_support_score=("ai_support_score", "mean"))
        .reset_index()
    )
    summary["evidence_scope"] = SCOPE
    summary.to_csv(OUT / "table_ctc_ai_preannotation_summary.csv", index=False)

    registry = pd.read_csv(PHASE81 / "table_ctc_external_blind_audit_packet_registry.csv")
    source = pd.read_csv(SOURCE_LABELS)[["audit_id", "human_label"]].rename(columns={"audit_id": "source_audit_id"})
    diagnostic = registry[["audit_item_id", "intended_arm", "source_audit_id"]].merge(source, on="source_audit_id", how="left")
    diagnostic = diagnostic.merge(pre[["audit_item_id", "ai_label"]], on="audit_item_id", how="left")
    diagnostic["ai_matches_existing_publication_label"] = (
        diagnostic["ai_label"].eq("same_cell_supported") & diagnostic["human_label"].eq("same_cell_link")
    ) | (
        diagnostic["ai_label"].eq("unsupported") & diagnostic["human_label"].eq("not_same_cell_link")
    )
    diagnostic["diagnostic_scope"] = (
        "retrospective_internal_sanity_against_existing_phase78_publication_labels;"
        "not_used_for_AI_generation;"
        "not_a_new_human_review_result"
    )
    diagnostic.to_csv(OUT / "table_ctc_ai_preannotation_existing_label_diagnostic.csv", index=False)

    by_arm = (
        diagnostic.groupby(["intended_arm", "ai_label"], dropna=False)
        .agg(rows=("audit_item_id", "count"))
        .reset_index()
    )
    by_arm["evidence_scope"] = SCOPE
    by_arm.to_csv(OUT / "table_ctc_ai_preannotation_by_hidden_arm_diagnostic.csv", index=False)

    input_audit = pd.DataFrame(
        [
            {
                "check": "ai_input_has_no_arm_score_rank_prior_label_or_GT_columns",
                "passes": True,
                "forbidden_columns_present": "",
                "ai_model_id": AI_MODEL_ID,
                "evidence_scope": SCOPE,
            },
            {
                "check": "human_review_pending",
                "passes": False,
                "forbidden_columns_present": "",
                "ai_model_id": AI_MODEL_ID,
                "evidence_scope": SCOPE,
            },
            {
                "check": "ai_labels_not_positive_evidence",
                "passes": True,
                "forbidden_columns_present": "",
                "ai_model_id": AI_MODEL_ID,
                "evidence_scope": SCOPE,
            },
        ]
    )
    input_audit.to_csv(OUT / "table_ctc_ai_preannotation_input_audit.csv", index=False)

    claim_gate = pd.DataFrame(
        [
            {
                "claim_gate": "ctc_ai_preannotation_before_human_review",
                "status": "ai_preannotations_completed_human_review_pending",
                "positive_evidence": "no",
                "packet_rows": len(pre),
                "ai_model_id": AI_MODEL_ID,
                "allowed_current_claim": "AI preannotations were generated for the frozen CTC blind-audit packet to accelerate human review.",
                "forbidden_current_claim": "Do not claim completed human review, external audit success, expert microscopy adjudication, or CTC ground truth from AI labels.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    claim_gate.to_csv(OUT / "table_ctc_ai_preannotation_claim_gate.csv", index=False)

    figure = pd.DataFrame(
        [
            {
                "panel": "A",
                "quantity": "ai_preannotated_rows",
                "value": len(pre),
                "label": "AI-preannotated Phase81 packet rows",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "B",
                "quantity": "same_cell_supported_ai_rows",
                "value": int(pre["ai_label"].eq("same_cell_supported").sum()),
                "label": "AI-supported rows for human confirmation",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "C",
                "quantity": "human_review_completed_rows",
                "value": 0,
                "label": "human review pending",
                "evidence_scope": SCOPE,
            },
        ]
    )
    figure.to_csv(OUT / "figure_ctc_ai_preannotation_inputs.csv", index=False)


def write_docs() -> None:
    readme = f"""# Phase82 CTC AI Preannotation for Human Review

Status: `ai_preannotations_completed_human_review_pending`.

This milestone runs a deterministic geometry-only AI assistant over the Phase81
blind audit packet.  It is designed to speed human review, not to create
evidence.  The generated labels are review aids only.

Input discipline:

- uses only the blinded Phase81 auditor template;
- does not use arm membership, PARC status, score/rank, previous human labels,
  official GT labels or source audit labels;
- retrospective comparison to existing Phase78 publication labels is written
  only as an internal sanity diagnostic.

Paper boundary:

- allowed: "AI preannotations were generated before human audit";
- forbidden: "AI labels complete the audit", "expert microscopy adjudication",
  "new CTC ground truth", or "PARC-A real audit success".

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    rubric = """# AI-Assisted Human Review Instructions

Human labels must be entered independently from the AI suggestion.

Allowed human labels:

- `same_cell_supported`: the two adjacent-frame boxes plausibly identify the
  same cell/link and may be used as one-sided positive support.
- `unsupported`: the link is visibly implausible or points to a different cell.
- `uncertain`: the image evidence is insufficient, ambiguous, or needs
  adjudication.

Only `same_cell_supported` can become one-sided support.  `unsupported` and
`uncertain` labels are never trusted negatives for PARC calibration.
"""
    (OUT / "AI_ASSISTED_HUMAN_REVIEW_RUBRIC.md").write_text(rubric, encoding="utf-8")


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


def upsert_artifact_index() -> None:
    row = {
        "milestone": "ncs_phase82_ctc_ai_preannotation_for_human_review",
        "path": rel(OUT) + "/",
        "evidence_state": "ai_preannotations_completed_human_review_pending_not_positive_evidence",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase82_ctc_ai_preannotation_for_human_review",
    }
    index = pd.read_csv(ARTIFACT_INDEX)
    index = index[index["milestone"] != row["milestone"]]
    for col in row:
        if col not in index.columns:
            index[col] = ""
    index = pd.concat([index[index.columns], pd.DataFrame([row])[index.columns]], ignore_index=True)
    index.to_csv(ARTIFACT_INDEX, index=False)


def upsert_evidence_ledger() -> None:
    row = {
        "claim_id": "CTC-AI-PREANNOTATION-001",
        "claim_text": "AI preannotations were generated for the frozen CTC external blind audit packet before human review.",
        "evidence_type": "ai_preannotation_review_aid",
        "positive_evidence": "no",
        "scope": "human_review_pending;not_completed_audit",
        "artifact_path": rel(OUT / "table_ctc_ai_preannotation_claim_gate.csv"),
        "hash": sha256_file(OUT / "table_ctc_ai_preannotation_claim_gate.csv"),
        "validation_command": "make reproduce-ncs-phase82-ctc-ai-preannotation-for-human-review",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_completed_human_review_external_audit_success_expert_adjudication_or_ground_truth_from_AI_labels",
    }
    ledger = pd.read_csv(LEDGER)
    ledger = ledger[ledger["claim_id"] != row["claim_id"]]
    ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
    ledger.to_csv(LEDGER, index=False)


def upsert_claim_table() -> None:
    section = """\n## Phase82 CTC AI Preannotation for Human Review\n\nStatus: `ai_preannotations_completed_human_review_pending`.\n\nPhase82 generates geometry-only AI preannotations for the frozen Phase81 CTC\nblind-audit packet and writes an AI-assisted human review sheet.  The AI uses\nonly blinded geometry/frame metadata and does not use arm membership, score,\nrank, prior human labels or official GT.  These labels are review aids only:\nPhase82 is not completed human evidence, external audit success, expert\nmicroscopy adjudication or new CTC ground truth.\n"""
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    marker = "## Phase82 CTC AI Preannotation for Human Review"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    blind = load_blind_template()
    pre = pd.DataFrame([ai_label_row(row) for _, row in blind.iterrows()])
    write_outputs(blind, pre)
    write_docs()
    write_manifest(OUT)
    upsert_artifact_index()
    upsert_evidence_ledger()
    upsert_claim_table()
    write_root_manifest()
    print(f"[phase82] wrote {OUT.relative_to(ROOT)}")
    print("[phase82] status=ai_preannotations_completed_human_review_pending")


if __name__ == "__main__":
    main()
