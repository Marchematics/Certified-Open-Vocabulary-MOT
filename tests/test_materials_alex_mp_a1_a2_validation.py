from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "materials_alex_mp_a1_a2_validation"


def test_alex_mp_a1_a2_outputs_are_completed_but_not_positive() -> None:
    primary = pd.read_csv(MILESTONE / "table_alex_mp_a2_primary_results.csv")
    temporal = pd.read_csv(MILESTONE / "table_alex_mp_a1_temporal_external_snapshot_primary.csv")
    matches = pd.read_csv(MILESTONE / "table_alex_mp_a2_candidate_matches.csv")

    row = primary.iloc[0]
    assert row["external_label_source"] == "alex-mp v20 local public snapshot"
    assert row["match_confidence"] == "exact_structure_match"
    assert "completed_independent_alex_mp_exact_structure" in row["evidence_status"]
    assert not bool(row["completed_positive_result"])
    assert float(row["independent_FTR"]) > float(row["alpha"])
    assert float(row["raw_topK_coverage_of_independent_source"]) > 0.30
    assert int(row["n_unique_exact_structure_matches"]) >= 200

    assert temporal["trial"].iloc[0] == "A1_quasi_temporal_external_snapshot_replay"
    assert temporal["temporal_claim_scope"].astype(str).str.contains("not a full timestamped").all()
    assert "exact_structure_match" in set(matches["match_confidence"])


def test_alex_mp_formula_only_rows_are_not_used_for_ftr() -> None:
    sensitivity = pd.read_csv(MILESTONE / "table_alex_mp_match_confidence_sensitivity.csv")
    formula = sensitivity[sensitivity["match_confidence"] == "formula_only_no_structure_match"].iloc[0]
    exact = sensitivity[sensitivity["match_confidence"] == "exact_structure_match"].iloc[0]

    assert formula["role"] == "coverage_diagnostic_not_used_for_FTR"
    assert "not_used_for_independent_FTR" in formula["evidence_status"]
    assert exact["role"] == "primary_A2_and_A1_exact_match_subset"


def test_claim_table_records_alex_mp_boundary() -> None:
    text = (ROOT / "docs" / "claim_table.md").read_text(encoding="utf-8")
    assert "Materials A1/A2 alex-mp external-snapshot validation" in text
    assert "not a positive independent validation" in text
    assert "Formula-only matches are excluded" in text
