from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONES = ROOT / "outputs" / "milestones"


FINAL_MILESTONES = [
    "materials_temporal_validation",
    "materials_independent_dft_validation",
    "fixed_budget_downstream_utility",
    "primary_statistics",
    "materials_robustness_triad",
    "baseline_matrix_final",
    "ctc_strict_anchor",
    "iwildcam_audit_final",
    "spacenet_real_audit_final",
    "reproducibility_freeze",
]


def test_experimental_plan_file_exists_and_scopes_evidence() -> None:
    plan = (ROOT / "docs" / "experimental_execution_plan.md").read_text(encoding="utf-8")
    assert "completed_evidence" in plan
    assert "diagnostic" in plan
    assert "protocol_only" in plan
    assert "Materials A1/A2 Validation" in plan
    assert "Fixed-Budget Downstream Utility" in plan
    assert "CTC Strict Anchor" in plan


def test_final_milestones_exist_with_manifests() -> None:
    for name in FINAL_MILESTONES:
        root = MILESTONES / name
        assert root.exists(), name
        manifest = root / "MANIFEST_SHA256.txt"
        assert manifest.exists(), name
        assert manifest.read_text(encoding="utf-8").strip(), name


def test_a1_is_protocol_only_and_a2_is_low_coverage_diagnostic() -> None:
    temporal = pd.read_csv(MILESTONES / "materials_temporal_validation" / "table_materials_temporal_primary.csv")
    independent = pd.read_csv(
        MILESTONES / "materials_independent_dft_validation" / "table_independent_dft_primary_results.csv"
    )
    matches = pd.read_csv(
        MILESTONES / "materials_independent_dft_validation" / "table_independent_dft_candidate_matches.csv"
    )
    assert not temporal["completed_positive_result"].astype(bool).any()
    assert not independent["completed_positive_result"].astype(bool).any()
    assert temporal["evidence_status"].astype(str).str.contains("protocol_only").all()
    assert independent["evidence_status"].astype(str).str.contains("completed_independent_oqmd").all()
    assert independent["evidence_status"].astype(str).str.contains("low_coverage").all()
    assert "timestamp" in temporal["blocker"].iloc[0]
    assert "exact_structure_match" in set(matches["match_confidence"])
    assert float(independent["coverage_of_independent_source"].iloc[0]) < 0.60


def test_fixed_budget_utility_contains_completed_materials_and_consequence_rows() -> None:
    materials = pd.read_csv(
        MILESTONES / "fixed_budget_downstream_utility" / "table_materials_budget_utility_primary.csv"
    )
    ctc = pd.read_csv(MILESTONES / "fixed_budget_downstream_utility" / "table_ctc_lineage_consequence.csv")
    spacenet = pd.read_csv(
        MILESTONES / "fixed_budget_downstream_utility" / "table_spacenet_persistence_consequence.csv"
    )
    assert {"raw_topK_FTR_mean", "PARC_FTR_mean", "prevented_unstable_followups_mean"}.issubset(
        materials.columns
    )
    alignn_k500 = materials[
        materials["proposal_source"].astype(str).str.contains("alignn_ff", case=False, na=False)
        & (materials["K"] == 500)
        & (materials["alpha"] == 0.10)
    ].iloc[0]
    assert float(alignn_k500["raw_topK_FTR_mean"]) > float(alignn_k500["PARC_FTR_mean"])
    assert float(alignn_k500["prevented_unstable_followups_mean"]) > 100
    assert not ctc.empty
    assert not spacenet.empty


def test_primary_statistics_have_effect_sizes_and_intervals() -> None:
    primary = pd.read_csv(MILESTONES / "primary_statistics" / "table_primary_endpoints.csv")
    paired = pd.read_csv(MILESTONES / "primary_statistics" / "table_paired_bootstrap_seed_rows.csv")
    assert {"mean_delta", "bootstrap_CI_low", "bootstrap_CI_high", "paired_p", "holm_p"}.issubset(primary.columns)
    mat = primary[primary["domain"] == "materials_discovery"]
    assert {300, 500, 5000}.issubset(set(mat["K"].astype(int)))
    assert (mat["mean_delta"].astype(float) > 0).all()
    assert (mat["bootstrap_CI_low"].astype(float) > 0).all()
    assert not paired.empty
    ctc = primary[primary["comparison_id"] == "ctc_learned_strict_alpha010_K300"].iloc[0]
    assert ctc["claim_scope"] == "completed_masked_official_GT_evaluation"


def test_materials_robustness_triad_is_populated() -> None:
    stability = pd.read_csv(MILESTONES / "materials_robustness_triad" / "table_stability_definition_robustness.csv")
    block = pd.read_csv(MILESTONES / "materials_robustness_triad" / "table_block_definition_robustness.csv")
    gamma = pd.read_csv(MILESTONES / "materials_robustness_triad" / "table_gamma_sensitivity.csv")
    hetero = pd.read_csv(MILESTONES / "materials_robustness_triad" / "table_block_size_heterogeneity.csv")
    assert "variant" in stability.columns
    assert {"composition_family_pair", "chemical_system", "wyckoff_family"}.intersection(
        set(block.get("block_definition", pd.Series(dtype=str)).astype(str))
    )
    assert gamma["gamma"].nunique() >= 4
    assert "materials_discovery" in set(hetero["domain"])


def test_ctc_anchor_keeps_completed_and_protocol_only_controls_separate() -> None:
    leakage = pd.read_csv(MILESTONES / "ctc_strict_anchor" / "table_ctc_leakage_audit_final.csv")
    controls = pd.read_csv(MILESTONES / "ctc_strict_anchor" / "table_ctc_destroyed_ranking_controls.csv")
    reverse = pd.read_csv(MILESTONES / "ctc_strict_anchor" / "table_ctc_primary_reverse_split_summary.csv")
    assert (leakage["forbidden_GT_or_match_columns_used"] == "no").all()
    assert "completed_destroyed_ranking_control" in set(controls["evidence_status"])
    assert "protocol_only_candidate_level_universe_not_in_public_package" in set(controls["evidence_status"])
    assert (reverse[(reverse["alpha"] == 0.10) & (reverse["M"] == 100)]["nonempty_seeds"] >= 18).all()


def test_iwildcam_and_spacenet_final_audit_rows_are_scoped() -> None:
    iwild_release = pd.read_csv(MILESTONES / "iwildcam_audit_final" / "table_iwildcam_release_audit_final.csv")
    iwild_irr = pd.read_csv(
        MILESTONES / "iwildcam_audit_final" / "table_iwildcam_second_review_agreement_final.csv"
    )
    space_k50 = pd.read_csv(MILESTONES / "spacenet_real_audit_final" / "table_spacenet_k50_release_audit.csv")
    space_k100 = pd.read_csv(MILESTONES / "spacenet_real_audit_final" / "table_spacenet_k100_refusal_diagnostics.csv")
    assert int(iwild_release["n_audited_unique_released_candidates"].iloc[0]) == 167
    assert float(iwild_release["human_FTR"].iloc[0]) == 0.0
    kappa = float(iwild_irr[iwild_irr["scope"] == "all_rows"]["cohen_kappa"].iloc[0])
    assert 0.75 <= kappa <= 0.83
    assert int(space_k50["n_unique_released_candidates_reviewed"].iloc[0]) == 147
    assert float(space_k50["audited_FTR_uncertain_as_false"].iloc[0]) == 0.0
    assert int(space_k100["non_empty_seeds"].iloc[0]) == 0
    assert "refusal" in space_k100["paper_status"].iloc[0]


def test_baseline_matrix_declares_target_object_mismatch() -> None:
    target = pd.read_csv(MILESTONES / "baseline_matrix_final" / "table_baseline_target_objects.csv")
    primary = pd.read_csv(MILESTONES / "baseline_matrix_final" / "table_baseline_primary_results.csv")
    ablation = pd.read_csv(MILESTONES / "baseline_matrix_final" / "table_component_ablation_load_bearing.csv")
    parc = target[target["method"] == "PARC"].iloc[0]
    assert bool(parc["uses_null_superset"])
    assert bool(parc["uses_SCS_denominator"])
    assert "nnPU classifier release" in set(target["method"])
    assert not primary.empty
    assert not ablation.empty


def test_reproducibility_index_lists_final_milestones() -> None:
    index = pd.read_csv(MILESTONES / "reproducibility_freeze" / "table_experiment_milestone_index.csv")
    assert set(FINAL_MILESTONES) == set(index["milestone"])
    assert "protocol_only" in " ".join(index["evidence_state"].astype(str))
    assert "completed_evidence" in " ".join(index["evidence_state"].astype(str))
    artifact = pd.read_csv(ROOT / "outputs" / "artifact_index.csv")
    assert set(FINAL_MILESTONES).issubset(set(artifact["milestone"]))
