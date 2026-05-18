from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "mattergen_parc_prospective_dft_followup"


def test_a3_v4_formal_gate_counts_and_scope() -> None:
    provenance = pd.read_json(MILESTONE / "generation_provenance.json", typ="series")
    formal = pd.read_csv(MILESTONE / "table_public_label_exclusion_formal.csv")
    strict = pd.read_csv(MILESTONE / "candidate_universe_strict_public_label_free.csv")
    hits = pd.read_csv(MILESTONE / "table_structure_match_hits.csv")

    assert int(provenance["raw_generated_cif_count"]) == 5000
    assert int(provenance["scored_candidate_count"]) >= 4000
    assert len(formal) >= 4000
    assert len(strict) >= 1000
    assert hits["structure_match_public"].astype(bool).sum() > 0
    assert formal["formal_public_sources_unavailable"].astype(str).str.contains("OQMD_structure_index").all()


def test_a3_v4_formula_only_tags_are_not_exclusions() -> None:
    formal = pd.read_csv(MILESTONE / "table_public_label_exclusion_formal.csv")
    tagged_but_kept = formal[
        formal["same_formula_known_public_alex_mp"].astype(bool)
        & ~formal["structure_match_public"].astype(bool)
        & formal["eligible_for_formal_selection"].astype(bool)
    ]
    assert not tagged_but_kept.empty
    assert tagged_but_kept["public_label_exclusion_status"].eq("available_source_strict_public_label_free").all()


def test_a3_v4_selection_and_manifest_are_release_only_pre_outcome() -> None:
    selection = pd.read_csv(MILESTONE / "selection_frozen_v4.csv")
    jobs = pd.read_csv(MILESTONE / "dft_job_manifest_v4.csv")
    gate = pd.read_csv(MILESTONE / "table_phase29_go_no_go.csv")

    assert not selection.empty
    assert len(jobs) == 40
    assert set(jobs["arm"]) == {"PARC-release"}
    assert jobs["selected_before_DFT_outcome"].astype(bool).all()
    assert not jobs["outcome_available"].astype(bool).any()
    assert jobs["evidence_status"].astype(str).str.contains("release_only_pilot").all()
    assert gate["completed_positive_result"].astype(bool).sum() == 0
    assert "pilot_go_release_only_no_raw_only_comparator" in set(gate["status"])


def test_a3_v4_claim_language_forbids_positive_discovery() -> None:
    closeout = (MILESTONE / "A3_V4_FORMAL_SELECTION_GATE_CLOSEOUT.md").read_text(encoding="utf-8")
    claim_table = (ROOT / "docs" / "claim_table.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "not DFT evidence" in closeout
    assert "No prospective materials discovery claim is made" in closeout
    assert "release-only" in claim_table
    assert "no positive prospective materials result is claimed" in readme
