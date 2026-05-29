from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase74_risk_gated_recertification"


def test_phase74_outputs_exist_and_scope_guardrails() -> None:
    expected = {
        "table_risk_gated_filtered_universe.csv",
        "table_risk_gated_nullsuperset_recomputed.csv",
        "table_risk_gated_scs_results.csv",
        "table_risk_gated_full_grid.csv",
        "table_risk_gated_primary_row.csv",
        "table_risk_gated_bootstrap_ci.csv",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    text = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "denominator and e-values are recomputed after filtering",
        "no DFT evidence",
        "no prospective materials discovery",
        "no full current-MP alpha certificate",
    ]:
        assert phrase in text


def test_risk_gate_is_pre_parc_and_uses_no_t1_for_threshold() -> None:
    universe = pd.read_csv(OUT / "table_risk_gated_filtered_universe.csv")
    assert universe["filter_stage"].eq("pre_PARC_before_calibration_split").all()
    assert universe["threshold_source"].eq("risk_score_quantile_only_no_t1_labels").all()
    assert universe["denominator_recomputed_after_filter"].astype(bool).all()
    assert (universe["K_eff"] <= universe["K_original"]).all()
    assert universe["risk_score_missing_n"].gt(0).any()


def test_nullsuperset_and_evalues_are_recomputed_after_filter() -> None:
    nulls = pd.read_csv(OUT / "table_risk_gated_nullsuperset_recomputed.csv")
    assert nulls["denominator_recomputed_after_filter"].astype(bool).all()
    assert nulls["evalues_recomputed_after_filter"].astype(bool).all()
    assert nulls["nonempty_calibration_null_blocks"].ge(0).all()
    assert nulls["K_eff"].le(nulls["K_original"]).all()
    assert nulls["gamma"].notna().any()


def test_scs_threshold_uses_keff_and_full_grid_reports_no_go() -> None:
    seed_rows = pd.read_csv(OUT / "table_risk_gated_scs_results.csv")
    assert seed_rows["K_eff"].le(seed_rows["K_original"]).all()
    assert not seed_rows["risk_gate_uses_t1_labels"].astype(bool).any()
    assert not seed_rows["heldout_t1_used_for_selection"].astype(bool).any()
    released = seed_rows[seed_rows["release_size"] > 0]
    if len(released):
        expected = released["K_eff"] / (released["alpha"] * released["release_size"])
        assert (released["required_evalue_threshold"] - expected).abs().max() < 1e-9

    grid = pd.read_csv(OUT / "table_risk_gated_full_grid.csv")
    assert len(grid) == 64
    assert not grid["go_strong"].astype(bool).any()
    assert not grid["go_medium"].astype(bool).any()
    assert not grid["self_consistency_pass_any_seed"].astype(bool).any()
    assert grid["nonempty_seeds"].max() == 0


def test_primary_row_is_phase69_prior_no_go() -> None:
    primary = pd.read_csv(OUT / "table_risk_gated_primary_row.csv")
    assert len(primary) == 1
    row = primary.iloc[0]
    assert row["risk_model"] == "system_margin_distribution"
    assert int(row["K_original"]) == 300
    assert int(row["K_eff"]) == 128
    assert float(row["retain_fraction"]) == 0.4
    assert row["support_mode"] == "t1_10pct_support"
    assert int(row["nonempty_seeds"]) == 0
    assert not bool(row["claim_supported"])
    assert row["paper_role"] == "failed_gate_supplementary_diagnostic"


def test_phase74_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase74-risk-gated-recertification"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "completed_risk_gated_recertification_no_go" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase74_risk_gated_recertification"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
