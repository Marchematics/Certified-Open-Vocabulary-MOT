from pathlib import Path
import json
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE68 = ROOT / "outputs/milestones/ncs_phase68_dft_v2_pilot"


def test_phase68_outputs_exist() -> None:
    expected = {
        "DFT_OUTCOME_TEMPLATE.csv",
        "DFT_V2_PILOT_PREREGISTRATION.md",
        "DFT_V2_PROTOCOL.md",
        "LOCAL_EXECUTION_STATUS.csv",
        "MANIFEST_SHA256.txt",
        "NCS_PHASE68_DFT_V2_PILOT_CLOSEOUT.md",
        "PACKAGE_HASH.txt",
        "SETTINGS_TEMPLATE_MP_COMPATIBLE.yaml",
        "TRANSFER_PACKAGE_README.md",
        "dft_v2_analysis_arm_key.csv",
        "dft_v2_blinded_transfer_manifest.csv",
        "dft_v2_candidate_selection_manifest.csv",
        "provenance.json",
        "table_dft_v2_arm_feasibility.csv",
        "table_dft_v2_arm_summary.csv",
        "table_dft_v2_package_hashes.csv",
    }
    assert not [name for name in expected if not (PHASE68 / name).exists()]
    assert (PHASE68 / "cifs").is_dir()


def test_phase68_blinded_manifest_has_no_arm_labels_and_expected_jobs() -> None:
    transfer = pd.read_csv(PHASE68 / "dft_v2_blinded_transfer_manifest.csv")
    key = pd.read_csv(PHASE68 / "dft_v2_analysis_arm_key.csv")
    cifs = sorted((PHASE68 / "cifs").glob("*.cif"))

    assert len(transfer) == 360
    assert len(key) == 360
    assert len(cifs) == 360
    assert "dft_v2_arm" not in transfer.columns
    assert "candidate_id" not in transfer.columns
    assert "dft_v2_arm" in key.columns
    assert set(transfer["blinded_job_id"]) == set(key["blinded_job_id"])
    assert transfer["cif_path"].str.startswith("cifs/DFTV2-").all()


def test_phase68_arm_counts_and_feasibility_boundary() -> None:
    summary = pd.read_csv(PHASE68 / "table_dft_v2_arm_summary.csv").set_index("dft_v2_arm")
    assert summary.loc["parc_release_core", "n_jobs"] == 100
    assert summary.loc["parc_release_boundary_t1_false", "n_jobs"] == 60
    assert summary.loc["raw_only_extra_tail", "n_jobs"] == 150
    assert summary.loc["public_sanity_stable", "n_jobs"] == 25
    assert summary.loc["public_sanity_unstable", "n_jobs"] == 25

    feasibility = pd.read_csv(PHASE68 / "table_dft_v2_arm_feasibility.csv").set_index("arm")
    rawr = feasibility.loc["matched_raw_topR_nonoverlap"]
    assert rawr["selected_n"] == 0
    assert rawr["status"] == "not_available_raw_topR_coextensive_with_PARC_release"


def test_phase68_does_not_start_or_claim_dft_outcomes() -> None:
    local = pd.read_csv(PHASE68 / "LOCAL_EXECUTION_STATUS.csv").iloc[0]
    assert local["processes_started"] == 0
    assert local["claim_scope"] == "pre_outcome_package_only_not_DFT_evidence"

    closeout = (PHASE68 / "NCS_PHASE68_DFT_V2_PILOT_CLOSEOUT.md").read_text(encoding="utf-8")
    for phrase in [
        "pre_outcome_blinded_manifest_frozen",
        "does not produce DFT outcomes",
        "does not support prospective materials discovery",
        "does not alter A3 selection or manifests",
    ]:
        assert phrase in closeout

    outcome = pd.read_csv(PHASE68 / "DFT_OUTCOME_TEMPLATE.csv")
    assert outcome.empty


def test_phase68_provenance_and_ledger_guardrails() -> None:
    provenance = json.loads((PHASE68 / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "pre_outcome_blinded_manifest_frozen"
    assert provenance["jobs"] == 360
    assert provenance["blinding"]["executor_manifest_contains_arm_labels"] is False
    assert "do_not_claim_DFT_outcome" in provenance["overclaim_guardrails"]
    assert "do_not_claim_prospective_materials_discovery" in provenance["overclaim_guardrails"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("MAT-DFTV2-PILOT-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert row.iloc[0]["scope"] == "pre_outcome_package_only_not_DFT_evidence"
    assert "do_not_claim_DFT_outcome" in row.iloc[0]["overclaim_guardrail"]


def test_phase68_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase68-dft-v2-pilot"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase68_dft_v2_pilot" in result.stdout
