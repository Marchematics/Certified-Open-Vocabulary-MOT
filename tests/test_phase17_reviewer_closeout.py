from pathlib import Path

import pandas as pd

from parc_track.phase17 import run_phase17_reviewer_closeout


def test_phase17_reviewer_closeout_outputs():
    summary = run_phase17_reviewer_closeout()
    artifacts = {Path(p).name for p in summary["artifacts"]}
    assert "table_actual_ftr_validation.csv" in artifacts
    assert "table_tao_sensitivity_framing.csv" in artifacts
    assert "THEOREM1_MAIN_TEXT.md" in artifacts
    actual = pd.read_csv("outputs/milestones/reliability_fortress/paper_tables/table_actual_ftr_validation.csv")
    assert {"controlled_simulation_known_ground_truth", "real_data_release_set_audit_anchor"}.issubset(
        set(actual["validation_block"])
    )
    sim = actual[actual["validation_block"].eq("controlled_simulation_known_ground_truth")]
    assert sim.groupby("certified_risk_level_alpha")["seed"].nunique().min() == 100
    assert (sim["actual_FTR"] <= sim["certified_risk_level_alpha"] + 1e-12).all()
    tao = pd.read_csv("outputs/milestones/reliability_fortress/paper_tables/table_tao_sensitivity_framing.csv")
    positive = tao[(tao["certified_risk_level_alpha"].eq(0.2)) & (tao["M"].eq(150))]
    assert not positive.empty
    assert int(positive["nonempty_seeds"].iloc[0]) == 3
    challenge = pd.read_csv("outputs/milestones/reliability_fortress/audit_review/second_review_challenge_template_500.csv")
    leaked = {"label", "verified_positive_for_calibration", "review_label_v2"}.intersection(challenge.columns)
    assert not leaked
