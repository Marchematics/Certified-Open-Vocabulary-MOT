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

    assert {"PU plug-in positive-vs-unlabeled classifier", "Oracle full-label conformal prefix"}.issubset(
        set(baseline["baseline"])
    )
    assert {"Materials discovery", "Biomedical cell tracking", "Ecological camera traps"}.issubset(
        set(baseline["domain"])
    )
    assert (baseline["set_level_guarantee"].astype(str) != "").all()
    assert {"Materials discovery", "Biomedical cell tracking", "Ecological camera traps", "Earth observation"}.issubset(
        set(runtime["domain"])
    )
    assert int(second_status["n_rows"].iloc[0]) == len(second_template)
    assert second_status["status"].iloc[0] == "requires_independent_second_review"
    assert second_status["kappa_status"].iloc[0] == "not_computed_until_second_reviewer_labels_exist"
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
    assert "P0 Supplemental Closeout" in closeout
