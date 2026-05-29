from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase75_active_versioned_recertification"


def test_phase75_outputs_exist_and_scope_guardrails() -> None:
    expected = {
        "table_active_recertification_budget_frontier.csv",
        "table_active_recertification_policy_comparison.csv",
        "table_active_recertification_self_consistency.csv",
        "table_active_recertification_random_transition_control.csv",
        "table_active_recertification_release_ftr.csv",
        "figure_active_recertification_frontier_inputs.csv",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    text = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "t1 public labels are used only to emulate calibration-side one-sided support",
        "test-side t1 labels are used only after SCS release",
        "null-superset denominators and e-values are recomputed after audit",
        "no DFT evidence",
        "no prospective materials discovery",
    ]:
        assert phrase in text


def test_phase75_required_grid_policies_and_support_modes() -> None:
    comparison = pd.read_csv(OUT / "table_active_recertification_policy_comparison.csv")
    required_policies = {
        "random_t1_audit",
        "score_targeted_t1_audit",
        "low_risk_score_targeted_t1_audit",
        "system_margin_distribution_low_risk_then_score",
        "blockmax_gain_t1_audit",
        "mass_gain_t1_audit",
        "diversity_mass_gain_t1_audit",
    }
    assert required_policies.issubset(set(comparison["audit_policy"]))
    assert set(comparison["K"]) == {20, 50, 100, 150, 300, 500}
    assert set(comparison["support_mode"]) == {"t1_10pct_support", "t1_full_calibration_block_support"}
    assert {0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 1.00}.issubset(
        {round(float(v), 3) for v in comparison["audit_budget_fraction_requested"]}
    )
    assert comparison["evidence_scope"].str.contains("not_DFT_evidence").all()
    assert comparison["evidence_scope"].str.contains("not_prospective_materials_discovery").all()


def test_phase75_no_t1_test_label_leakage_and_recomputed_denominator() -> None:
    scs = pd.read_csv(OUT / "table_active_recertification_self_consistency.csv")
    assert not scs["policy_uses_t1_test_labels"].astype(bool).any()
    assert not scs["heldout_t1_used_for_selection"].astype(bool).any()
    assert scs["denominator_recomputed_after_audit"].astype(bool).all()
    assert scs["evalues_recomputed_after_audit"].astype(bool).all()
    released = scs[scs["release_size"] > 0]
    if len(released):
        expected = released["K"] / (released["alpha"] * released["release_size"])
        assert (released["required_evalue_threshold"] - expected).abs().max() < 1e-9


def test_phase75_full_grid_no_go_is_explicit() -> None:
    comparison = pd.read_csv(OUT / "table_active_recertification_policy_comparison.csv")
    assert len(comparison) == 756
    assert not comparison["go_strong"].astype(bool).any()
    assert not comparison["go_medium"].astype(bool).any()
    assert comparison["nonempty_seeds"].max() == 4
    assert comparison["safe_seeds"].max() == 0
    assert comparison["max_release_size"].max() == 39

    transitions = pd.read_csv(OUT / "table_active_recertification_release_transition.csv")
    assert transitions["first_go_strong_budget_fraction"].isna().all()
    assert transitions["first_go_medium_budget_fraction"].isna().all()
    assert transitions["first_any_nonempty_budget_fraction"].notna().sum() > 0


def test_phase75_random_transition_control_and_ledger() -> None:
    random_control = pd.read_csv(OUT / "table_active_recertification_random_transition_control.csv")
    assert {"active_budget_fraction", "random_budget_fraction", "random_budget_multiplier"}.issubset(random_control.columns)
    assert len(random_control) > 0
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("PARC-ACTIVE-RECERT-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_DFT_evidence" in row.iloc[0]["overclaim_guardrail"]


def test_phase75_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase75-active-versioned-recertification"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "completed_active_recertification_no_go" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase75_active_versioned_recertification"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
