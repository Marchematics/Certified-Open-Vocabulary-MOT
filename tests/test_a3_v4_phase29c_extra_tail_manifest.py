from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "mattergen_parc_prospective_dft_followup"


def test_phase29c_extra_tail_manifest_is_pre_outcome_and_has_25_rows() -> None:
    manifest = pd.read_csv(MILESTONE / "dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv")
    summary = pd.read_csv(MILESTONE / "table_phase29c_raw_top100_extra_tail_summary.csv")

    assert len(manifest) == 25
    assert set(manifest["arm"]) == {"raw_top100_extra_tail"}
    assert manifest["selected_before_DFT_outcome"].astype(bool).all()
    assert not manifest["outcome_available"].astype(bool).any()
    assert manifest["outcome_file"].fillna("").eq("").all()
    assert manifest["evidence_status"].eq("pre_outcome_phase29c_extra_tail_manifest_not_DFT_evidence").all()
    assert "frozen_pre_outcome" in set(summary["status"])
    assert summary["completed_positive_result"].astype(bool).sum() == 0


def test_phase29c_extra_tail_is_disjoint_from_release_and_uses_frozen_inputs() -> None:
    extra = pd.read_csv(MILESTONE / "dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv")
    addendum = pd.read_csv(MILESTONE / "dft_job_manifest_v4_addendum.csv")
    release_ids = set(addendum[addendum["arm"].eq("PARC-release-full")]["candidate_id"].astype(str))

    assert set(extra["candidate_id"].astype(str)).isdisjoint(release_ids)
    assert extra["formal_raw_score_rank"].min() == 76
    assert extra["formal_raw_score_rank"].max() == 100
    assert extra["construction_inputs"].str.contains("strict_public_label_free_universe").all()
    assert extra["selection_frozen_v4_sha256"].nunique() == 1


def test_phase29c_launch_status_is_not_fake_started() -> None:
    launch = pd.read_csv(MILESTONE / "table_phase29c_dft_launch_status.csv")
    closeout = (MILESTONE / "A3_V4_PHASE29C_RAW_TOP100_EXTRA_TAIL_CLOSEOUT.md").read_text(encoding="utf-8")

    assert launch.loc[0, "launch_target"] == "PARC-release-full"
    assert int(launch.loc[0, "requested_jobs"]) == 75
    assert launch.loc[0, "claim_scope"] == "launch_status_only_not_DFT_evidence"
    if str(launch.loc[0, "launch_status"]).startswith("blocked"):
        assert int(launch.loc[0, "processes_started"]) == 0
        assert "no DFT process was started" in closeout


def test_phase29c_claim_language_preserves_a3_boundary() -> None:
    claim_table = (ROOT / "docs" / "claim_table.md").read_text(encoding="utf-8")
    closeout = (MILESTONE / "A3_V4_PHASE29C_RAW_TOP100_EXTRA_TAIL_CLOSEOUT.md").read_text(encoding="utf-8")

    assert "no DFT outcome or prospective discovery claim is made" in claim_table
    assert "This is not DFT evidence" in closeout
    assert "no prospective DFT evidence" in closeout
