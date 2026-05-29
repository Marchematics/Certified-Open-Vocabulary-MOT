from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase69b_parc_d_hardening"


def test_phase69b_outputs_exist_and_are_scoped() -> None:
    expected = {
        "table_parc_d_self_consistency_check.csv",
        "table_parc_d_beta_ucb_sensitivity.csv",
        "table_parc_d_full_grid.csv",
        "table_parc_d_primary_selection_rule.csv",
        "table_parc_d_negative_controls.csv",
        "table_parc_d_feature_ablation.csv",
        "figure_parc_d_budget_frontier_inputs.csv",
        "PARC_D_METHOD_FORMALIZATION.md",
        "README_evidence_scope.md",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "no full current-MP alpha certificate",
        "no label-free deployment predictor",
        "no prospective materials discovery",
        "no DFT validation evidence",
    ]:
        assert phrase in readme


def test_primary_row_is_hardened_to_risk_triage_not_alpha_certificate() -> None:
    selection = pd.read_csv(OUT / "table_parc_d_primary_selection_rule.csv")
    assert len(selection) == 1
    row = selection.iloc[0]
    assert row["risk_model"] == "system_margin_distribution"
    assert int(row["K"]) == 300
    assert float(row["alpha0"]) == 0.01
    assert float(row["retain_fraction"]) == 0.4
    assert int(row["release_size_candidate_level"]) == 89
    assert bool(row["passes_95pct_beta_budget"])
    assert not bool(row["passes_97p5pct_beta_budget"])
    assert not bool(row["passes_postfilter_self_consistency"])
    assert row["claim_after_hardening"] == "PARC_D_risk_triage_positive_not_alpha_certificate"
    assert not bool(row["uses_heldout_t1_FTR_for_selection"])


def test_self_consistency_check_blocks_certificate_overclaim() -> None:
    checks = pd.read_csv(OUT / "table_parc_d_self_consistency_check.csv")
    primary = checks[
        (checks["check_unit"] == "aggregate")
        & (checks["risk_model"] == "system_margin_distribution")
        & (checks["K"] == 300)
        & (checks["alpha0"] == 0.01)
        & (checks["retain_fraction"] == 0.4)
    ]
    assert len(primary) == 1
    row = primary.iloc[0]
    assert int(row["release_size"]) == 89
    assert float(row["required_evalue"]) > float(row["min_evalue"])
    assert not bool(row["passes_self_consistency"])
    assert int(row["n_failed_candidates"]) > 0
    assert row["claim_after_self_consistency"] == "risk_triage_subset_not_alpha_certificate"


def test_beta_sensitivity_reports_near_boundary_behavior() -> None:
    beta = pd.read_csv(OUT / "table_parc_d_beta_ucb_sensitivity.csv")
    primary = beta[
        (beta["risk_model"] == "system_margin_distribution")
        & (beta["K"] == 300)
        & (beta["alpha0"] == 0.01)
        & (beta["retain_fraction"] == 0.4)
    ]
    assert set(primary["beta_UCB_confidence_level"]) == {0.90, 0.95, 0.975}
    pass95 = primary[primary["beta_UCB_confidence_level"] == 0.95].iloc[0]
    pass975 = primary[primary["beta_UCB_confidence_level"] == 0.975].iloc[0]
    assert bool(pass95["budget_pass_pre_eval"])
    assert float(pass95["alpha0_plus_beta_UCB"]) <= 0.10
    assert not bool(pass975["budget_pass_pre_eval"])
    assert float(pass975["alpha0_plus_beta_UCB"]) > 0.10


def test_negative_controls_and_feature_ablation_support_system_level_claim() -> None:
    controls = pd.read_csv(OUT / "table_parc_d_negative_controls.csv")
    margin = controls[controls["control_id"] == "model_auc_candidate_margin_only"].iloc[0]
    score = controls[controls["control_id"] == "model_auc_candidate_t0_score_only"].iloc[0]
    perm = controls[controls["control_id"] == "primary_label_permutation_global"].iloc[0]
    within = controls[controls["control_id"] == "primary_label_permutation_within_chemical_system"].iloc[0]
    assert float(margin["observed_auc"]) < 0.60
    assert float(score["observed_auc"]) < 0.60
    assert abs(float(perm["control_auc_mean"]) - 0.5) < 0.08
    assert within["control_result"] == "not_a_valid_signal_breaker_for_system_constant_features"

    ablation = pd.read_csv(OUT / "table_parc_d_feature_ablation.csv")
    system = ablation[ablation["risk_model"] == "system_margin_distribution"].iloc[0]
    near_candidate = ablation[ablation["risk_model"] == "candidate_margin_only"].iloc[0]
    assert float(system["mean_roc_auc"]) > float(near_candidate["mean_roc_auc"]) + 0.20


def test_phase69b_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase69b-parc-d-hardening"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "completed_PARC_D_hardening" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase69b_parc_d_hardening"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
