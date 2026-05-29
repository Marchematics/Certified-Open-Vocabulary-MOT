from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase69_durability_budgeted_parc"


def test_phase69_outputs_and_crossfit_scores_are_scoped() -> None:
    expected = {
        "table_crossfit_durability_risk_scores.csv",
        "table_risk_model_cv_metrics.csv",
        "table_risk_triage_frontier.csv",
        "table_durability_budgeted_release_frontier.csv",
        "table_alpha0_beta_budget_by_row.csv",
        "table_phase69_claim_gate.csv",
        "figure_durability_budget_frontier_inputs.csv",
        "README_evidence_scope.md",
    }
    assert expected.issubset({p.name for p in OUT.iterdir()})
    scores = pd.read_csv(OUT / "table_crossfit_durability_risk_scores.csv")
    assert scores["crossfit_durability_risk"].between(0, 1).all()
    assert scores["evidence_scope"].str.contains("not_full_release_alpha_certificate").all()
    assert scores["evidence_scope"].str.contains("not_DFT_evidence").all()
    assert {"system_margin_distribution", "candidate_margin_only"}.issubset(set(scores["risk_model"]))


def test_phase69_group_split_integrity_for_budget_rows() -> None:
    rows = pd.read_csv(OUT / "table_alpha0_beta_budget_by_row.csv")
    assert rows["chemical_system_overlap_n"].eq(0).all()
    assert rows["split_scope"].str.contains("heldout_chemical_systems").all()
    assert rows["beta_UCB"].between(0, 1).all()
    assert (rows["alpha0_plus_beta_UCB"] >= rows["alpha0"]).all()


def test_phase69_budget_success_cannot_ignore_budget_constraint() -> None:
    frontier = pd.read_csv(OUT / "table_durability_budgeted_release_frontier.csv")
    success = frontier[frontier["primary_success_candidate_level"].astype(bool)]
    if len(success):
        assert success["budget_pass_pre_eval"].astype(bool).all()
        assert success["alpha0_plus_beta_UCB"].le(0.10 + 1e-12).all()
        assert success["observed_FTR_t1"].le(0.10 + 1e-12).all()
        assert success["release_size_candidate_level"].ge(10).all()
    assert not frontier["primary_success_full_certificate"].astype(bool).any()
    assert not frontier["seed_level_gate_available"].astype(bool).any()


def test_phase69_guardrails_forbid_label_free_and_dft_overclaim() -> None:
    text = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "no label-free deployment predictor",
        "no prospective materials discovery",
        "no DFT evidence",
        "no full-release alpha certificate",
    ]:
        assert phrase in text
    claims = pd.read_csv(OUT / "table_phase69_claim_gate.csv")
    assert claims["guardrail"].str.contains("not_DFT_evidence|not_label_free", regex=True).all()


def test_phase69_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase69-durability-budgeted-parc"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase69_durability_budgeted_parc" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase69_durability_budgeted_parc"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

