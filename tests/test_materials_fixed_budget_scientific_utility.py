import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "materials_fixed_budget_scientific_utility"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_materials_fixed_budget_lead_numbers_include_source_hashes() -> None:
    lead = pd.read_csv(MILESTONE / "table_materials_fixed_budget_lead_numbers.csv")

    assert not lead.empty
    assert lead["source_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()
    assert lead["protocol_family_member"].astype(bool).all()

    for source_table, source_hash in lead[["source_table", "source_sha256"]].drop_duplicates().itertuples(index=False):
        assert sha256_file(ROOT / source_table) == source_hash


def test_alignn_fixed_budget_headline_rows_are_public_label_utility() -> None:
    lead = pd.read_csv(MILESTONE / "table_materials_fixed_budget_lead_numbers.csv")
    rows = lead[
        lead["result_id"].isin(
            {
                "materials_alignn_ff_modern_learned_materials_model_alpha0.1_K300",
                "materials_alignn_ff_modern_learned_materials_model_alpha0.1_K500",
            }
        )
    ]

    assert len(rows) == 2
    assert set(rows["manuscript_role"]) == {"primary_headline"}
    assert (rows["prevented_unstable_followups_mean"].astype(float) > 0).all()
    assert (rows["PARC_FTR_mean"].astype(float) <= 0.10).all()
    assert rows["claim_scope"].astype(str).str.contains("not prospective discovery").all()


def test_cgcnn_k100_is_calibration_check_not_headline() -> None:
    lead = pd.read_csv(MILESTONE / "table_materials_fixed_budget_lead_numbers.csv")
    cgcnn = lead[lead["result_id"].eq("materials_cgcnn_ensemble_learned_materials_model_alpha0.1_K100")]

    assert len(cgcnn) == 1
    assert cgcnn["manuscript_role"].iloc[0] == "calibration_check"

