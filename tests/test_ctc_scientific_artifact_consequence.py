import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "ctc_scientific_artifact_consequence"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_ctc_false_lineage_edges_table_has_source_hashes() -> None:
    table = pd.read_csv(MILESTONE / "table_ctc_false_lineage_edges_avoided.csv")

    assert not table.empty
    assert table["source_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()
    for source_table, source_hash in table[["source_table", "source_sha256"]].drop_duplicates().itertuples(index=False):
        assert sha256_file(ROOT / source_table) == source_hash


def test_ctc_strict_anchor_and_refusal_consequence_are_both_present() -> None:
    table = pd.read_csv(MILESTONE / "table_ctc_false_lineage_edges_avoided.csv")

    strict = table[(table["proposal_source"] == "ctc_learned_hybrid") & (table["K"].astype(int) == 300)]
    assert len(strict) == 1
    assert int(strict["non_empty_seeds"].iloc[0]) == 20
    assert float(strict["raw_false_lineage_edges_mean"].iloc[0]) == 0.0
    assert float(strict["PARC_false_lineage_edges_mean"].iloc[0]) == 0.0

    refusal = table[
        (table["proposal_source"] == "ctc_random_score_negative_control")
        & (table["K"].astype(int) == 300)
    ]
    assert len(refusal) == 1
    assert int(refusal["non_empty_seeds"].iloc[0]) == 0
    assert float(refusal["prevented_false_lineage_edges_mean"].iloc[0]) > 0


def test_ctc_lineage_graph_damage_has_claim_scope() -> None:
    table = pd.read_csv(MILESTONE / "table_ctc_lineage_graph_damage.csv")

    assert not table.empty
    assert "claim_scope" in table.columns
    assert table["claim_scope"].astype(str).str.contains("not official challenge scores").any()

