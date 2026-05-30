#!/usr/bin/env python3
"""Build Phase89 NCS submission integration map for A.

This translates Phase88 low-cost editorial hardening into concrete manuscript
integration targets. It is not a manuscript rewrite and not new evidence.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE88 = ROOT / "outputs/milestones/ncs_phase88_low_cost_editorial_hardening"
OUT = ROOT / "outputs/milestones/ncs_phase89_submission_integration_map"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "NCS_phase89_submission_integration_map;"
    "manuscript_integration_plan_only;"
    "no_new_empirical_result;"
    "no_new_human_labels;"
    "not_DFT_evidence;"
    "not_prospective_materials_discovery"
)


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
        if ".pytest_cache" in path.parts or "tmp" in path.parts:
            continue
        if "cache" in path.parts or "third_party" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_tables() -> None:
    actions = pd.read_csv(PHASE88 / "table_low_cost_action_matrix.csv")
    rows = []
    mapping = {
        "rewrite_first_screen": ("Title/Abstract/Introduction paragraph 1", "must_apply_before_submission"),
        "front_existing_real_audit_envelopes": ("Cover letter and operating-envelope paragraph", "apply_with_pending_boundary"),
        "front_phase83_necessity_and_prevented_harm": ("Introduction paragraph 2, Figure 3 caption, Discussion", "must_apply_before_submission"),
        "insert_capability_table": ("Figure 6 or Extended Data table", "must_apply_before_submission"),
        "overclaim_scrub": ("Full manuscript, cover letter, abstract, figure captions", "must_apply_before_submission"),
    }
    for action in actions.itertuples(index=False):
        target, status = mapping[action.action]
        rows.append(
            {
                "integration_id": f"NCS89-{len(rows)+1:03d}",
                "action": action.action,
                "target_location": target,
                "integration_status": status,
                "source_artifact": f"outputs/milestones/ncs_phase88_low_cost_editorial_hardening/{action.artifact.split(';')[0]}",
                "guardrail": action.guardrail,
                "evidence_scope": SCOPE,
            }
        )
    pd.DataFrame(rows).to_csv(OUT / "table_phase89_integration_targets.csv", index=False)

    pd.DataFrame(
        [
            {
                "check_id": "SUBMIT-A-001",
                "question": "Does the first paragraph define release cards as the object, not top-K ranking or e-values?",
                "required_answer": "yes",
                "blocking_if_no": True,
                "evidence_scope": SCOPE,
            },
            {
                "check_id": "SUBMIT-A-002",
                "question": "Are Phase81 labels excluded unless gate-passing labels exist?",
                "required_answer": "yes",
                "blocking_if_no": True,
                "evidence_scope": SCOPE,
            },
            {
                "check_id": "SUBMIT-A-003",
                "question": "Are materials framed only as reference-drift stress test / expiry / triage?",
                "required_answer": "yes",
                "blocking_if_no": True,
                "evidence_scope": SCOPE,
            },
            {
                "check_id": "SUBMIT-A-004",
                "question": "Does the capability table avoid presenting e-BH as a strawman FTR baseline?",
                "required_answer": "yes",
                "blocking_if_no": True,
                "evidence_scope": SCOPE,
            },
            {
                "check_id": "SUBMIT-A-005",
                "question": "Are DFT-v2 and B-line claim-decay outputs absent from A positive claims unless independently claim-ready?",
                "required_answer": "yes",
                "blocking_if_no": True,
                "evidence_scope": SCOPE,
            },
        ]
    ).to_csv(OUT / "table_submission_blocker_checklist.csv", index=False)

    pd.DataFrame(
        [
            {
                "section": "Abstract",
                "max_role": "state release-card lifecycle, PARC-A, and materials stress-test boundary",
                "must_not_include": "Phase81 pending labels; B-line smoke; DFT-v2 pending outcomes",
                "evidence_scope": SCOPE,
            },
            {
                "section": "Cover letter",
                "max_role": "make scientific-AI release infrastructure and prevented harm visible",
                "must_not_include": "claim that NCS/NC desk review is guaranteed",
                "evidence_scope": SCOPE,
            },
            {
                "section": "Materials Results",
                "max_role": "versioned reference-drift stress test and risk triage",
                "must_not_include": "current-MP alpha certificate or prospective discovery",
                "evidence_scope": SCOPE,
            },
            {
                "section": "Methods/Supplement",
                "max_role": "necessity principles and lifecycle calculus",
                "must_not_include": "universal optimality claim",
                "evidence_scope": SCOPE,
            },
        ]
    ).to_csv(OUT / "table_section_scope_map.csv", index=False)


def write_docs_and_gate() -> None:
    gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase89_submission_integration_map",
                "status": "integration_plan_ready_not_manuscript_rewrite",
                "positive_evidence": "synthesis_only",
                "allowed_current_claim": "Phase89 maps Phase88 low-cost editorial hardening artifacts to concrete manuscript integration targets.",
                "forbidden_current_claim": "Do not claim manuscript submission, new evidence, completed Phase81 audit, B-line evidence in A, DFT validation, or prospective materials discovery.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    gate.to_csv(OUT / "table_phase89_submission_integration_claim_gate.csv", index=False)

    readme = f"""# Phase89 Submission Integration Map

Status: `integration_plan_ready_not_manuscript_rewrite`.

This A-line artifact maps Phase88 low-cost editorial hardening into concrete
manuscript locations and blocking submission checks. It does not rewrite the
manuscript and does not add evidence.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    brief = """# Phase89 Integration Brief

Use this package as the final pre-edit map:

1. Apply the release-card first-screen replacement.
2. Insert the capability table in Figure 6 or Extended Data.
3. Move Phase83 necessity and prevented-harm language into visible text.
4. Keep Phase81, DFT-v2 and B-line outputs out of A positive claims unless
   separately gate-passing.
"""
    (OUT / "NCS_PHASE89_SUBMISSION_INTEGRATION_MAP.md").write_text(brief, encoding="utf-8")


def update_artifact_index() -> None:
    row = {
        "milestone": "ncs_phase89_submission_integration_map",
        "path": "outputs/milestones/ncs_phase89_submission_integration_map/",
        "evidence_state": "integration_plan_ready_not_manuscript_rewrite",
        "manifest": "outputs/milestones/ncs_phase89_submission_integration_map/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase89_submission_integration_map",
        "notes": "Maps Phase88 low-cost editorial hardening into A manuscript integration targets.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(ARTIFACT_INDEX, index=False)


def update_ledger() -> None:
    row = {
        "claim_id": "NCS-PHASE89-SUBMISSION-INTEGRATION-001",
        "claim_text": "Phase89 maps low-cost editorial hardening artifacts to concrete A-manuscript integration targets.",
        "evidence_type": "submission_integration_plan",
        "positive_evidence": "synthesis_only",
        "scope": "not_new_evidence;not_manuscript_submission;not_B_line",
        "artifact_path": "outputs/milestones/ncs_phase89_submission_integration_map/table_phase89_submission_integration_claim_gate.csv",
        "hash": sha256_file(OUT / "table_phase89_submission_integration_claim_gate.csv"),
        "validation_command": "make reproduce-ncs-phase89-submission-integration-map",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_submission_or_new_evidence",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """
## Phase89 NCS Submission Integration Map

Status: `integration_plan_ready_not_manuscript_rewrite`.

Phase89 maps Phase88 low-cost editorial hardening artifacts to concrete
A-manuscript integration targets and blocking submission checks. It is not new
evidence and not a completed manuscript submission.
"""
    marker = "## Phase89 NCS Submission Integration Map"
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    if marker in text:
        before = text.split(marker)[0].rstrip()
        after = text.split(marker, 1)[1]
        next_idx = after.find("\n## ")
        if next_idx >= 0:
            text = before + "\n" + section + after[next_idx:]
        else:
            text = before + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    if not PHASE88.exists():
        raise FileNotFoundError("Phase88 editorial hardening artifact is required")
    OUT.mkdir(parents=True, exist_ok=True)
    write_tables()
    write_docs_and_gate()
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase89-a] wrote {rel(OUT)}")
    print("[phase89-a] status=integration_plan_ready_not_manuscript_rewrite")


if __name__ == "__main__":
    main()
