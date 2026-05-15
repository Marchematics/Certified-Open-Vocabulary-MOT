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

    panel_text = " ".join(
        " ".join(map(str, row)) for row in panel.astype(object).to_numpy()
    )
    assert "CTC learned-hybrid" in panel_text
    assert "SpaceNet7 real audit" in panel_text
    assert "certified_refusal" in panel_text or "human_audit_certified_refusal" in panel_text
    assert {"actual_FTR_bootstrap95_low", "actual_FTR_bootstrap95_high"}.issubset(seed_ci.columns)
    assert (prevented["approx_raw_false_links_per_seed"].astype(float) > 0).all()


def test_closeout_tables_are_public_safe() -> None:
    roots = [
        ROOT / "outputs/milestones/scientific_domain_ctc_learned",
        ROOT / "outputs/milestones/scientific_domain_spacenet7_prospective",
        ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit",
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


def test_iwildcam_human_audit_trial_is_pending_human_confirmation() -> None:
    root = ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit"
    protocol = pd.read_csv(root / "table_iwildcam_human_audit_protocol_summary.csv")
    proxy = pd.read_csv(root / "table_iwildcam_human_audit_proxy_primary_results.csv")
    control = pd.read_csv(root / "table_iwildcam_random_score_control.csv")
    closeout = (root / "IWILDCAM_ANIMAL_HUMAN_AUDIT_CLOSEOUT.md").read_text(encoding="utf-8")

    assert protocol["paper_status"].iloc[0] == "not_a_human_audited_flagship_until_human_fields_are_confirmed"
    assert protocol["release_audit_n_written"].iloc[0] > 0
    assert (proxy["human_audit_status"] == "requires_human_confirmation").all()
    assert proxy["non_empty_seeds"].max() >= 18
    assert (control["non_empty_seeds"] == 0).all()
    assert "must not be\nreported as human-audited FTR" in closeout
