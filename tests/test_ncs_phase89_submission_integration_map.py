from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase89_submission_integration_map"


def test_phase89_a_outputs_exist_and_are_integration_only() -> None:
    expected = {
        "README_evidence_scope.md",
        "NCS_PHASE89_SUBMISSION_INTEGRATION_MAP.md",
        "table_phase89_integration_targets.csv",
        "table_submission_blocker_checklist.csv",
        "table_section_scope_map.csv",
        "table_phase89_submission_integration_claim_gate.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    flat_readme = " ".join(readme.split())
    assert "integration_plan_ready_not_manuscript_rewrite" in readme
    assert "does not rewrite the manuscript" in flat_readme


def test_phase89_a_integration_targets_cover_phase88_actions() -> None:
    targets = pd.read_csv(OUT / "table_phase89_integration_targets.csv")
    assert {
        "rewrite_first_screen",
        "front_existing_real_audit_envelopes",
        "front_phase83_necessity_and_prevented_harm",
        "insert_capability_table",
        "overclaim_scrub",
    }.issubset(set(targets["action"]))
    assert targets["integration_status"].str.contains("must_apply|apply_with_pending_boundary", regex=True).all()
    assert targets["evidence_scope"].str.contains("no_new_empirical_result").all()


def test_phase89_a_blockers_protect_a_b_boundary() -> None:
    checks = pd.read_csv(OUT / "table_submission_blocker_checklist.csv")
    assert checks["blocking_if_no"].all()
    joined = " ".join(checks["question"].astype(str))
    assert "Phase81 labels excluded" in joined
    assert "B-line claim-decay outputs absent" in joined

    scope = pd.read_csv(OUT / "table_section_scope_map.csv")
    abstract = scope[scope["section"].eq("Abstract")].iloc[0]
    assert "B-line smoke" in abstract["must_not_include"]


def test_phase89_a_gate_ledger_claim_table_and_reproduce() -> None:
    gate = pd.read_csv(OUT / "table_phase89_submission_integration_claim_gate.csv")
    assert gate.iloc[0]["positive_evidence"] == "synthesis_only"
    assert "Do not claim manuscript submission" in gate.iloc[0]["forbidden_current_claim"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("NCS-PHASE89-SUBMISSION-INTEGRATION-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "synthesis_only"

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    flat_claim_table = " ".join(claim_table.split())
    assert "Phase89 NCS Submission Integration Map" in claim_table
    assert "not new evidence" in flat_claim_table

    result = subprocess.run(
        ["make", "reproduce-ncs-phase89-submission-integration-map"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    result = subprocess.run(
        [
            "python",
            "scripts/validate_public_bundle.py",
            "outputs/milestones/ncs_phase89_submission_integration_map",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
