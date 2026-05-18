from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "materials_independent_dft_validation"


def test_oqmd_independent_validation_outputs_are_scoped() -> None:
    primary = pd.read_csv(MILESTONE / "table_independent_dft_primary_results.csv")
    matches = pd.read_csv(MILESTONE / "table_independent_dft_candidate_matches.csv")
    seeds = pd.read_csv(MILESTONE / "table_independent_dft_seed_rows.csv")

    row = primary.iloc[0]
    assert row["external_label_source"] == "OQMD public API"
    assert row["match_confidence"] == "exact_structure_match"
    assert "completed_independent_oqmd_exact_structure" in row["evidence_status"]
    assert "low_coverage" in row["evidence_status"]
    assert not bool(row["completed_positive_result"])
    assert float(row["coverage_of_independent_source"]) < 0.60

    assert {"exact_structure_match", "no_formula_match"}.issubset(set(matches["match_confidence"]))
    exact = matches[matches["match_confidence"] == "exact_structure_match"]
    assert not exact.empty
    assert exact["oqmd_entry_ids"].astype(str).str.len().gt(0).all()
    assert not seeds.empty


def test_oqmd_independent_validation_does_not_use_formula_only_for_ftr() -> None:
    sensitivity = pd.read_csv(MILESTONE / "table_independent_dft_match_confidence_sensitivity.csv")
    formula = sensitivity[sensitivity["match_confidence"] == "formula_only_no_structure_match"].iloc[0]
    exact = sensitivity[sensitivity["match_confidence"] == "exact_structure_match"].iloc[0]

    assert formula["role"] == "sensitivity_only"
    assert "not_used_for_independent_FTR" in formula["evidence_status"]
    assert "primary_if_coverage_sufficient" in exact["role"]
