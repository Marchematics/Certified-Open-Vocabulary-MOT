from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs/milestones/materials_queue_source_uncertainty_overlay"


def test_materials_queue_overlay_files_exist() -> None:
    expected = {
        "table_materials_queue_overlay_candidate_rows.csv",
        "table_materials_queue_overlay_summary.csv",
        "table_materials_queue_overlay_lead_contrasts.csv",
        "table_materials_queue_reconstruction_seed_rows.csv",
        "table_materials_queue_overlay_claim_boundary.csv",
        "MATERIALS_QUEUE_SOURCE_UNCERTAINTY_OVERLAY.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in expected if not (MILESTONE / name).exists()]
    assert not missing


def test_overlay_uses_only_exact_structure_matches_for_alex_metrics() -> None:
    rows = pd.read_csv(MILESTONE / "table_materials_queue_overlay_candidate_rows.csv")
    exact = rows[rows["included_in_alex_exact_metrics"].astype(bool)]
    non_exact = rows[~rows["included_in_alex_exact_metrics"].astype(bool)]
    assert not exact.empty
    assert set(exact["match_confidence"]) == {"exact_structure_match"}
    assert "formula_only_no_structure_match" in set(non_exact["match_confidence"])
    assert not non_exact["source_discordant_exact"].astype(bool).any()


def test_overlay_summary_is_candidate_level_diagnostic_for_alignn_k300_k500() -> None:
    summary = pd.read_csv(MILESTONE / "table_materials_queue_overlay_summary.csv")
    assert set(summary["K"]) == {300, 500}
    assert {
        "raw_topK_requested_budget",
        "PARC_release",
        "raw_topR_matched_release_size",
        "raw_only_rejected_tail",
    }.issubset(set(summary["arm"]))
    assert set(summary["paper_role"]) == {"diagnostic_only_source_uncertainty_overlay"}
    assert not summary["formula_only_rows_used_for_FTR"].astype(bool).any()
    parc = summary[summary["arm"].eq("PARC_release")]
    assert (parc["mean_exact_matched_n"] > 0).all()
    assert (parc["mean_exact_match_coverage"] > 0).all()


def test_lead_contrasts_do_not_promote_alex_as_positive_validation() -> None:
    contrasts = pd.read_csv(MILESTONE / "table_materials_queue_overlay_lead_contrasts.csv")
    assert set(contrasts["K"]) == {300, 500}
    assert set(contrasts["interpretation"]) == {
        "candidate_level_overlay_diagnostic_not_independent_validation"
    }
    assert contrasts["PARC_alex_exact_FTR"].notna().all()
    assert contrasts["raw_alex_exact_FTR"].notna().all()


def test_claim_boundary_forbids_prospective_or_independent_validation_overclaim() -> None:
    boundary = pd.read_csv(MILESTONE / "table_materials_queue_overlay_claim_boundary.csv")
    text = (MILESTONE / "MATERIALS_QUEUE_SOURCE_UNCERTAINTY_OVERLAY.md").read_text(encoding="utf-8")
    assert "diagnostic_only_source_discordance_stress" in set(boundary["setting"])
    assert "prospective materials discovery" in text
    assert "not positive independent validation" in text
