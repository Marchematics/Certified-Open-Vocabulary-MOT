from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs/milestones/materials_temporal_mlip_audit"


def test_materials_temporal_mlip_outputs_exist() -> None:
    expected = {
        "MATERIALS_TEMPORAL_MLIP_AUDIT_CLOSEOUT.md",
        "table_temporal_hull_shift_audit.csv",
        "table_temporal_replay_lead_numbers.csv",
        "table_mlip_dense_audit_summary.csv",
        "table_mlip_rank_agreement.csv",
        "table_mlip_topk_overlap.csv",
        "table_mlip_release_tail_contrast.csv",
        "table_mlip_boundary_explanation.csv",
        "table_week1_4_go_no_go.csv",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in expected if not (MILESTONE / name).exists()]
    assert not missing


def test_temporal_gate_remains_no_go_without_t0_t1_snapshots() -> None:
    temporal = pd.read_csv(MILESTONE / "table_temporal_hull_shift_audit.csv")
    assert not temporal["completed_positive_result"].astype(bool).any()
    joined = " ".join(temporal["status"].astype(str).str.lower())
    assert "no_go_missing_timestamped_snapshots" in joined
    assert "not_evaluable_without_t0_t1_snapshots" in joined


def test_mlip_dense_audit_has_two_or_more_directional_support_models() -> None:
    mlip = pd.read_csv(MILESTONE / "table_mlip_dense_audit_summary.csv")
    assert {"CHGNet", "MACE-MP", "ALIGNN-FF"}.issubset(set(mlip["audit_model"]))
    assert mlip["directional_support"].astype(bool).sum() >= 3
    supported = mlip[mlip["directional_support"].astype(bool)]
    assert (supported["release_minus_tail_mean_delta"] > 0).all()
    assert (supported["release_minus_tail_median_delta"] > 0).all()
    assert supported["evidence_status"].str.contains("not_DFT_evidence", case=False).all()


def test_rank_agreement_records_mace_chgnet_high_and_alignn_distinct() -> None:
    rank = pd.read_csv(MILESTONE / "table_mlip_rank_agreement.csv")
    chg_mace = rank[
        rank["score_a"].eq("chgnet_score") & rank["score_b"].eq("mace_score")
    ].iloc[0]
    assert chg_mace["spearman"] > 0.9
    alignn_rows = rank[
        rank["score_a"].str.contains("alignnff", case=False, na=False)
        | rank["score_b"].str.contains("alignnff", case=False, na=False)
    ]
    assert not alignn_rows.empty
    assert (alignn_rows["agreement_interpretation"] == "moderate_or_model_distinct").any()


def test_boundary_explanation_is_source_level_not_validation() -> None:
    boundary = pd.read_csv(MILESTONE / "table_mlip_boundary_explanation.csv")
    text = " ".join(boundary.astype(str).agg(" ".join, axis=1)).lower()
    assert "not parc validation" in text
    assert "source_level_boundary_support_only" in text
    neither = boundary[boundary["diagnostic"].eq("neither_source_near_hull_25meV")].iloc[0]
    assert neither["discordant_n"] == 0


def test_week1_4_go_no_go_scope() -> None:
    gates = pd.read_csv(MILESTONE / "table_week1_4_go_no_go.csv")
    temporal_gate = gates[gates["gate"].eq("temporal_t0_t1_hull_shift")].iloc[0]
    assert temporal_gate["status"] == "NO_GO"
    mlip_gate = gates[gates["gate"].eq("two_or_more_MLIP_models_same_direction")].iloc[0]
    assert bool(mlip_gate["pass"])
    overall = gates[gates["gate"].eq("overall_week1_4_materials_temporal_mlip")].iloc[0]
    assert overall["status"] == "PARTIAL_PASS_MLIP_SUPPORT_TEMPORAL_NO_GO"
    assert not bool(overall["pass"])
    assert "no prospective" in overall["allowed_claim"].lower()


def test_source_hashes_are_recorded() -> None:
    for filename in [
        "table_temporal_hull_shift_audit.csv",
        "table_temporal_replay_lead_numbers.csv",
        "table_mlip_dense_audit_summary.csv",
        "table_mlip_rank_agreement.csv",
        "table_mlip_boundary_explanation.csv",
    ]:
        table = pd.read_csv(MILESTONE / filename)
        assert "source_sha256" in table.columns
        assert table["source_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all(), filename


def test_closeout_forbids_prospective_materials_claims() -> None:
    text = (MILESTONE / "MATERIALS_TEMPORAL_MLIP_AUDIT_CLOSEOUT.md").read_text(encoding="utf-8").lower()
    assert "no prospective materials-discovery claim" in text
    assert "not candidate-level a3 validation" in text
    assert "pre-outcome mlip scorer audit completed" in text
