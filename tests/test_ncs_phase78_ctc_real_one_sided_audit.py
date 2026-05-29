from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase78_ctc_real_one_sided_audit"


def test_phase78_outputs_exist_and_scope() -> None:
    expected = {
        "table_ctc_real_audit_arm_summary.csv",
        "table_ctc_real_audit_release_gate.csv",
        "table_ctc_real_audit_one_sided_support.csv",
        "table_ctc_real_audit_uncertainty_bounds.csv",
        "table_ctc_real_audit_claim_scope.csv",
        "figure_ctc_real_audit_inputs.csv",
        "README_evidence_scope.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "does not create new labels",
        "trained human review",
        "human-confirmed one-sided audit",
        "do not claim microscopy-expert adjudication",
        "not_same_cell_link",
        "must not be treated as trusted negatives",
    ]:
        assert phrase in readme


def test_phase78_release_gate_passes_with_zero_false_and_uncertain() -> None:
    gate = pd.read_csv(OUT / "table_ctc_real_audit_release_gate.csv")
    assert len(gate) == 1
    row = gate.iloc[0]
    assert row["decision"] == "go"
    assert int(row["release_rows"]) == 1064
    assert int(row["human_false_rows"]) == 0
    assert int(row["uncertain_rows"]) == 0
    assert float(row["human_false_fraction"]) == 0.0
    assert float(row["uncertain_as_false_fraction"]) == 0.0
    assert 0.0 < float(row["wilson_upper95_uncertain_as_false"]) < 0.01


def test_phase78_one_sided_rule_and_no_expert_claim() -> None:
    support = pd.read_csv(OUT / "table_ctc_real_audit_one_sided_support.csv")
    assert len(support) == 1
    row = support.iloc[0]
    assert row["allowed_positive_label"] == "same_cell_link"
    assert "must_remain_unverified" in row["forbidden_negative_use"]
    assert int(row["calibration_rows"]) == 1500
    assert int(row["calibration_verified_positive_yes"]) == 1455
    assert int(row["calibration_not_same_or_uncertain"]) == 45
    assert not bool(row["expert_review_claimed"])
    assert "trained human review" in row["allowed_paper_wording"]
    assert "microscopy-expert" in row["forbidden_paper_wording"]


def test_phase78_arm_summary_matches_source_package() -> None:
    summary = pd.read_csv(OUT / "table_ctc_real_audit_arm_summary.csv")
    arms = set(summary["audit_arm"])
    assert {
        "all_human_confirmed_rows",
        "calibration_one_sided_support_pool",
        "simulated_strict_release_queue",
        "raw_topK_reference_overlap",
        "not_same_or_uncertain_control_rows",
    }.issubset(arms)
    all_rows = summary[summary["audit_arm"].eq("all_human_confirmed_rows")].iloc[0]
    assert int(all_rows["rows"]) == 2564
    assert int(all_rows["same_cell_link"]) == 2519
    assert int(all_rows["not_same_cell_link"]) == 45
    release = summary[summary["audit_arm"].eq("simulated_strict_release_queue")].iloc[0]
    assert int(release["same_cell_link"]) == 1064
    assert int(release["not_same_cell_link"]) == 0
    assert summary["evidence_scope"].str.contains("not_DFT_evidence").all()


def test_phase78_claim_scope_and_ledger_guardrails() -> None:
    scope = pd.read_csv(OUT / "table_ctc_real_audit_claim_scope.csv")
    assert set(scope["claim_id"]) == {"CTC-REAL-AUDIT-001", "CTC-REAL-AUDIT-002", "CTC-REAL-AUDIT-003"}
    assert scope["forbidden_claim"].str.contains("expert|trusted negatives|broad", case=False, regex=True).any()
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("CTC-REAL-AUDIT-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "yes"
    assert "do_not_claim_microscopy_expert_adjudication" in row.iloc[0]["overclaim_guardrail"]


def test_phase78_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase78-ctc-real-one-sided-audit"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "completed_CTC_real_one_sided_audit_integration" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase78_ctc_real_one_sided_audit"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
