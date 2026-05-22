from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "nmi_reviewer_p0_hardening"


def test_nmi_p0_hardening_outputs_exist() -> None:
    required = {
        "table_p0_reviewer_gap_action_matrix.csv",
        "table_human_audit_uncertainty_intervals.csv",
        "table_baseline_frontier_maintext_map.csv",
        "table_assumption_diagnostics_maintext_map.csv",
        "table_refusal_feasibility_attribution.csv",
        "NMI_REVIEWER_P0_HARDENING_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (MILESTONE / name).exists()]
    assert not missing


def test_p0_materials_positive_evidence_gap_is_not_overclaimed() -> None:
    p0 = pd.read_csv(MILESTONE / "table_p0_reviewer_gap_action_matrix.csv")
    p01 = p0[p0["p0_item"].eq("P0-1")].iloc[0]
    p02 = p0[p0["p0_item"].eq("P0-2")].iloc[0]
    assert p01["current_status"] == "not_completed_positive_evidence"
    assert "do not claim prospective materials discovery" in p01["manuscript_action"]
    assert p02["current_status"] == "completed_negative_or_diagnostic_only"
    assert "not validation success" in p02["manuscript_action"]


def test_audit_uncertainty_has_interval_upper_bounds() -> None:
    audit = pd.read_csv(MILESTONE / "table_human_audit_uncertainty_intervals.csv")
    assert {"clopper_pearson_upper95", "wilson_upper95", "jeffreys_upper95"}.issubset(audit.columns)
    assert (audit["n_audited"].astype(int) > 0).all()
    assert (audit["wilson_upper95"].astype(float) > 0).all()
    assert "zero-risk" in " ".join(audit["claim_boundary"].astype(str))


def test_baseline_frontier_marks_only_parc_as_full_certificate_object() -> None:
    baseline = pd.read_csv(MILESTONE / "table_baseline_frontier_maintext_map.csv")
    parc = baseline[baseline["method"].astype(str).str.contains("PARC")]
    assert not parc.empty
    assert set(parc["uses_null_superset"].astype(str).str.lower()) == {"true"}
    assert set(parc["uses_SCS_denominator"].astype(str).str.lower()) == {"true"}
    non_parc = baseline[~baseline["method"].astype(str).str.contains("PARC")]
    assert not non_parc["main_text_comparison_role"].eq("primary_method_set_level_certificate").any()


def test_refusal_attribution_does_not_blame_greedy_selector() -> None:
    refusal = pd.read_csv(MILESTONE / "table_refusal_feasibility_attribution.csv")
    assert (refusal["selector_power_limitation"].astype(str).str.lower() == "false").all()
    assert refusal["paper_interpretation"].astype(str).str.contains("evidence-mass|finite-resolution|mass", regex=True).any()
