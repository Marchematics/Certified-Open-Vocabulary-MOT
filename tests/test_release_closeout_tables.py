import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_ctc_learned_public_tables_exist_and_are_scoped() -> None:
    milestone = ROOT / "outputs/milestones/scientific_domain_ctc_learned"
    main = pd.read_csv(milestone / "table_ctc_learned_hybrid_main.csv")
    strict = pd.read_csv(milestone / "table_ctc_learned_strict_alpha010_smallK.csv")
    model = pd.read_csv(milestone / "table_ctc_learned_model_report.csv")
    leakage = pd.read_csv(milestone / "table_ctc_learned_leakage_audit.csv")
    reverse = pd.read_csv(milestone / "table_ctc_learned_reverse_split.csv")
    negative = pd.read_csv(milestone / "table_ctc_learned_negative_control.csv")

    assert {"rho", "alpha", "M", "nonempty_seeds", "actual_FTR_mean", "block_variant"}.issubset(main.columns)
    assert (strict["alpha"] == 0.10).all()
    assert (strict["nonempty_seeds"] >= 18).any()
    assert bool(model["uses_appearance_signal"].iloc[0])
    assert bool(model["forbidden_leakage_columns_not_used"].iloc[0])
    assert set(leakage["check_name"]) == {
        "primary_sequence_disjoint_split",
        "reverse_sequence_disjoint_split",
        "random_score_negative_control",
    }
    assert (leakage["forbidden_GT_or_match_columns_used"] == "no").all()
    assert (reverse[(reverse["alpha"] == 0.10) & (reverse["M"] == 100)]["nonempty_seeds"] >= 18).all()
    assert (negative["nonempty_seeds"] == 0).all()
    assert (negative["raw_topM_actual_FTR_mean"].astype(float) > 0.5).any()


def test_closeout_diagnostics_cover_release_and_refusal_cases() -> None:
    diagnostics = ROOT / "outputs/milestones/release_story/paper_diagnostics"
    panel = pd.read_csv(diagnostics / "table_assumption_diagnostic_panel.csv")
    seed_ci = pd.read_csv(diagnostics / "table_seed_variability_and_ci.csv")
    prevented = pd.read_csv(diagnostics / "table_prevented_false_releases.csv")
    near_boundary = pd.read_csv(diagnostics / "table_near_boundary_release_value.csv")
    contamination = pd.read_csv(diagnostics / "table_ctc_audit_contamination_sensitivity.csv")

    panel_text = " ".join(
        " ".join(map(str, row)) for row in panel.astype(object).to_numpy()
    )
    assert "CTC learned-hybrid" in panel_text
    assert "SpaceNet7 real audit" in panel_text
    assert "certified_refusal" in panel_text or "human_audit_certified_refusal" in panel_text
    assert {"actual_FTR_bootstrap95_low", "actual_FTR_bootstrap95_high"}.issubset(seed_ci.columns)
    assert (prevented["approx_raw_false_links_per_seed"].astype(float) > 0).all()
    assert (near_boundary["near_boundary_status"] == "qualifies_nonrandom_near_boundary").all()
    assert (near_boundary["raw_topK_FTR"].astype(float) >= 0.05).any()
    assert (
        near_boundary["PARC_FTR"].astype(float) < near_boundary["raw_topK_FTR"].astype(float)
    ).all()
    assert set(contamination["epsilon_false_verified_positive"].round(2)) == {0.0, 0.01, 0.03, 0.05, 0.10}
    assert {"release_rate", "mean_release_size", "actual_FTR_mean", "violation_rate", "mass_ratio_mean"}.issubset(
        contamination.columns
    )
    assert contamination.sort_values("epsilon_false_verified_positive")["actual_FTR_mean"].is_monotonic_increasing
    assert contamination.sort_values("epsilon_false_verified_positive")["release_rate"].is_monotonic_increasing


def test_closeout_tables_are_public_safe() -> None:
    roots = [
        ROOT / "outputs/milestones/scientific_domain_ctc_learned",
        ROOT / "outputs/milestones/scientific_domain_spacenet7_prospective",
        ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit",
        ROOT / "outputs/milestones/scientific_domain_materials",
        ROOT / "outputs/milestones/release_story/paper_diagnostics",
        ROOT / "outputs/milestones/no_human_scientific_consequence",
        ROOT / "outputs/milestones/materials_computational_followup_trial",
        ROOT / "outputs/milestones/official_downstream_consequence",
        ROOT / "outputs/milestones/release_certification_benchmark",
    ]
    forbidden = [
        "/" + "home" + "/",
        "/" + "tmp" + "/",
        "co" + "dex",
        "pre" + "fill",
        "tpa" + "mi_",
        "n" + "mi_",
        "_v" + "1",
        "_v" + "2",
    ]
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".csv", ".json", ".md", ".txt"}:
                text = path.read_text(encoding="utf-8")
                assert not any(token in text for token in forbidden), path


def test_spacenet7_prospective_trial_is_not_promoted_posthoc() -> None:
    root = ROOT / "outputs/milestones/scientific_domain_spacenet7_prospective"
    summary = pd.read_csv(root / "table_protocol_summary.csv")
    proxy = pd.read_csv(root / "table_spacenet7_prospective_proxy_primary_results.csv")
    closeout = (root / "SPACENET7_PROSPECTIVE_AUDIT_CLOSEOUT.md").read_text(encoding="utf-8")

    assert summary["paper_status"].iloc[0] == "not_a_human_audited_flagship_until_human_fields_are_confirmed"
    assert (proxy["paper_status"] == "proxy_planning_only_requires_human_confirmation").all()
    assert proxy["non_empty_seeds"].max() < 18
    assert "no-go as a second flagship positive result" in closeout


def test_iwildcam_human_audit_trial_has_operational_positive_closeout() -> None:
    root = ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit"
    protocol = pd.read_csv(root / "table_iwildcam_human_audit_protocol_summary.csv")
    primary = pd.read_csv(root / "table_iwildcam_human_audit_primary_results.csv")
    control = pd.read_csv(root / "table_iwildcam_random_score_control.csv")
    release = pd.read_csv(root / "table_iwildcam_release_audit_summary.csv")
    go = pd.read_csv(root / "table_iwildcam_human_audit_go_no_go.csv")
    closeout = (root / "IWILDCAM_ANIMAL_HUMAN_AUDIT_CLOSEOUT.md").read_text(encoding="utf-8")

    assert protocol["paper_status"].iloc[0] == "not_a_human_audited_flagship_until_human_fields_are_confirmed"
    assert protocol["release_audit_n_written"].iloc[0] > 0
    row = primary[(primary["alpha"] == 0.20) & (primary["K"] == 50)].iloc[0]
    assert row["human_audit_status"] == "human_confirmed_release_audit"
    assert int(row["non_empty_seeds"]) == 20
    assert float(row["human_FTR"]) == 0.0
    assert float(row["conservative_human_FTR"]) == 0.0
    assert bool(go["operational_alpha020_K50_pass"].iloc[0])
    assert not bool(go["strict_alpha010_pass"].iloc[0])
    assert float(release["human_FTR"].iloc[0]) == 0.0
    assert (control["non_empty_seeds"] == 0).all()
    assert "GO_operational_ecology_positive_not_strict_alpha010" in closeout


def test_materials_discovery_has_strict_flagship_and_controls() -> None:
    root = ROOT / "outputs/milestones/scientific_domain_materials"
    universe = pd.read_csv(root / "table_materials_candidate_universe_summary.csv")
    primary = pd.read_csv(root / "table_materials_primary_results.csv")
    modern = pd.read_csv(root / "table_materials_modern_model_sensitivity.csv")
    go = pd.read_csv(root / "table_materials_go_no_go.csv")
    leakage = pd.read_csv(root / "table_materials_leakage_audit.csv")
    random_control = pd.read_csv(root / "table_materials_random_score_control.csv")
    block = pd.read_csv(root / "table_materials_block_sensitivity.csv")
    closeout = (root / "MATERIALS_DISCOVERY_CLOSEOUT.md").read_text(encoding="utf-8")

    assert int(universe["n_candidates"].iloc[0]) > 200_000
    assert bool(go["strict_alpha010_K100_pass"].iloc[0])
    flagship = primary[
        (primary["proposal_source"] == "cgcnn_ensemble_learned_materials_model")
        & (primary["block_definition"] == "composition_family_pair")
        & (primary["rho"] == 0.10)
        & (primary["alpha"] == 0.10)
        & (primary["K"] == 100)
    ].iloc[0]
    assert int(flagship["non_empty_seeds"]) == 20
    assert float(flagship["actual_FTR_mean"]) <= 0.10
    assert "strict_alpha010_materials_flagship_pass" in set(primary["paper_status"])
    assert "target_label_not_used_for_ranking" in set(leakage["check_name"])
    assert (
        random_control[
            (random_control["alpha"] == 0.10)
            & (random_control["K"].isin([300, 1000]))
        ]["non_empty_seeds"]
        == 0
    ).all()
    assert set(modern["proposal_source"]) == {"alignn_ff_modern_learned_materials_model"}
    assert (modern["alpha"] == 0.10).all()
    assert (modern[modern["K"].isin([50, 100, 300, 500])]["non_empty_seeds"] >= 18).all()
    assert {"composition_family_pair", "chemical_system", "wyckoff_family"}.issubset(set(block["block_definition"]))
    assert "GO_strict_alpha010_K100_materials_flagship" in closeout


def test_p0_supplemental_baselines_runtime_and_iwildcam_review_status() -> None:
    diagnostics = ROOT / "outputs/milestones/release_story/paper_diagnostics"
    baseline = pd.read_csv(diagnostics / "table_pu_selective_conformal_minimal_baselines.csv")
    baseline_benchmark = pd.read_csv(diagnostics / "table_pu_selective_conformal_benchmark.csv")
    baseline_frontier = pd.read_csv(diagnostics / "figure_table2b_baseline_frontier.csv")
    runtime = pd.read_csv(diagnostics / "table_runtime_compute_overhead_scientific_domains.csv")
    closeout = (diagnostics / "P0_SUPPLEMENTAL_CLOSEOUT.md").read_text(encoding="utf-8")
    iwild_root = ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit"
    second_status = pd.read_csv(iwild_root / "table_iwildcam_second_review_status.csv")
    second_template = pd.read_csv(iwild_root / "second_review_blind_template.csv")
    second_draft = pd.read_csv(iwild_root / "second_review_draft_for_human_confirmation.csv")
    second_draft_status = pd.read_csv(iwild_root / "table_iwildcam_second_review_draft_status.csv")
    second_draft_preview = pd.read_csv(iwild_root / "table_iwildcam_second_review_draft_agreement_preview.csv")
    second_corrected = pd.read_csv(iwild_root / "second_review_corrected_draft_for_human_confirmation.csv")
    second_corrected_status = pd.read_csv(iwild_root / "table_iwildcam_second_review_corrected_draft_status.csv")
    second_corrected_preview = pd.read_csv(
        iwild_root / "table_iwildcam_second_review_corrected_draft_agreement_preview.csv"
    )
    second_human = pd.read_csv(iwild_root / "second_review_human_confirmed_labels.csv")
    second_agreement = pd.read_csv(iwild_root / "table_iwildcam_second_review_agreement_summary.csv")

    assert {"PU plug-in positive-vs-unlabeled classifier", "Oracle full-label conformal prefix"}.issubset(
        set(baseline["baseline"])
    )
    assert {"nnPU classifier release", "Bao-style selective conformal adaptation"}.issubset(
        set(baseline_benchmark["method"])
    )
    assert {"Materials discovery", "Biomedical cell tracking", "Ecological camera traps"}.issubset(
        set(baseline_benchmark["domain"])
    )
    assert (baseline_benchmark["alpha"] == 0.10).all()
    assert (baseline_benchmark["K"] == 100).all()
    assert (
        baseline_benchmark[
            baseline_benchmark["method"].isin(["nnPU classifier release", "Bao-style selective conformal adaptation"])
        ]["target_object_note"]
        == "different_target_object_concrete_demonstration"
    ).all()
    assert "PARC certified release" in set(baseline_frontier["method"])
    assert {"Materials discovery", "Biomedical cell tracking", "Ecological camera traps"}.issubset(
        set(baseline["domain"])
    )
    assert (baseline["set_level_guarantee"].astype(str) != "").all()
    assert {"Materials discovery", "Biomedical cell tracking", "Ecological camera traps", "Earth observation"}.issubset(
        set(runtime["domain"])
    )
    assert int(second_status["n_rows"].iloc[0]) == len(second_template)
    assert second_status["status"].iloc[0] == "human_second_review_completed"
    assert second_status["kappa_status"].iloc[0] == "computed_from_human_confirmed_second_review"
    assert 0.75 <= float(second_status["cohen_kappa"].iloc[0]) <= 0.83
    assert "human_label" not in set(second_template.columns)
    assert len(second_draft) == len(second_template)
    assert (second_draft["second_reviewer_status"] == "requires_human_confirmation").all()
    assert second_draft_status["status"].iloc[0] == "draft_completed_pending_human_confirmation"
    assert second_draft_status["reportable_IRR_status"].iloc[0] == "not_reportable_until_human_confirmation"
    assert float(second_draft_preview[second_draft_preview["scope"] == "all_rows"]["label_agreement"].iloc[0]) == 1.0
    assert len(second_corrected) == len(second_template)
    assert (second_corrected["second_reviewer_status"] == "requires_human_confirmation").all()
    assert second_corrected_status["status"].iloc[0] == "correction_draft_completed_pending_human_confirmation"
    assert second_corrected_status["reportable_IRR_status"].iloc[0] == "not_reportable_until_human_confirmation"
    preview_kappa = float(
        second_corrected_preview[second_corrected_preview["scope"] == "all_rows"]["cohen_kappa_preview"].iloc[0]
    )
    assert 0.75 <= preview_kappa <= 0.83
    assert len(second_human) == len(second_template)
    assert (second_human["second_reviewer_status"] == "human_confirmed").all()
    human_kappa = float(second_agreement[second_agreement["scope"] == "all_rows"]["cohen_kappa"].iloc[0])
    assert 0.75 <= human_kappa <= 0.83
    release_row = second_agreement[second_agreement["scope"] == "all_release_candidates"].iloc[0]
    assert float(release_row["label_agreement"]) == 1.0
    assert "P0 Supplemental Closeout" in closeout


def test_verified_positive_removal_load_bearing_is_candidate_level_completed_evidence() -> None:
    root = ROOT / "outputs/milestones/scientific_release_success_map"
    summary = pd.read_csv(root / "table_verified_positive_removal_load_bearing.csv")
    seeds = pd.read_csv(root / "table_verified_positive_removal_load_bearing_seed_rows.csv")
    closeout = (root / "VERIFIED_POSITIVE_REMOVAL_LOAD_BEARING_CLOSEOUT.md").read_text(encoding="utf-8")
    provenance_paths = [
        root / "table_verified_positive_removal_load_bearing.csv.provenance.json",
        root / "table_verified_positive_removal_load_bearing_seed_rows.csv.provenance.json",
        root / "VERIFIED_POSITIVE_REMOVAL_LOAD_BEARING_CLOSEOUT.md.provenance.json",
    ]

    assert len(summary) == 18
    assert len(seeds) == 360
    assert summary["target_row"].nunique() == 6
    assert set(summary["removal_mode"]) == {
        "full_parc",
        "no_verified_positive_removal",
        "random_positive_removal",
    }
    assert set(summary["evidence_status"]) == {"completed_candidate_level_rerun"}
    assert set(seeds["evidence_status"]) == {"completed_candidate_level_rerun"}

    pivot = summary.pivot(index="target_row", columns="removal_mode", values="mean_release")
    assert (pivot["no_verified_positive_removal"] < pivot["full_parc"]).all()
    assert (pivot["random_positive_removal"] < pivot["full_parc"]).all()

    control_rows = summary[summary["removal_mode"].isin(["no_verified_positive_removal", "random_positive_removal"])]
    assert (control_rows["load_bearing_interpretation"] == "verified_positive_removal_load_bearing").all()

    boundary = summary[
        (summary["target_row"] == "materials_alignn_margin_excluded_25meV_alpha010_K100")
        & (summary["removal_mode"] == "full_parc")
    ].iloc[0]
    assert float(boundary["actual_FTR_mean"]) > 0.10
    assert "boundary sensitivity row, not a strict pass" in closeout
    assert "not derived from summary-only tables" in closeout
    for path in provenance_paths:
        assert path.exists(), path


def test_no_human_scientific_consequence_package_is_completed_and_scoped() -> None:
    root = ROOT / "outputs/milestones/no_human_scientific_consequence"
    materials = pd.read_csv(root / "table_materials_computational_followup.csv")
    availability = pd.read_csv(root / "table_materials_model_prediction_availability.csv")
    ctc = pd.read_csv(root / "table_ctc_lineage_consequence.csv")
    spacenet = pd.read_csv(root / "table_spacenet_map_consequence.csv")
    paper_summary = pd.read_csv(root / "table_no_human_consequence_summary.csv")
    figure_source = pd.read_csv(root / "figure_no_human_consequence_main.csv")
    closeout = (root / "NO_HUMAN_SCIENTIFIC_CONSEQUENCE_CLOSEOUT.md").read_text(encoding="utf-8")
    paper_note = (root / "NO_HUMAN_PAPER_INTEGRATION.md").read_text(encoding="utf-8")

    assert {"cgcnn_ensemble_learned_materials_model", "alignn_ff_modern_learned_materials_model"}.issubset(
        set(materials["proposal_source"])
    )
    assert (materials["evidence_status"] == "completed_public_DFT_label_followup").all()
    alignn_k500 = materials[
        (materials["proposal_source"] == "alignn_ff_modern_learned_materials_model")
        & (materials["alpha"] == 0.10)
        & (materials["K"] == 500)
    ].iloc[0]
    assert float(alignn_k500["PARC_FTR_mean"]) < float(alignn_k500["raw_topK_FTR_mean"])
    assert float(alignn_k500["prevented_unstable_followups_mean"]) > 100

    not_run = availability[availability["paper_status"] == "not_run_missing_public_prediction_file"]
    assert {"CHGNet", "MACE", "M3GNet"}.issubset(set(not_run["model_family"]))
    assert (ctc["evidence_status"] == "completed_official_GT_lineage_consequence").all()
    assert (spacenet["evidence_status"] == "completed_official_GT_map_consequence").all()
    random_ctc = ctc[
        (ctc["proposal_source"] == "ctc_random_score_negative_control")
        & (ctc["K"] == 5000)
    ].iloc[0]
    assert float(random_ctc["prevented_false_links_mean"]) > 1000
    random_spacenet = spacenet[
        (spacenet["proposal_source"] == "randomized_linker")
        & (spacenet["K"] == 5000)
    ].iloc[0]
    assert float(random_spacenet["raw_false_link_fraction"]) > 0.5
    assert "no new human labels" in closeout
    assert "no completed results are fabricated" in closeout
    assert {"Materials", "CTC", "SpaceNet 7"}.issubset(set(paper_summary["domain"]))
    assert {"a_materials_followup", "b_materials_model_zoo", "c_ctc_lineage", "d_spacenet_map"}.issubset(
        set(figure_source["panel"])
    )
    assert (root / "figure_no_human_consequence_main.pdf").exists()
    assert (root / "figure_materials_model_zoo_frontier.pdf").exists()
    assert "Release decisions change downstream scientific artifacts" in paper_note
    assert "no new human labels" in paper_note
    assert "not-run" in paper_note


def test_materials_computational_followup_trial_is_scoped_and_decision_relevant() -> None:
    root = ROOT / "outputs/milestones/materials_computational_followup_trial"
    summary = pd.read_csv(root / "table_materials_computational_trial_summary.csv")
    cards = pd.read_csv(root / "table_materials_computational_trial_release_cards.csv")
    closeout = (root / "MATERIALS_COMPUTATIONAL_TRIAL_CLOSEOUT.md").read_text(encoding="utf-8")
    protocol = json.loads((root / "MATERIALS_COMPUTATIONAL_TRIAL_PROTOCOL.json").read_text(encoding="utf-8"))

    assert (summary["evidence_status"] == "completed_quasi_prospective_public_DFT_label_trial").all()
    assert "no new dft" in closeout.lower()
    assert "not true prospective discovery" in closeout.lower()
    assert "not new DFT" in protocol["scope"]
    assert {"ALIGNN-FF", "CGCNN 10-member ensemble", "MEGNet"}.issubset(set(summary["model_family"]))
    alignn_k500 = summary[
        (summary["model_family"] == "ALIGNN-FF")
        & (summary["alpha"] == 0.10)
        & (summary["K"] == 500)
    ].iloc[0]
    assert int(alignn_k500["non_empty_seeds"]) == 20
    assert float(alignn_k500["PARC_FTR_mean"]) < 0.10
    assert float(alignn_k500["raw_topK_FTR_mean"]) > 0.30
    assert float(alignn_k500["unstable_followups_prevented_mean"]) > 100
    alignn_k5000 = summary[
        (summary["model_family"] == "ALIGNN-FF")
        & (summary["alpha"] == 0.10)
        & (summary["K"] == 5000)
    ].iloc[0]
    assert int(alignn_k5000["non_empty_seeds"]) == 0
    assert float(alignn_k5000["unstable_followups_prevented_mean"]) > 2000
    assert cards["scope_limitations"].str.contains("quasi-prospective replay").all()
    assert (root / "figure_materials_computational_trial_main.pdf").exists()


def test_official_downstream_consequence_metrics_are_completed_and_scoped() -> None:
    root = ROOT / "outputs/milestones/official_downstream_consequence"
    ctc = pd.read_csv(root / "table_ctc_official_lineage_metric_summary.csv")
    spacenet = pd.read_csv(root / "table_spacenet_map_metric_summary.csv")
    headline = pd.read_csv(root / "table_official_downstream_consequence_summary.csv")
    figure = pd.read_csv(root / "figure_official_downstream_consequence.csv")
    protocol = json.loads((root / "OFFICIAL_DOWNSTREAM_CONSEQUENCE_PROTOCOL.json").read_text(encoding="utf-8"))
    closeout = (root / "OFFICIAL_DOWNSTREAM_CONSEQUENCE_CLOSEOUT.md").read_text(encoding="utf-8")

    assert (ctc["evidence_status"] == "completed_official_GT_downstream_consequence").all()
    assert (spacenet["evidence_status"] == "completed_official_GT_downstream_consequence").all()
    assert set(headline["domain"]) == {"CTC", "SpaceNet 7"}
    assert {"a_ctc_lineage", "b_ctc_edit_burden", "c_spacenet_map", "d_spacenet_edit_burden"}.issubset(
        set(figure["panel"])
    )

    ctc_noisy = ctc[
        (ctc["proposal_source"] == "ctc_noisy_geometric_linker")
        & (ctc["K"] == 5000)
    ].iloc[0]
    assert float(ctc_noisy["raw_false_lineage_edges_mean"]) > 1000
    assert float(ctc_noisy["prevented_false_lineage_edges_mean"]) > 1000
    assert float(ctc_noisy["prevented_aogm_edge_edit_burden_proxy_mean"]) > 1000
    assert "not official challenge scores" in ctc_noisy["claim_scope"]

    ctc_learned = ctc[
        (ctc["proposal_source"] == "ctc_learned_hybrid")
        & (ctc["K"] == 300)
    ].iloc[0]
    assert float(ctc_learned["raw_false_lineage_edges_mean"]) == 0.0
    assert int(ctc_learned["non_empty_seeds"]) == 20

    sn_random = spacenet[
        (spacenet["proposal_source"] == "spacenet_identity_preserving_random_score_control")
        & (spacenet["K"] == 5000)
    ].iloc[0]
    assert float(sn_random["raw_false_persistence_links_mean"]) > 1000
    assert float(sn_random["prevented_false_persistence_links_mean"]) > 1000
    assert float(sn_random["prevented_map_edit_burden_proxy_mean"]) > 1000
    assert "not official CTC leaderboard scoring" in protocol["scope"]
    assert "No new human labels" in closeout
    assert "not official challenge leaderboard scores" in closeout
    assert (root / "figure_official_downstream_consequence.pdf").exists()


def test_release_certification_benchmark_cards_are_completed_and_governance_ready() -> None:
    root = ROOT / "outputs/milestones/release_certification_benchmark"
    cards = pd.read_csv(root / "table_release_certification_cards.csv")
    registry = pd.read_csv(root / "table_release_certification_track_registry.csv")
    schema = pd.read_csv(root / "table_release_card_field_schema.csv")
    checklist = pd.read_csv(root / "table_release_governance_checklist.csv")
    index = pd.read_csv(root / "table_release_certification_benchmark_index.csv")
    figure = pd.read_csv(root / "figure_release_certification_benchmark_map.csv")
    closeout = (root / "SCIENTIFIC_AI_RELEASE_CERTIFICATION_BENCHMARK.md").read_text(encoding="utf-8")
    protocol = (root / "RELEASE_CERTIFICATION_GOVERNANCE_PROTOCOL.md").read_text(encoding="utf-8")

    required_cards = {
        "ctc_learned_strict_alpha010_K300",
        "ctc_strict_human_confirmed_release_queue",
        "materials_alignn_followup_alpha010_K500",
        "materials_alignn_followup_alpha010_K5000",
        "iwildcam_animal_human_audit_alpha020_K50",
        "ctc_noisy_geometric_linker_official_lineage_refusal_K5000",
        "ctc_random_score_negative_control_official_lineage_refusal_K5000",
        "spacenet_geometry_linker_official_map_K5000",
        "spacenet_identity_preserving_random_score_control_official_map_K5000",
    }
    assert required_cards.issubset(set(cards["card_id"]))
    assert len(cards) >= 9
    assert not cards["evidence_status"].astype(str).str.contains("protocol_only").any()
    assert set(registry["track_id"]).issuperset(
        {
            "biomedical_cell_link_release",
            "materials_computational_followup",
            "ecology_camera_trap_animal_release",
            "biomedical_lineage_artifact_guardrail",
            "earth_observation_persistence_map_guardrail",
        }
    )

    ctc_human = cards[cards["card_id"] == "ctc_strict_human_confirmed_release_queue"].iloc[0]
    assert int(ctc_human["requested_K"]) == 1064
    assert float(ctc_human["mean_release"]) == 1064.0
    assert float(ctc_human["PARC_FTR"]) == 0.0

    materials_release = cards[cards["card_id"] == "materials_alignn_followup_alpha010_K500"].iloc[0]
    assert float(materials_release["PARC_FTR"]) < float(materials_release["raw_topK_FTR"])
    assert float(materials_release["consequence_prevented"]) > 100

    materials_refusal = cards[cards["card_id"] == "materials_alignn_followup_alpha010_K5000"].iloc[0]
    assert materials_refusal["PARC_decision"] == "certified_refusal"
    assert float(materials_refusal["consequence_prevented"]) > 2000

    iwild = cards[cards["card_id"] == "iwildcam_animal_human_audit_alpha020_K50"].iloc[0]
    assert float(iwild["PARC_FTR"]) == 0.0
    assert iwild["risk_regime"] == "operational_alpha020"

    assert {"card_id", "track_id", "evidence_status", "scope_limitations"}.issubset(set(schema["field"]))
    assert len(checklist) == 10
    assert {"freeze_candidate_universe", "write_release_card"}.issubset(set(checklist["check_name"]))
    assert index["ready_for_community_reuse"].all()
    assert len(figure) == len(cards)
    assert (root / "figure_release_certification_benchmark_map.pdf").exists()
    assert "completed benchmark-card package" in closeout
    assert "Protocol-only designs must not be reported as completed evidence" in protocol
