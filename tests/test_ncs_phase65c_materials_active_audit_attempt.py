from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE65C = ROOT / "outputs/milestones/ncs_phase65c_materials_active_audit_attempt"


def test_phase65c_outputs_exist() -> None:
    expected = {
        "table_materials_active_audit_seed_rows.csv",
        "table_materials_active_audit_policy_comparison.csv",
        "table_materials_active_audit_budget_frontier.csv",
        "table_materials_active_audit_release_transition.csv",
        "table_materials_active_audit_t1_utility.csv",
        "table_materials_active_audit_claim_gate.csv",
        "figure_materials_active_audit_inputs.csv",
        "NCS_PHASE65C_MATERIALS_ACTIVE_AUDIT_ATTEMPT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE65C / name).exists()]


def test_phase65c_required_materials_policies_and_scope() -> None:
    comparison = pd.read_csv(PHASE65C / "table_materials_active_audit_policy_comparison.csv")
    required = {
        "random",
        "raw_score_targeted",
        "parc_m_evidence_targeted",
        "chgnet_mace_support_targeted",
        "mass_gain",
    }
    assert required.issubset(set(comparison["audit_policy"]))
    assert set(comparison["K"]) == {300, 500}
    assert comparison["evidence_scope"].str.contains("not_prospective_materials_discovery").all()
    assert comparison["evidence_scope"].str.contains("not_DFT_evidence").all()


def test_phase65c_reports_t0_transition_and_t1_utility() -> None:
    transition = pd.read_csv(PHASE65C / "table_materials_active_audit_release_transition.csv")
    assert {"first_any_safe_t0_budget_fraction", "first_strict_20of20_t0_budget_fraction"}.issubset(transition.columns)
    utility = pd.read_csv(PHASE65C / "table_materials_active_audit_t1_utility.csv")
    assert {"mean_t1_label_coverage", "mean_t1_FTR_known", "mean_raw_topK_t1_FTR_known"}.issubset(utility.columns)
    assert utility["mean_t1_label_coverage"].max() > 0.0


def test_phase65c_claim_gate_forbids_materials_overclaim() -> None:
    gate = pd.read_csv(PHASE65C / "table_materials_active_audit_claim_gate.csv")
    assert set(gate["K"]) == {300, 500}
    assert gate["evidence_scope"].str.contains("not_materials_primary_headline").all()
    closeout = (PHASE65C / "NCS_PHASE65C_MATERIALS_ACTIVE_AUDIT_ATTEMPT.md").read_text(encoding="utf-8")
    assert "no prospective materials discovery" in closeout
    assert "no t1 alpha certificate" in closeout
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("MAT-PARCA-ACTIVE-001")]
    assert len(row) == 1
    assert "not_prospective_discovery" not in row.iloc[0]["positive_evidence"]


def test_phase65c_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase65c-materials-active-audit-attempt"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase65c_materials_active_audit_attempt" in result.stdout
