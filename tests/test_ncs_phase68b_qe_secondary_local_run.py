from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE68B = ROOT / "outputs/milestones/ncs_phase68b_qe_secondary_launch"


def test_phase68b_static_outputs_exist_and_are_public_safe() -> None:
    expected = {
        "QE_SECONDARY_LOCAL_LAUNCH.md",
        "qe_secondary_job_manifest_summary.csv",
        "qe_secondary_launch_status.csv",
        "qe_secondary_pseudopotential_coverage.csv",
    }
    assert not [name for name in expected if not (PHASE68B / name).exists()]

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase68b_qe_secondary_launch"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_phase68b_launch_status_and_claim_scope() -> None:
    status = pd.read_csv(PHASE68B / "qe_secondary_launch_status.csv").iloc[0]
    assert status["tmux_session"] == "ncs68b_qe"
    assert status["launch_state"] in {"launched_in_tmux", "already_running_in_tmux"}
    assert status["input_ready_jobs"] == 360
    assert status["blocked_jobs"] == 0
    assert "not_primary_DFT_v2_validity_endpoint" in status["claim_scope"]
    assert "not_prospective_materials_discovery" in status["claim_scope"]
    assert "/home/waas" not in status.to_string()
    assert "/root/" not in status.to_string()


def test_phase68b_pseudopotential_coverage_is_complete_and_element_exact() -> None:
    coverage = pd.read_csv(PHASE68B / "qe_secondary_pseudopotential_coverage.csv").set_index("element")
    assert coverage["status"].eq("available").all()
    assert coverage.loc["F", "pseudo_file"].startswith("f_")
    assert coverage.loc["S", "pseudo_file"].startswith("s_")
    assert coverage.loc["Fe", "pseudo_file"].startswith("Fe")
    assert coverage.loc["Se", "pseudo_file"].startswith("Se")
    for element in ["Ac", "Np", "Pa", "Pu", "Th", "U"]:
        assert coverage.loc[element, "source"] == "downloaded_QE_upf_files"


def test_phase68b_ledger_forbids_overclaim() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("MAT-DFTV2-QE-SECONDARY-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "not_primary_DFT_v2_validity_endpoint" in row.iloc[0]["scope"]
    assert "do_not_claim_primary_DFT_endpoint" in row.iloc[0]["overclaim_guardrail"]
