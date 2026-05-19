import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/mattergen_alignnff_preoutcome_scoring_snapshot"


def test_alignnff_preoutcome_snapshot_files_exist():
    required = [
        "candidate_scores_alignnff_4039.csv",
        "candidate_scores_alignnff_strict_public_label_free_2990.csv",
        "table_alignnff_rank_correlation.csv",
        "table_alignnff_topk_overlap.csv",
        "table_alignnff_release_tail_scores.csv",
        "table_alignnff_release_vs_tail_score_contrast.csv",
        "table_alignnff_preoutcome_score_status.csv",
        "provenance.json",
        "A3_ALIGNNFF_PREOUTCOME_SCORING_SNAPSHOT.md",
        "MANIFEST_SHA256.txt",
    ]
    missing = [name for name in required if not (OUT / name).exists()]
    assert not missing


def test_alignnff_scored_candidate_counts_and_statuses():
    all_scores = pd.read_csv(OUT / "candidate_scores_alignnff_4039.csv")
    strict = pd.read_csv(OUT / "candidate_scores_alignnff_strict_public_label_free_2990.csv")
    assert len(all_scores) == 4039
    assert len(strict) == 2990
    assert all_scores["score_status"].eq("scored").all()
    assert strict["score_status"].eq("scored").all()
    assert all_scores["outcome_available"].eq(False).all()
    assert strict["outcome_available"].eq(False).all()


def test_alignnff_release_tail_summary_is_75_plus_25():
    arms = pd.read_csv(OUT / "table_alignnff_release_tail_scores.csv")
    assert arms["snapshot_arm"].value_counts().to_dict() == {
        "PARC-release-full": 75,
        "raw_top100_extra_tail": 25,
    }
    assert arms["alignnff_score"].notna().all()


def test_alignnff_rank_and_overlap_diagnostics_include_alignnff():
    corr = pd.read_csv(OUT / "table_alignnff_rank_correlation.csv")
    pairs = set(zip(corr["score_a"], corr["score_b"]))
    assert ("consensus_score", "alignnff_score") in pairs
    assert ("chgnet_score", "alignnff_score") in pairs
    assert corr["evidence_status"].eq("completed_pre_outcome_scorer_diagnostic_not_DFT_evidence").all()

    overlap = pd.read_csv(OUT / "table_alignnff_topk_overlap.csv")
    assert set(overlap["K"]) == {25, 50, 75, 100, 300, 500}
    assert (overlap["score_b"].eq("alignnff_score") | overlap["score_a"].eq("alignnff_score")).any()


def test_alignnff_snapshot_is_not_dft_evidence():
    provenance = json.loads((OUT / "provenance.json").read_text())
    assert provenance["status"] == "completed_pre_outcome_scorer_diagnostic_not_DFT_evidence"
    assert provenance["no_dft_outcomes_used"] is True
    assert "selection_frozen_v4.csv" in provenance["does_not_modify"]

    closeout = (OUT / "A3_ALIGNNFF_PREOUTCOME_SCORING_SNAPSHOT.md").read_text()
    forbidden = ["prospective materials discovery claim", "DFT utility claim"]
    assert "not DFT evidence" in closeout
    assert "does not modify `selection_frozen_v4.csv`" in closeout
    for phrase in forbidden:
        assert phrase in closeout
