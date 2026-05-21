from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "materials_selection_conditional_discordance"


def test_selection_conditional_discordance_outputs_exist() -> None:
    required = [
        "table_selection_conditional_denominator.csv",
        "table_score_stratified_discordance.csv",
        "table_decile_discordance.csv",
        "table_top_decile_discordance.csv",
        "table_model_trend_tests.csv",
        "table_selection_conditional_go_no_go.csv",
        "SELECTION_CONDITIONAL_DISCORDANCE_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    ]
    for name in required:
        assert (MILESTONE / name).exists(), name


def test_full_snapshot_denominator_and_baseline_are_recorded() -> None:
    gate = pd.read_csv(MILESTONE / "table_selection_conditional_go_no_go.csv").iloc[0]

    assert gate["source_pair"] == "Materials_Project_vs_alex_mp_v20"
    assert int(gate["n_common"]) == 287
    assert 0.10 <= float(gate["baseline_discordance"]) <= 0.12
    assert gate["paper_role"] == "completed_go_no_go_diagnostic"


def test_hypothesis_b_is_not_promoted_after_no_go() -> None:
    gate = pd.read_csv(MILESTONE / "table_selection_conditional_go_no_go.csv").iloc[0]
    top = pd.read_csv(MILESTONE / "table_top_decile_discordance.csv")
    trend = pd.read_csv(MILESTONE / "table_model_trend_tests.csv")

    assert gate["go_no_go"] == "NO_GO_hypothesis_B_not_supported"
    assert int(gate["models_supporting_rule"]) == 0
    assert int(gate["models_top_decile_ge_0_30"]) == 0
    assert int(gate["models_top_decile_ge_2x_baseline"]) == 0
    assert set(top["model"]) == {"ALIGNN-FF", "CHGNet", "MACE-MP"}
    assert (top["top_decile_discordance"].astype(float) < 0.30).all()
    assert not trend["supports_high_score_amplification"].astype(bool).any()


def test_decile_rows_cover_all_models_without_claiming_positive_validation() -> None:
    deciles = pd.read_csv(MILESTONE / "table_decile_discordance.csv")
    assert set(deciles["model"]) == {"ALIGNN-FF", "CHGNet", "MACE-MP"}
    assert set(deciles["bin_family"]) == {"decile"}
    assert deciles.groupby("model").size().to_dict() == {
        "ALIGNN-FF": 10,
        "CHGNet": 10,
        "MACE-MP": 10,
    }
    assert set(deciles["paper_role"]) == {"selection_conditional_go_no_go_diagnostic"}
