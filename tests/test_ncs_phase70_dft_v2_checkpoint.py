from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase70_dft_v2_checkpoint"


def test_phase70_outputs_are_execution_checkpoint_not_outcome_claims() -> None:
    expected = {
        "table_dft_v2_blinded_execution_status.csv",
        "table_dft_v2_execution_checkpoint_summary.csv",
        "table_dft_v2_completed_energy_extract.csv",
        "table_dft_v2_quarantined_arm_failure_checkpoint.csv",
        "table_dft_v2_outcome_readiness.csv",
        "DFT_V2_CHECKPOINT.md",
    }
    assert expected.issubset({p.name for p in OUT.iterdir()})
    status = pd.read_csv(OUT / "table_dft_v2_blinded_execution_status.csv")
    assert not status["e_above_hull_available"].astype(bool).any()
    assert not status["stable_exact_available"].astype(bool).any()
    assert status["claim_status"].str.contains("not_stability_outcome").all()


def test_phase70_summary_reports_failure_rate_without_claiming_gate_pass() -> None:
    summary = pd.read_csv(OUT / "table_dft_v2_execution_checkpoint_summary.csv").iloc[0]
    assert int(summary["total_manifest_jobs"]) == 360
    assert int(summary["finished_jobs"]) >= 1
    assert float(summary["workflow_gate_threshold"]) == 0.10
    assert not bool(summary["e_above_hull_outcomes_available"])
    assert not bool(summary["stable_exact_outcomes_available"])
    assert "no_claim_ready_DFT_signal" in summary["checkpoint_interpretation"]


def test_phase70_completed_energy_extract_has_no_hull_fields() -> None:
    energies = pd.read_csv(OUT / "table_dft_v2_completed_energy_extract.csv")
    if len(energies):
        assert energies["execution_status"].eq("completed").all()
        assert energies["final_energy_per_atom_eV"].notna().all()
        assert not energies["stable_exact_available"].astype(bool).any()


def test_phase70_readiness_requires_reference_hull_postprocessing() -> None:
    readiness = pd.read_csv(OUT / "table_dft_v2_outcome_readiness.csv")
    blocked = readiness[readiness["outcome_field"].isin(["e_above_hull_ev_per_atom", "stable_exact"])]
    assert not blocked["available_at_checkpoint"].astype(bool).any()
    assert blocked["blocker_or_source"].str.contains("reference_hull|e_above_hull", regex=True).all()


def test_phase70_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase70-dft-v2-checkpoint"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase70_dft_v2_checkpoint" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase70_dft_v2_checkpoint"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

