from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "materials_source_discordance_stress_test"


def test_materials_external_sources_are_negative_diagnostics() -> None:
    stress = pd.read_csv(MILESTONE / "table_materials_external_source_stress_summary.csv")

    assert {"OQMD public API", "alex-mp v20 local public snapshot"}.issubset(set(stress["source"]))
    assert stress["not_primary_positive_validation"].astype(bool).all()
    assert set(stress["claim_status"]) == {"completed_negative_diagnostic"}
    assert set(stress["main_text_role"]) == {"extended_data_stress_test"}
    assert stress["formula_only_excluded"].astype(bool).all()


def test_alex_mp_discordance_is_not_hidden() -> None:
    stress = pd.read_csv(MILESTONE / "table_materials_external_source_stress_summary.csv")
    alex = stress[stress["source"] == "alex-mp v20 local public snapshot"].iloc[0]

    assert int(alex["exact_matched_n"]) >= 200
    assert float(alex["PARC_matched_FTR"]) > float(alex["alpha"])
    assert float(alex["WBM_external_discordance"]) > 0.5
