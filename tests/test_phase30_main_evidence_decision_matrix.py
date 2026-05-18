from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "main_evidence_hard_upgrade_phase30"


def test_phase30_decision_matrix_roles_are_scoped() -> None:
    matrix = pd.read_csv(MILESTONE / "table_main_evidence_decision_matrix.csv")

    assert "primary_main_evidence" in set(matrix["main_text_role"])
    assert "extended_data_stress_test" in set(matrix["main_text_role"])

    materials = matrix[matrix["domain"] == "materials_discovery"]
    external = materials[materials["evidence_block"].astype(str).str.contains("external-source")]
    assert not external.empty
    assert set(external["main_text_role"]) == {"extended_data_stress_test"}
    assert set(external["positive_or_negative"]) == {"negative_diagnostic"}

    a3 = matrix[matrix["evidence_block"].astype(str).str.contains("A3 MatterGen")]
    assert len(a3) == 1
    assert a3["main_text_role"].iloc[0] != "primary_main_evidence"
    assert a3["completed_status"].iloc[0] != "completed"

    assert not matrix["completed_status"].astype(str).str.contains("protocol_only").any()


def test_phase30_primary_rows_are_completed_non_a3() -> None:
    matrix = pd.read_csv(MILESTONE / "table_main_evidence_decision_matrix.csv")
    primary = matrix[matrix["main_text_role"] == "primary_main_evidence"]

    assert not primary.empty
    assert set(primary["completed_status"]) == {"completed"}
    assert not primary["evidence_block"].astype(str).str.contains("A3").any()
    assert not primary["domain"].eq("materials_discovery").any()
