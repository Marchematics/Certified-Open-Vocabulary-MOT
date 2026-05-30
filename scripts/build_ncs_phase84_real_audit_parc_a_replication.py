#!/usr/bin/env python3
"""Freeze Phase84 real-audit PARC-A replication package.

Phase84 is stronger than a release-set audit: it is designed to test whether
external human one-sided calibration support can drive PARC-A, then evaluate
the resulting release with an independent release-audit packet.

This script does not ingest returned labels and does not produce positive
evidence.  It freezes templates, schema and GO/NO-GO gates before external
labels are available.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE81 = ROOT / "outputs/milestones/ncs_phase81_ctc_external_blind_audit_mini_study"
PHASE82 = ROOT / "outputs/milestones/ncs_phase82_ctc_ai_preannotation_for_human_review"
OUT = ROOT / "outputs/milestones/ncs_phase84_real_audit_parc_a_replication"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "phase84_real_audit_parc_a_replication_protocol;"
    "external_labels_pending;"
    "workflow_replication_packet_frozen;"
    "not_completed_positive_evidence;"
    "not_new_CTC_ground_truth;"
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

ARM_TO_PACKET = {
    "calibration_one_sided_support_pool": "calibration_audit",
    "parc_release_core": "release_audit",
    "random_blind_control_from_available_reviewed_rows": "random_same_budget_control",
    "raw_topK_reference_overlap": "raw_overlap_diagnostic",
    "hard_negative_or_uncertain_control": "hard_negative_or_uncertain_control",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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


def blind_template(rows: pd.DataFrame) -> pd.DataFrame:
    out = rows[BLIND_COLUMNS].copy()
    out["auditor_label"] = ""
    out["auditor_confidence"] = ""
    out["auditor_notes"] = ""
    return out


def ai_assisted_template(rows: pd.DataFrame, ai: pd.DataFrame) -> pd.DataFrame:
    out = rows[BLIND_COLUMNS].merge(
        ai[["audit_item_id", "ai_label", "ai_confidence", "ai_support_score", "ai_reason"]],
        on="audit_item_id",
        how="left",
    )
    out["human_label"] = ""
    out["human_confidence"] = ""
    out["human_notes"] = ""
    out["human_accepts_ai_label"] = ""
    return out


def write_packet_templates(registry: pd.DataFrame, ai: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for arm, packet in ARM_TO_PACKET.items():
        subset = registry[registry["intended_arm"].eq(arm)].copy()
        rows.append(
            {
                "packet": packet,
                "source_arm": arm,
                "rows": len(subset),
                "primary_role": "yes" if packet in {"calibration_audit", "release_audit", "random_same_budget_control"} else "no",
                "blinded_template": f"phase84_{packet}_blind_template.csv",
                "ai_assisted_template": f"phase84_{packet}_ai_assisted_template.csv",
                "evidence_scope": SCOPE,
            }
        )
        blind_template(subset).to_csv(OUT / f"phase84_{packet}_blind_template.csv", index=False)
        ai_assisted_template(subset, ai).to_csv(OUT / f"phase84_{packet}_ai_assisted_template.csv", index=False)
    plan = pd.DataFrame(rows)
    plan.to_csv(OUT / "table_phase84_audit_packet_plan.csv", index=False)
    return plan


def write_protocol(plan: pd.DataFrame) -> None:
    protocol = f"""# Phase84 Real-Audit PARC-A Replication Protocol

Status: `workflow_replication_packet_frozen_pending_external_labels`.

Objective:

Test whether external human one-sided calibration support can reproduce the
PARC-A CTC release workflow, rather than merely auditing an already released
set or replaying masked official labels.

Frozen design:

- candidate source: Phase81 frozen CTC external blind audit packet;
- risk target: `alpha = 0.10`;
- headline budget: `K = 100`;
- calibration support rule: only consensus `same_cell_supported` human labels
  may enter the verified-positive set;
- `unsupported` and `uncertain` labels are never trusted negatives;
- primary human-review route: blind no-AI templates;
- optional operational route: AI-assisted templates from Phase82, disclosed as
  AI-assisted and not used as independent evidence without human confirmation;
- raw-only comparator is unavailable in the tracked Phase81 source rows, so
  Phase84 uses random same-budget control and raw-overlap/boundary diagnostics.

Primary GO gate after labels return:

```text
human-calibration PARC-A produces non-empty release at K=100
release size >= 80
conservative release-audit FTR <= 0.05
Clopper-Pearson 95% upper bound <= 0.10
two-auditor agreement kappa >= 0.70
random same-budget arm remains empty or fails evidence threshold
no arm-label leakage
```

Current packet rows:

{plan.to_markdown(index=False)}

Claim boundary:

- allowed now: Phase84 freezes the external real-audit PARC-A replication
  packet and protocol;
- forbidden now: real-audit PARC-A success, completed external adjudication,
  new CTC ground truth, raw-only superiority, materials evidence, or DFT
  evidence.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "PHASE84_REAL_AUDIT_PARC_A_REPLICATION_PROTOCOL.md").write_text(protocol, encoding="utf-8")


def write_schema_and_gates(plan: pd.DataFrame) -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Phase84 returned human label schema",
        "type": "object",
        "required": ["audit_item_id", "auditor_id", "human_label", "human_confidence"],
        "properties": {
            "audit_item_id": {"type": "string", "pattern": "^CTC-PHASE81-[0-9]{4}$"},
            "auditor_id": {"type": "string"},
            "human_label": {
                "type": "string",
                "enum": ["same_cell_supported", "unsupported", "uncertain"],
            },
            "human_confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "human_notes": {"type": "string"},
            "human_accepts_ai_label": {"type": ["string", "boolean", "null"]},
        },
        "additionalProperties": False,
    }
    (OUT / "returned_human_label_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")

    gates = pd.DataFrame(
        [
            {
                "gate": "external_labels_returned",
                "threshold": "two auditors for calibration and release packets",
                "current_status": "pending",
                "required_for_positive_claim": True,
                "evidence_scope": SCOPE,
            },
            {
                "gate": "human_calibration_parc_a_release",
                "threshold": "K=100 nonempty release size >=80",
                "current_status": "not_run_pending_labels",
                "required_for_positive_claim": True,
                "evidence_scope": SCOPE,
            },
            {
                "gate": "release_audit_conservative_FTR",
                "threshold": "point estimate <=0.05 and Clopper-Pearson 95% upper <=0.10",
                "current_status": "not_run_pending_labels",
                "required_for_positive_claim": True,
                "evidence_scope": SCOPE,
            },
            {
                "gate": "auditor_agreement",
                "threshold": "kappa >=0.70 or conservative adjudication documented",
                "current_status": "pending",
                "required_for_positive_claim": True,
                "evidence_scope": SCOPE,
            },
            {
                "gate": "random_same_budget_control",
                "threshold": "same-budget random control remains empty or fails evidence threshold",
                "current_status": "pending",
                "required_for_positive_claim": True,
                "evidence_scope": SCOPE,
            },
        ]
    )
    gates.to_csv(OUT / "table_phase84_go_no_go_gates.csv", index=False)

    claim_gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase84_real_audit_parc_a_replication",
                "status": "workflow_replication_packet_frozen_pending_external_labels",
                "positive_evidence": "no",
                "packet_rows": int(plan["rows"].sum()),
                "primary_packet_rows": int(plan.loc[plan["primary_role"].eq("yes"), "rows"].sum()),
                "allowed_current_claim": "Phase84 freezes a real-audit PARC-A workflow replication packet before returned external labels.",
                "forbidden_current_claim": "Do not claim real-audit PARC-A success, completed external adjudication, new CTC ground truth, raw-only superiority, materials evidence, or DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    claim_gate.to_csv(OUT / "table_phase84_claim_gate.csv", index=False)

    execution = pd.DataFrame(
        [
            {
                "step": 1,
                "action": "external auditors complete calibration blind templates",
                "input": "phase84_calibration_audit_blind_template.csv",
                "output": "returned calibration labels",
                "status": "pending",
                "evidence_scope": SCOPE,
            },
            {
                "step": 2,
                "action": "consensus same-cell labels become one-sided positives",
                "input": "returned calibration labels",
                "output": "human verified-positive set",
                "status": "pending",
                "evidence_scope": SCOPE,
            },
            {
                "step": 3,
                "action": "rerun PARC-A K=100 using human calibration positives",
                "input": "human verified-positive set",
                "output": "human-calibration PARC-A release/refusal",
                "status": "pending",
                "evidence_scope": SCOPE,
            },
            {
                "step": 4,
                "action": "external auditors complete release audit",
                "input": "phase84_release_audit_blind_template.csv",
                "output": "release-audit FTR and confidence bound",
                "status": "pending",
                "evidence_scope": SCOPE,
            },
            {
                "step": 5,
                "action": "evaluate random same-budget control",
                "input": "phase84_random_same_budget_control_blind_template.csv",
                "output": "control transition status",
                "status": "pending",
                "evidence_scope": SCOPE,
            },
        ]
    )
    execution.to_csv(OUT / "table_phase84_execution_plan.csv", index=False)


def write_docs(plan: pd.DataFrame) -> None:
    readme = f"""# Phase84 Real-Audit PARC-A Replication

Status: `workflow_replication_packet_frozen_pending_external_labels`.

Phase84 freezes the packet needed to test whether real external one-sided
human calibration support can reproduce the PARC-A CTC active-verification
result.  It is not a completed audit result.

Primary packets:

- calibration audit rows: {int(plan.loc[plan['packet'].eq('calibration_audit'), 'rows'].iloc[0])}
- release audit rows: {int(plan.loc[plan['packet'].eq('release_audit'), 'rows'].iloc[0])}
- random same-budget control rows: {int(plan.loc[plan['packet'].eq('random_same_budget_control'), 'rows'].iloc[0])}

Important blocker:

The tracked Phase81 source rows do not contain a true raw-only top-K arm.
Phase84 therefore uses random same-budget control as the primary workflow
control and keeps raw-overlap rows as diagnostics only.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    rubric = """# Phase84 External Human Review Rubric

Allowed labels:

- `same_cell_supported`: visual evidence supports the same-cell link.
- `unsupported`: visual evidence points to a different cell or impossible link.
- `uncertain`: insufficient or ambiguous visual evidence.

Only consensus `same_cell_supported` labels can enter the PARC-A one-sided
verified-positive set.  `unsupported` and `uncertain` are not trusted
negatives and must remain unverified for PARC calibration.
"""
    (OUT / "PHASE84_HUMAN_REVIEW_RUBRIC.md").write_text(rubric, encoding="utf-8")


def upsert_artifact_index() -> None:
    row = {
        "milestone": "ncs_phase84_real_audit_parc_a_replication",
        "path": rel(OUT) + "/",
        "evidence_state": "workflow_replication_packet_frozen_pending_external_labels_not_positive_evidence",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase84_real_audit_parc_a_replication",
    }
    index = pd.read_csv(ARTIFACT_INDEX)
    index = index[index["milestone"] != row["milestone"]]
    index = pd.concat([index, pd.DataFrame([row])[index.columns]], ignore_index=True)
    index.to_csv(ARTIFACT_INDEX, index=False)


def upsert_ledger() -> None:
    row = {
        "claim_id": "CTC-PHASE84-REAL-AUDIT-PARCA-001",
        "claim_text": "Phase84 freezes a real-audit PARC-A workflow replication packet before external human labels are returned.",
        "evidence_type": "external_audit_protocol_packet",
        "positive_evidence": "no",
        "scope": "external_labels_pending;not_completed_audit",
        "artifact_path": rel(OUT / "table_phase84_claim_gate.csv"),
        "hash": sha256_file(OUT / "table_phase84_claim_gate.csv"),
        "validation_command": "make reproduce-ncs-phase84-real-audit-parc-a-replication",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_real_audit_success_completed_external_adjudication_new_CTC_ground_truth_raw_only_superiority_materials_or_DFT_evidence",
    }
    ledger = pd.read_csv(LEDGER)
    ledger = ledger[ledger["claim_id"] != row["claim_id"]]
    ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
    ledger.to_csv(LEDGER, index=False)


def upsert_claim_table() -> None:
    section = """\n## Phase84 Real-Audit PARC-A Replication\n\nStatus: `workflow_replication_packet_frozen_pending_external_labels`.\n\nPhase84 freezes a stronger PARC-A real-audit workflow replication packet.  The\nprimary question is whether external human one-sided calibration support can\nrerun PARC-A and unlock a K=100 CTC release, followed by an independent release\naudit.  Current status is protocol/packet only: external labels have not been\nreturned, PARC-A has not been rerun from human calibration positives, and no\nreal-audit success claim is allowed.  The tracked Phase81 source still lacks a\ntrue raw-only top-K arm, so random same-budget control is the primary workflow\ncontrol and raw-overlap rows remain diagnostic.\n"""
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    marker = "## Phase84 Real-Audit PARC-A Replication"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    registry = pd.read_csv(PHASE81 / "table_ctc_external_blind_audit_packet_registry.csv")
    ai = pd.read_csv(PHASE82 / "table_ctc_ai_preannotations.csv")
    plan = write_packet_templates(registry, ai)
    write_protocol(plan)
    write_schema_and_gates(plan)
    write_docs(plan)
    write_manifest(OUT)
    upsert_artifact_index()
    upsert_ledger()
    upsert_claim_table()
    write_root_manifest()
    print(f"[phase84] wrote {OUT.relative_to(ROOT)}")
    print("[phase84] status=workflow_replication_packet_frozen_pending_external_labels")


if __name__ == "__main__":
    main()
