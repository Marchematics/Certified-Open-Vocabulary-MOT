from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "mattergen_parc_prospective_dft_followup"


def test_phase29b_addendum_is_pre_outcome_and_does_not_modify_selection_contract() -> None:
    addendum = pd.read_csv(MILESTONE / "dft_job_manifest_v4_addendum.csv")
    summary = pd.read_csv(MILESTONE / "table_phase29b_dft_manifest_addendum_summary.csv")
    selection = pd.read_csv(MILESTONE / "selection_frozen_v4.csv")

    assert not addendum.empty
    assert "selection_frozen_v4_sha256" in addendum.columns
    assert addendum["selected_before_DFT_outcome"].astype(bool).all()
    assert not addendum["outcome_available"].astype(bool).any()
    assert addendum["outcome_file"].fillna("").eq("").all()
    assert addendum["evidence_status"].eq("pre_outcome_manifest_addendum_not_DFT_evidence").all()
    assert "selection_frozen_v4_unmodified_input" in set(summary["status"])
    assert int(summary.loc[summary["gate"].eq("selection_integrity"), "n_rows"].iloc[0]) == len(selection)


def test_phase29b_full_release_and_raw_topr_are_identical_and_scoped() -> None:
    addendum = pd.read_csv(MILESTONE / "dft_job_manifest_v4_addendum.csv")
    summary = pd.read_csv(MILESTONE / "table_phase29b_dft_manifest_addendum_summary.csv")

    release = addendum[addendum["arm"].eq("PARC-release-full")]
    raw_topr = addendum[addendum["arm"].eq("raw_topR_matched")]
    raw_only = addendum[addendum["arm"].eq("raw_only_rejected_tail")]

    assert len(release) == 75
    assert len(raw_topr) == len(release)
    assert set(raw_topr["candidate_id"]) == set(release["candidate_id"])
    assert raw_only.empty
    assert "exported_but_identical_to_full_release" in set(summary["status"])
    assert "absent_no_raw_only_tail" in set(summary["status"])
    assert summary["completed_positive_result"].astype(bool).sum() == 0


def test_phase29b_claim_language_forbids_positive_a3_evidence() -> None:
    closeout = (MILESTONE / "A3_V4_DFT_MANIFEST_ADDENDUM_CLOSEOUT.md").read_text(encoding="utf-8")
    claim_table = (ROOT / "docs" / "claim_table.md").read_text(encoding="utf-8")

    assert "This is not DFT evidence" in closeout
    assert "not prospective materials discovery evidence" in closeout
    assert "raw_topR is identical" in claim_table
    assert "no DFT outcome is claimed" in claim_table
