from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE62 = ROOT / "outputs/milestones/ncs_phase62_full_calibration_mlip_evalues"


def test_phase62_outputs_exist() -> None:
    expected = {
        "FULL_CALIBRATION_MLIP_EVALUE_PROTOCOL.md",
        "table_full_calibration_score_inventory.csv",
        "table_mace_full_calibration_scores.csv",
        "table_parc_m_full_calibration_results.csv",
        "table_parc_m_full_calibration_candidate_level.csv",
        "table_parc_m_full_calibration_gate_audit.csv",
        "figure_parc_m_full_calibration_inputs.csv",
        "NCS_PHASE62_FULL_CALIBRATION_MLIP_EVALUES.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE62 / name).exists()]


def test_phase62_inventory_has_full_calibration_sources() -> None:
    inventory = pd.read_csv(PHASE62 / "table_full_calibration_score_inventory.csv")
    source_rows = inventory[inventory["status"].eq("available_full_calibration_subset")]
    assert set(source_rows["source"]) == {"CHGNet", "MACE-MP"}
    assert source_rows["target_overlap_excluded"].eq(32).all()
    assert source_rows["full_calibration_rows_after_target_exclusion"].eq(5765).all()
    assert source_rows["scored_rows"].eq(5765).all()

    diagnostics = inventory[inventory["source"].isin(["CHGNet", "MACE-MP"]) & inventory["target_scored_rows"].notna()]
    assert diagnostics["target_scored_rows"].eq(1892).all()
    assert diagnostics["null_calibration_blocks"].gt(5000).all()


def test_phase62_results_are_fullcal_sources_but_not_headline() -> None:
    results = pd.read_csv(PHASE62 / "table_parc_m_full_calibration_results.csv")
    for k in [300, 500]:
        subset = results[results["K"].eq(k)].set_index("method")
        assert subset.loc["CHGNet-fullcal-only", "release_size"] == 0
        assert subset.loc["MACE-fullcal-only", "release_size"] == 0
        best = subset[subset.index.str.contains("fullcal")].sort_values("t1_FTR").dropna(subset=["t1_FTR"]).iloc[0]
        assert best["release_size"] >= 100
        assert best["t1_FTR"] < subset.loc["PARC original release", "t1_FTR"]
        assert "CHGNet_and_MACE_full_calibration_sources_available" in best["theorem_grade_source_status"]
        assert "not_DFT_evidence" in best["evidence_scope"]
        assert "not_prospective_discovery" in best["evidence_scope"]


def test_phase62_gate_audit_resolves_source_blocker_but_blocks_headline() -> None:
    gate = pd.read_csv(PHASE62 / "table_parc_m_full_calibration_gate_audit.csv")
    for k in [300, 500]:
        subset = gate[gate["K"].eq(k)].set_index("gate")
        assert subset.loc["CHGNet_full_calibration_evalues_available", "status"] == "PASS"
        assert subset.loc["MACE_full_calibration_evalues_available", "status"] == "PASS"
        assert subset.loc["best_fullcal_release_nontrivial_ge_100", "status"] == "PASS"
        assert subset.loc["best_fullcal_t1_improvement_ge_0p05", "status"] == "FAIL"
        assert subset.loc["headline_method_upgrade_allowed", "status"] == "FAIL"
    assert gate[gate["gate"].eq("best_fullcal_t1_improvement_ge_0p03")]["status"].tolist() == ["FAIL", "PASS"]


def test_phase62_closeout_and_ledger_forbid_overclaims() -> None:
    closeout = (PHASE62 / "NCS_PHASE62_FULL_CALIBRATION_MLIP_EVALUES.md").read_text(encoding="utf-8")
    for phrase in [
        "not DFT evidence",
        "not a current-MP t1 alpha certificate",
        "not a prospective materials discovery claim",
    ]:
        assert phrase in closeout
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("M-PARCM-FULLCAL-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "partial"
    assert "do_not_claim_t1_alpha_control" in row.iloc[0]["overclaim_guardrail"]


def test_phase62_reproduce_target_runs_from_cache() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase62-full-calibration-mlip-evalues"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "wrote outputs/milestones/ncs_phase62_full_calibration_mlip_evalues" in result.stdout
