from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
HEADLINE = ROOT / "outputs" / "milestones" / "audit_budget_release_frontier_headline"
EXTENDED = ROOT / "outputs" / "milestones" / "audit_budget_release_frontier_extended"


def test_audit_budget_headline_outputs_exist() -> None:
    required = {
        "table_audit_budget_transition_primary.csv",
        "table_audit_policy_efficiency.csv",
        "table_audit_budget_frontier_lead_numbers.csv",
        "figure_audit_budget_transition_source.csv",
        "AUDIT_BUDGET_FRONTIER_HEADLINE_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (HEADLINE / name).exists()]
    assert not missing
    assert (EXTENDED / "table_audit_budget_frontier_summary.csv").exists()


def test_audit_budget_headline_roles_are_scoped() -> None:
    primary = pd.read_csv(HEADLINE / "table_audit_budget_transition_primary.csv")
    roles = dict(zip(primary["target_row"], primary["manuscript_role"]))
    assert roles["ctc_learned_strict_alpha010_K100"] == "strict_seed_stable_headline_candidate"
    assert roles["ctc_learned_strict_alpha010_K300"] == "strict_seed_stable_headline_candidate"
    assert roles["materials_alignn_exact_stable_alpha010_K300"] == "mean_operating_boundary_secondary"
    assert roles["materials_alignn_exact_stable_alpha010_K500"] == "mean_operating_boundary_secondary"
    assert roles["materials_cgcnn_exact_stable_alpha010_K100"] == "calibration_check_not_headline"


def test_ctc_strict_transition_has_random_comparator() -> None:
    primary = pd.read_csv(HEADLINE / "table_audit_budget_transition_primary.csv")
    ctc = primary[primary["target_row"].str.contains("ctc_learned")]
    assert (ctc["top_score_first_strict_budget"].astype(float) == 0.005).all()
    assert (ctc["random_first_strict_budget"].astype(float) == 1.0).all()
    assert set(ctc["top_score_vs_random_efficiency_gain"]) == {"200.0x"}


def test_materials_rows_are_not_strict_seed_stable_headlines() -> None:
    primary = pd.read_csv(HEADLINE / "table_audit_budget_transition_primary.csv")
    materials = primary[primary["target_row"].str.contains("materials_alignn")]
    assert materials["top_score_first_strict_budget"].isna().all()
    assert (materials["top_score_first_mean_operating_budget"].astype(float) == 0.005).all()
    assert (materials["top_score_alpha_violation_rate_at_mean_operating"].astype(float) > 0).all()
    text = (HEADLINE / "AUDIT_BUDGET_FRONTIER_HEADLINE_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "boundary/secondary, not strict headline" in text
    assert "do not support prospective materials-discovery wording" in text
