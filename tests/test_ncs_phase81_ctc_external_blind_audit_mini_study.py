from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase81_ctc_external_blind_audit_mini_study"


def test_phase81_outputs_exist_and_pending_scope() -> None:
    expected = {
        "PHASE81_CTC_EXTERNAL_BLIND_AUDIT_PROTOCOL.md",
        "README_evidence_scope.md",
        "table_ctc_external_blind_audit_packet_registry.csv",
        "external_blind_auditor_A_template.csv",
        "external_blind_auditor_B_template.csv",
        "external_blind_adjudication_template.csv",
        "label_ingest_schema.json",
        "table_ctc_external_blind_audit_arm_plan.csv",
        "table_ctc_external_blind_audit_arm_availability.csv",
        "table_ctc_external_blind_audit_packet_integrity.csv",
        "table_ctc_external_blind_audit_claim_gate.csv",
        "figure_ctc_external_blind_audit_packet_inputs.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "packet_frozen_pending_independent_labels" in readme
    assert "may not support a completed audit result" in readme


def test_phase81_blind_templates_are_blinded_and_sized() -> None:
    template_a = pd.read_csv(OUT / "external_blind_auditor_A_template.csv")
    template_b = pd.read_csv(OUT / "external_blind_auditor_B_template.csv")
    assert len(template_a) == 600
    assert len(template_b) == 600
    assert template_a["audit_item_id"].tolist() == template_b["audit_item_id"].tolist()
    forbidden = {
        "intended_arm",
        "source_audit_id",
        "queue_membership",
        "candidate_rank",
        "score",
        "path_id",
        "human_label",
        "human_verified_positive_for_calibration",
        "human_reason",
        "human_confidence",
        "human_review_status",
    }
    assert not forbidden.intersection(template_a.columns)
    assert template_a["auditor_label"].fillna("").eq("").all()
    assert template_a["auditor_confidence"].fillna("").eq("").all()


def test_phase81_registry_and_arm_availability_are_honest() -> None:
    registry = pd.read_csv(OUT / "table_ctc_external_blind_audit_packet_registry.csv")
    assert len(registry) == 600
    assert registry["audit_item_id"].is_unique
    arm_counts = registry["intended_arm"].value_counts().to_dict()
    assert arm_counts["parc_release_core"] == 250
    assert arm_counts["raw_topK_reference_overlap"] == 100
    assert arm_counts["calibration_one_sided_support_pool"] == 150
    assert arm_counts["hard_negative_or_uncertain_control"] == 45
    assert arm_counts["random_blind_control_from_available_reviewed_rows"] == 55
    assert "human_label" not in registry.columns

    availability = pd.read_csv(OUT / "table_ctc_external_blind_audit_arm_availability.csv")
    raw_only = availability[availability["desired_arm"].eq("raw-only top-K")].iloc[0]
    assert raw_only["available_in_phase81_packet"] == "no"
    assert int(raw_only["selected_rows"]) == 0
    assert "requires regenerating or restoring the full candidate universe" in raw_only["blocker_or_note"]


def test_phase81_integrity_and_claim_gate_keep_it_non_positive() -> None:
    integrity = pd.read_csv(OUT / "table_ctc_external_blind_audit_packet_integrity.csv")
    checks = {row["check"]: row for _, row in integrity.iterrows()}
    assert checks["packet_size"]["passes"] == True
    assert checks["blind_templates_hide_arm_score_rank_and_prior_labels"]["passes"] == True
    assert checks["raw_only_arm_available"]["passes"] == False
    assert checks["returned_independent_labels_available"]["passes"] == False

    gate = pd.read_csv(OUT / "table_ctc_external_blind_audit_claim_gate.csv")
    assert len(gate) == 1
    row = gate.iloc[0]
    assert row["status"] == "packet_frozen_pending_independent_labels"
    assert row["positive_evidence"] == "no"
    assert "independent blind labels not returned" in row["current_blocker"]
    assert "Do not claim completed external audit" in row["forbidden_current_claim"]


def test_phase81_ledger_and_claim_table_guardrails() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("CTC-EXT-BLIND-AUDIT-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_completed_external_audit" in row.iloc[0]["overclaim_guardrail"]
    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase81 CTC External Blind Audit Mini-Study" in claim_table
    assert "not completed positive evidence" in claim_table


def test_phase81_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase81-ctc-external-blind-audit-mini-study"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "packet_frozen_pending_independent_labels" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase81_ctc_external_blind_audit_mini_study"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
