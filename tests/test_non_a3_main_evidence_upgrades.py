from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONES = ROOT / "outputs" / "milestones"


NEW_MILESTONES = [
    "materials_temporal_replay_completed",
    "fixed_budget_scientific_utility_trial",
    "adversarial_release_stress_trial",
    "selector_optimality_diagnostics",
]


def test_non_a3_milestones_exist_and_are_indexed() -> None:
    artifact = pd.read_csv(ROOT / "outputs" / "artifact_index.csv")
    for name in NEW_MILESTONES:
        root = MILESTONES / name
        assert root.exists(), name
        assert (root / "MANIFEST_SHA256.txt").exists(), name
        assert name in set(artifact["milestone"])


def test_temporal_replay_is_not_promoted_without_snapshots() -> None:
    primary = pd.read_csv(MILESTONES / "materials_temporal_replay_completed" / "table_temporal_primary.csv")
    inventory = pd.read_csv(
        MILESTONES / "materials_temporal_replay_completed" / "table_temporal_snapshot_inventory.csv"
    )
    assert not primary["completed_positive_result"].astype(bool).any()
    assert set(primary["evidence_state"]) == {"protocol_only"}
    assert "missing_t0_t1" in primary["release_version_inputs"].iloc[0]
    assert inventory["status"].astype(str).str.contains("missing_timestamped_public_label_release").any()


def test_fixed_budget_scientific_utility_has_material_effect_rows() -> None:
    false_followups = pd.read_csv(
        MILESTONES / "fixed_budget_scientific_utility_trial" / "table_false_followups_prevented.csv"
    )
    curve = pd.read_csv(MILESTONES / "fixed_budget_scientific_utility_trial" / "table_decision_curve.csv")
    cost = pd.read_csv(MILESTONES / "fixed_budget_scientific_utility_trial" / "table_cost_per_true_candidate.csv")
    k500 = false_followups[
        false_followups["proposal_source"].astype(str).str.contains("alignn_ff", case=False, na=False)
        & (false_followups["K"].astype(int) == 500)
        & (false_followups["alpha"].astype(float) == 0.10)
    ].iloc[0]
    assert float(k500["prevented_unstable_followups_mean"]) > 100
    assert float(k500["raw_topK_FTR_mean"]) > float(k500["PARC_FTR_mean"])
    assert "completed_evidence" in set(curve["evidence_state"])
    assert "cost_per_true_candidate_PARC" in cost.columns


def test_adversarial_stress_contains_refusal_boundaries_without_positive_promotion() -> None:
    stress = pd.read_csv(MILESTONES / "adversarial_release_stress_trial" / "table_adversarial_stress_trials.csv")
    scope = pd.read_csv(MILESTONES / "adversarial_release_stress_trial" / "table_stress_claim_scope.csv")
    assert {"score_corruption", "high_K_unsafe_request"}.issubset(set(stress["stress_family"]))
    assert stress["evidence_state"].astype(str).str.contains("diagnostic|sensitivity|evidence").all()
    assert "not_claimed" in set(scope["evidence_state"])


def test_selector_diagnostics_do_not_fabricate_ilp_rescue() -> None:
    mass = pd.read_csv(MILESTONES / "selector_optimality_diagnostics" / "table_mass_vs_graph_failure.csv")
    loss = pd.read_csv(MILESTONES / "selector_optimality_diagnostics" / "table_conflict_loss.csv")
    scope = pd.read_csv(MILESTONES / "selector_optimality_diagnostics" / "table_selector_claim_scope.csv")
    assert not mass.empty
    assert {"mass_failure", "finite_resolution_failure", "selector_power_limitation"}.issubset(mass.columns)
    assert not mass["selector_power_limitation"].astype(bool).any()
    assert loss["conflict_loss_interpretation"].astype(str).str.contains("before selector optimality").any()
    assert "not_claimed" in set(scope["evidence_state"])


def test_claim_table_lists_non_a3_upgrades_with_scope_limits() -> None:
    text = (ROOT / "docs" / "claim_table.md").read_text(encoding="utf-8")
    assert "Materials temporal replay remains blocked" in text
    assert "Fixed-budget scientific utility" in text
    assert "Adversarial release stress" in text
    assert "Selector optimality diagnostics" in text
    assert "must not be promoted" in text
