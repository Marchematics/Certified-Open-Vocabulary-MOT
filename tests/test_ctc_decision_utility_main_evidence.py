from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "ctc_decision_utility_main_evidence"


def test_ctc_decision_utility_has_strict_release_and_refusal_controls() -> None:
    utility = pd.read_csv(MILESTONE / "table_ctc_release_utility_primary.csv")

    strict = utility[utility["evidence_type"] == "strict_release"]
    assert {100, 300}.issubset(set(strict["K"].astype(int)))
    assert strict["raw_topK_comparator_present"].astype(bool).all()
    assert strict["heldout_FTR"].astype(float).max() == 0.0
    assert strict["non_empty_seeds"].astype(int).min() == 20

    controls = utility[utility["evidence_type"] == "certified_refusal_control"]
    assert not controls.empty
    assert controls["certified_refusal"].astype(bool).all()
    assert controls["false_links_avoided_mean"].astype(float).max() > 2000
    assert controls["raw_topK_FTR"].astype(float).max() > 0.5


def test_ctc_downstream_damage_table_contains_raw_vs_parc() -> None:
    damage = pd.read_csv(MILESTONE / "table_ctc_raw_vs_parc_downstream_damage.csv")
    required = {
        "raw_false_lineage_edges_mean",
        "PARC_false_lineage_edges_mean",
        "prevented_false_lineage_edges_mean",
        "raw_aogm_edge_edit_burden_proxy_mean",
        "PARC_aogm_edge_edit_burden_proxy_mean",
    }
    assert required.issubset(set(damage.columns))
