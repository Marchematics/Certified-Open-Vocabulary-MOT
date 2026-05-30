from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase84_real_audit_parc_a_replication"


def test_phase84_outputs_exist_and_pending_scope() -> None:
    expected = {
        "PHASE84_REAL_AUDIT_PARC_A_REPLICATION_PROTOCOL.md",
        "PHASE84_HUMAN_REVIEW_RUBRIC.md",
        "README_evidence_scope.md",
        "returned_human_label_schema.json",
        "table_phase84_audit_packet_plan.csv",
        "table_phase84_go_no_go_gates.csv",
        "table_phase84_claim_gate.csv",
        "table_phase84_execution_plan.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "workflow_replication_packet_frozen_pending_external_labels" in readme
    assert "not a completed audit result" in readme
    assert "true raw-only top-K arm" in readme


def test_phase84_packet_plan_has_expected_rows_and_roles() -> None:
    plan = pd.read_csv(OUT / "table_phase84_audit_packet_plan.csv")
    rows = dict(zip(plan["packet"], plan["rows"]))
    assert rows["calibration_audit"] == 150
    assert rows["release_audit"] == 250
    assert rows["random_same_budget_control"] == 55
    assert rows["raw_overlap_diagnostic"] == 100
    assert rows["hard_negative_or_uncertain_control"] == 45
    primary = set(plan[plan["primary_role"].eq("yes")]["packet"])
    assert primary == {"calibration_audit", "release_audit", "random_same_budget_control"}
    assert plan["evidence_scope"].str.contains("not_completed_positive_evidence").all()


def test_phase84_templates_are_blinded_and_ai_assisted_is_separate() -> None:
    forbidden_blind = {
        "intended_arm",
        "source_audit_id",
        "path_id",
        "candidate_rank",
        "score",
        "human_label",
        "human_verified_positive_for_calibration",
        "queue_membership",
    }
    forbidden_assisted = forbidden_blind - {"human_label"}
    for packet, expected_rows in [
        ("calibration_audit", 150),
        ("release_audit", 250),
        ("random_same_budget_control", 55),
    ]:
        blind = pd.read_csv(OUT / f"phase84_{packet}_blind_template.csv")
        assisted = pd.read_csv(OUT / f"phase84_{packet}_ai_assisted_template.csv")
        assert len(blind) == expected_rows
        assert len(assisted) == expected_rows
        assert blind["audit_item_id"].tolist() == assisted["audit_item_id"].tolist()
        assert not forbidden_blind.intersection(blind.columns)
        assert not forbidden_assisted.intersection(assisted.columns)
        assert {"auditor_label", "auditor_confidence", "auditor_notes"}.issubset(blind.columns)
        assert {"ai_label", "ai_confidence", "ai_support_score", "ai_reason"}.issubset(assisted.columns)
        assert {"human_label", "human_confidence", "human_notes", "human_accepts_ai_label"}.issubset(assisted.columns)


def test_phase84_gates_are_pending_and_do_not_claim_success() -> None:
    gates = pd.read_csv(OUT / "table_phase84_go_no_go_gates.csv")
    assert set(gates["current_status"]).issubset({"pending", "not_run_pending_labels"})
    assert gates["required_for_positive_claim"].all()
    assert gates["evidence_scope"].str.contains("external_labels_pending").all()

    claim = pd.read_csv(OUT / "table_phase84_claim_gate.csv")
    assert len(claim) == 1
    row = claim.iloc[0]
    assert row["positive_evidence"] == "no"
    assert row["status"] == "workflow_replication_packet_frozen_pending_external_labels"
    assert "real-audit PARC-A success" in row["forbidden_current_claim"]
    assert "raw-only superiority" in row["forbidden_current_claim"]


def test_phase84_ledger_and_claim_table_guardrails() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("CTC-PHASE84-REAL-AUDIT-PARCA-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_real_audit_success" in row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    claim_table_flat = " ".join(claim_table.split())
    assert "Phase84 Real-Audit PARC-A Replication" in claim_table
    assert "external labels have not been returned" in claim_table_flat


def test_phase84_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase84-real-audit-parc-a-replication"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "workflow_replication_packet_frozen_pending_external_labels" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase84_real_audit_parc_a_replication"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
