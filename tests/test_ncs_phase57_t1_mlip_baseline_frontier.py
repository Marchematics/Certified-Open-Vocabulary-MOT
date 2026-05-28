from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE57 = ROOT / "outputs/milestones/ncs_phase57_t1_mlip_baseline_frontier"


def test_phase57_outputs_exist() -> None:
    expected = {
        "table_t1_mlip_baseline_frontier.csv",
        "table_baseline_capability_t1_mlip.csv",
        "figure_t1_mlip_baseline_frontier_inputs.csv",
        "NCS_PHASE57_T1_MLIP_BASELINE_FRONTIER.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in expected if not (PHASE57 / name).exists()]
    assert not missing


def test_t1_mlip_baseline_frontier_contains_required_methods_and_fields() -> None:
    table = pd.read_csv(PHASE57 / "table_t1_mlip_baseline_frontier.csv")
    expected_methods = {
        "PARC",
        "raw top-K",
        "matched raw top-R",
        "fixed score threshold",
        "split conformal threshold",
        "post-filter e-value",
        "e-BH-style selection",
    }
    required = {
        "method",
        "release_size",
        "t0_FTR",
        "t1_FTR",
        "t1_raw_minus_method",
        "stable_to_unstable_drift",
        "MLIP_unstable_fraction",
        "can_refuse",
        "has_expected_FTR_certificate",
        "uses_one_sided_null_superset",
        "uses_denominator_self_consistency",
        "uses_compatibility",
        "matched_volume_boundary",
    }
    assert required.issubset(table.columns)
    assert set(table["K"]) == {300, 500}
    for k in [300, 500]:
        assert set(table[table["K"].eq(k)]["method"]) == expected_methods
    assert table["evidence_scope"].str.contains("not_matched_volume_ranking_improvement").all()


def test_parc_has_certificate_and_matched_raw_topr_preserves_boundary() -> None:
    table = pd.read_csv(PHASE57 / "table_t1_mlip_baseline_frontier.csv")
    for k in [300, 500]:
        subset = table[table["K"].eq(k)].set_index("method")
        parc = subset.loc["PARC"]
        raw = subset.loc["raw top-K"]
        raw_r = subset.loc["matched raw top-R"]
        assert bool(parc["has_expected_FTR_certificate"])
        assert bool(parc["uses_denominator_self_consistency"])
        assert bool(parc["uses_compatibility"])
        assert not bool(raw["has_expected_FTR_certificate"])
        assert not bool(raw_r["has_expected_FTR_certificate"])
        assert parc["release_size"] == raw_r["release_size"]
        assert abs(parc["t1_FTR"] - raw_r["t1_FTR"]) < 1e-12
        assert "not_deployable" in raw_r["matched_volume_boundary"]
        assert parc["t1_FTR"] < raw["t1_FTR"]
        assert parc["MLIP_unstable_fraction"] < raw["MLIP_unstable_fraction"]


def test_capability_table_marks_only_parc_as_full_release_certificate() -> None:
    capability = pd.read_csv(PHASE57 / "table_baseline_capability_t1_mlip.csv")
    parc = capability[capability["method"].eq("PARC")].iloc[0]
    assert bool(parc["has_expected_FTR_certificate"])
    assert bool(parc["uses_one_sided_null_superset"])
    assert bool(parc["uses_denominator_self_consistency"])
    assert bool(parc["uses_compatibility"])
    non_parc = capability[~capability["method"].eq("PARC")]
    assert not non_parc["has_expected_FTR_certificate"].astype(bool).any()


def test_phase57_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase57-t1-mlip-baseline-frontier"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "wrote outputs/milestones/ncs_phase57_t1_mlip_baseline_frontier" in result.stdout
