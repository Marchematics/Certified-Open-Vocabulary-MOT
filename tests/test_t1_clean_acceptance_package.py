from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "t1_clean_acceptance_package"


def test_t1_outputs_exist() -> None:
    required = {
        "table_t1_baseline_frontier_summary.csv",
        "figure_t1_empirical_baseline_frontier_source.csv",
        "table_t1_baseline_family_coverage.csv",
        "table_t1_materials_validation_go_no_go.csv",
        "table_t1_clean_acceptance_lead_numbers.csv",
        "T1_CLEAN_ACCEPTANCE_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (MILESTONE / name).exists()]
    assert not missing


def test_materials_validation_routes_are_not_promoted() -> None:
    validation = pd.read_csv(MILESTONE / "table_t1_materials_validation_go_no_go.csv")
    assert not validation.empty
    assert not validation["completed_positive_result"].astype(bool).any()
    joined = " ".join(validation["claim_boundary"].astype(str)).lower()
    assert "not positive independent validation" in joined
    assert "no prospective materials discovery claim" in joined


def test_empirical_baseline_frontier_has_required_families() -> None:
    coverage = pd.read_csv(MILESTONE / "table_t1_baseline_family_coverage.csv")
    required = {
        "raw top-K",
        "raw top-R",
        "fixed threshold",
        "calibrated threshold",
        "split conformal candidate threshold",
        "post-filter e-value",
        "e-BH-style",
        "nnPU classifier release",
        "PARC",
    }
    present = set(coverage[coverage["has_empirical_row"].astype(bool)]["method_family"])
    assert required.issubset(present)


def test_only_parc_has_full_release_certificate() -> None:
    frontier = pd.read_csv(MILESTONE / "table_t1_baseline_frontier_summary.csv")
    full = frontier[frontier["has_full_release_certificate"].astype(bool)]
    assert not full.empty
    assert set(full["method_family"]) == {"PARC"}
    non_parc = frontier[~frontier["method_family"].eq("PARC")]
    assert not non_parc["has_full_release_certificate"].astype(bool).any()


def test_baseline_frontier_contains_visual_and_materials_panels() -> None:
    figure = pd.read_csv(MILESTONE / "figure_t1_empirical_baseline_frontier_source.csv")
    panels = set(figure["panel"])
    assert "visual_full_baseline_matrix" in panels
    assert "materials_public_dft_baseline_frontier" in panels
    assert "materials_ALIGNN_fixed_budget_utility" in panels


def test_materials_alignn_lead_numbers_are_scoped() -> None:
    leads = pd.read_csv(MILESTONE / "table_t1_clean_acceptance_lead_numbers.csv")
    k500 = leads[leads["lead_id"].eq("materials_ALIGNN_K500_fixed_budget")].iloc[0]
    assert "raw top-K FTR 0.327" in k500["lead_number"]
    assert "PARC FTR 0.048" in k500["lead_number"]
    assert "raw top-R matched FTR 0.048" in k500["lead_number"]
    assert "fixed-budget utility" in k500["claim_boundary"]
    assert len(str(k500["source_sha256"])) == 64


def test_closeout_forbids_t1_materials_overclaim() -> None:
    text = (MILESTONE / "T1_CLEAN_ACCEPTANCE_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "Materials independent/prospective validation remains unavailable" in text
    assert "A3 remains outside positive evidence" in text
