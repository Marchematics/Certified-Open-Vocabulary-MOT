from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE65B = ROOT / "outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics"


def test_phase65b_outputs_exist() -> None:
    expected = {
        "table_parc_a_budget_frontier_finegrid.csv",
        "table_parc_a_positive_yield_by_policy.csv",
        "table_parc_a_blockmax_removal.csv",
        "table_parc_a_evidence_mass_transition.csv",
        "figure_parc_a_phase_transition_inputs.csv",
        "table_parc_a_mechanism_gate.csv",
        "NCS_PHASE65B_PARC_A_MECHANISM_DIAGNOSTICS.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE65B / name).exists()]


def test_phase65b_finegrid_contains_score_transition_and_random_control() -> None:
    frontier = pd.read_csv(PHASE65B / "table_parc_a_budget_frontier_finegrid.csv")
    assert {0.0015, 0.002, 0.003, 0.004}.issubset(set(frontier["audit_budget_fraction"].round(4)))
    k100 = frontier[frontier["target_row"].eq("ctc_learned_strict_alpha010_K100")]
    score_002 = k100[(k100["audit_policy"].eq("score_targeted")) & (k100["audit_budget_fraction"].eq(0.002))].iloc[0]
    assert score_002["safe_seeds"] == 20
    random_full = k100[(k100["audit_policy"].eq("random")) & (k100["audit_budget_fraction"].eq(1.0))].iloc[0]
    assert random_full["safe_seeds"] == 20


def test_phase65b_mechanism_gate_and_scope() -> None:
    gate = pd.read_csv(PHASE65B / "table_parc_a_mechanism_gate.csv").set_index("gate")
    assert gate.loc["score_0p2pct_safe_release_20of20", "status"] == "PASS"
    assert gate.loc["score_removes_more_blockmax_than_random_at_0p2pct", "status"] == "PASS"
    assert gate.loc["mechanism_claim_allowed", "status"] == "PASS"
    assert gate["evidence_scope"].str.contains("not_new_human_labels").all()
    assert gate["evidence_scope"].str.contains("not_prospective_materials_discovery").all()


def test_phase65b_closeout_and_ledger() -> None:
    closeout = (PHASE65B / "NCS_PHASE65B_PARC_A_MECHANISM_DIAGNOSTICS.md").read_text(encoding="utf-8")
    assert "high-score one-sided positives remove calibration" in closeout
    assert "no new human audit" in closeout
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("CTC-PARCA-MECH-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "partial"


def test_phase65b_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase65b-parc-a-mechanism-diagnostics"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase65b_parc_a_mechanism_diagnostics" in result.stdout
