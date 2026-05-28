from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE65 = ROOT / "outputs/milestones/ncs_phase65_parc_a_certificate_directed_policy"


def test_phase65_outputs_exist() -> None:
    expected = {
        "PARC_A_POLICY_PREREGISTRATION.md",
        "table_parc_a_policy_seed_rows.csv",
        "table_parc_a_policy_comparison.csv",
        "table_parc_a_budget_frontier.csv",
        "table_parc_a_release_transition.csv",
        "table_parc_a_random_transition_control.csv",
        "table_parc_a_validity_scope.csv",
        "table_parc_a_claim_gate.csv",
        "figure_parc_a_certificate_directed_policy_inputs.csv",
        "NCS_PHASE65_PARC_A_CERTIFICATE_DIRECTED_POLICY.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE65 / name).exists()]


def test_phase65_compares_required_acquisition_policies() -> None:
    comparison = pd.read_csv(PHASE65 / "table_parc_a_policy_comparison.csv")
    required = {
        "random",
        "score_targeted",
        "block_max_gain",
        "mass_gain",
        "diversity_mass_gain",
    }
    assert required.issubset(set(comparison["audit_policy"]))
    assert set(comparison["K"]) == {100, 300}
    assert comparison["evidence_scope"].str.contains("primary_CTC_only").all()
    assert comparison["evidence_scope"].str.contains("not_new_human_labels").all()


def test_phase65_primary_gate_is_go_medium_not_go_strong() -> None:
    gate = pd.read_csv(PHASE65 / "table_parc_a_claim_gate.csv").set_index("gate")
    assert gate.loc["score_targeted_primary_at_or_below_0p5pct_transition", "status"] == "PASS"
    assert gate.loc["random_budget_multiplier_ge_100x", "status"] == "PASS"
    assert gate.loc["certificate_directed_policy_reaches_original_0p5pct_transition", "status"] == "PASS"
    assert gate.loc["certificate_directed_policy_random_multiplier_ge_100x", "status"] == "PASS"
    assert gate.loc["phase65_GO_medium_method_claim_allowed", "status"] == "PASS"
    assert gate.loc["certificate_directed_policy_beats_score_targeted", "status"] == "FAIL"
    assert gate.loc["certificate_directed_policy_matches_fine_grid_score_targeted", "status"] == "FAIL"


def test_phase65_transition_numbers_are_consistent() -> None:
    transition = pd.read_csv(PHASE65 / "table_parc_a_release_transition.csv")
    k100 = transition[transition["target_row"].eq("ctc_learned_strict_alpha010_K100")].set_index("audit_policy")
    assert k100.loc["score_targeted", "first_strict_20of20_budget_fraction"] <= 0.005
    assert k100.loc["mass_gain", "first_strict_20of20_budget_fraction"] == 0.005
    assert k100.loc["diversity_mass_gain", "first_strict_20of20_budget_fraction"] == 0.005
    assert k100.loc["random", "first_strict_20of20_budget_fraction"] == 1.0

    random = pd.read_csv(PHASE65 / "table_parc_a_random_transition_control.csv")
    row = random[random["target_row"].eq("ctc_learned_strict_alpha010_K100")].iloc[0]
    assert row["random_budget_multiplier"] >= 100.0


def test_phase65_closeout_and_ledger_forbid_overclaim() -> None:
    closeout = (PHASE65 / "NCS_PHASE65_PARC_A_CERTIFICATE_DIRECTED_POLICY.md").read_text(encoding="utf-8")
    for phrase in [
        "completed_GO_medium_certificate_directed_policy",
        "Score-targeted audit remains the strongest fine-grid empirical transition",
        "no new human labels",
        "no DFT evidence",
        "no prospective materials discovery",
        "no claim that materials are a Phase65 primary active-verification success",
    ]:
        assert phrase in closeout

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("CTC-PARCA-POLICY-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "partial"
    assert "primary_CTC_only" in row.iloc[0]["scope"]
    assert "do_not_claim_new_human_labels" in row.iloc[0]["overclaim_guardrail"]


def test_phase65_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase65-parc-a-certificate-directed-policy"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase65_parc_a_certificate_directed_policy" in result.stdout
