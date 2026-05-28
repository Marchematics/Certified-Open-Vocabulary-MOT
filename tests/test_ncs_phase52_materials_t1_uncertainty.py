from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE52 = ROOT / "outputs/milestones/ncs_phase52_materials_t1_uncertainty"


def test_phase52_outputs_exist() -> None:
    expected = {
        "table_t1_bootstrap_ci.csv",
        "table_t1_randomization_tests.csv",
        "NCS_PHASE52_MATERIALS_T1_UNCERTAINTY.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE52 / name).exists()]


def test_bootstrap_ci_contains_requested_metrics_and_claim_boundary() -> None:
    ci = pd.read_csv(PHASE52 / "table_t1_bootstrap_ci.csv")
    assert set(ci["K"]) == {300, 500}
    assert {
        "FTR_t1_raw_minus_PARC",
        "stable_to_unstable_raw_minus_PARC",
        "DCR",
        "MLIP_consensus_raw_minus_PARC",
    }.issubset(set(ci["metric"]))
    computed = ci[ci["metric_status"].eq("computed")]
    assert not computed.empty
    assert (computed["n_bootstrap"] == 2000).all()
    assert (computed["ci_low_95"] <= computed["estimate"]).all()
    assert (computed["estimate"] <= computed["ci_high_95"]).all()
    blocked = ci[ci["metric"].eq("MLIP_consensus_raw_minus_PARC")]
    assert blocked["metric_status"].str.contains("not_evaluable_no_CHGNet_MACE", regex=False).all()
    assert ci["evidence_scope"].str.contains("not_strict_alpha_temporal_certificate", regex=False).all()


def test_randomization_tests_compare_required_controls() -> None:
    tests = pd.read_csv(PHASE52 / "table_t1_randomization_tests.csv")
    assert set(tests["K"]) == {300, 500}
    assert {
        "PARC_vs_full_raw_topK",
        "PARC_vs_matched_raw_topR",
        "PARC_vs_stratified_random_raw_topK_subset",
    } == set(tests["comparison"])
    assert tests["p_value_one_sided"].between(0, 1).all()
    assert tests["p_value_two_sided"].between(0, 1).all()
    assert (tests["n_permutations"] == 2000).all()
    matched = tests[tests["comparison"].eq("PARC_vs_matched_raw_topR")]
    assert (matched["observed_difference"].abs() < 1e-12).all()
