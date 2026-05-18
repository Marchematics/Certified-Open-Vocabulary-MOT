from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "mattergen_parc_prospective_dft_followup"
RUN = MILESTONE / "A3_QE_LOCAL_RUN"


def test_a3_qe_local_run_has_inputs_for_frozen_package() -> None:
    manifest = pd.read_csv(RUN / "qe_job_manifest.csv")
    inputs = sorted((RUN / "qe_inputs").glob("*/pw.vc-relax.in"))
    pseudo = pd.read_csv(RUN / "table_qe_pseudopotential_map.csv")

    assert len(manifest) == 100
    assert len(inputs) == 100
    assert int(manifest["arm"].eq("PARC-release-full").sum()) == 75
    assert int(manifest["arm"].eq("raw_top100_extra_tail").sum()) == 25
    assert manifest["selected_before_DFT_outcome"].astype(bool).all()
    assert not manifest["outcome_available"].astype(bool).any()
    assert not manifest["completed_positive_result"].astype(bool).any()
    assert manifest["qe_input_path"].map(lambda p: (ROOT / p).exists()).all()
    assert len(pseudo) == 70
    assert pseudo["pseudo_sha256"].astype(str).str.len().eq(64).all()


def test_a3_qe_local_run_claim_boundary_and_launch_scripts() -> None:
    status = pd.read_csv(RUN / "QE_ENVIRONMENT_STATUS.csv")
    protocol = (RUN / "QE_LOCAL_RUN_PROTOCOL.md").read_text(encoding="utf-8")
    manifest = (RUN / "MANIFEST_SHA256.txt").read_text(encoding="utf-8")

    assert status.loc[0, "claim_scope"] == "environment_and_input_deck_only_not_DFT_evidence"
    assert not bool(status.loc[0, "outcomes_present"])
    assert "not DFT evidence" in protocol
    assert "Prospective materials discovery claims remain forbidden" in protocol
    assert "run_qe_job.sh" in manifest
    assert "launch_parc_release_tmux.sh" in manifest


def test_a3_qe_local_run_does_not_change_frozen_selection_or_package() -> None:
    package = pd.read_csv(MILESTONE / "A3_DFT_RUN_PACKAGE" / "package_job_manifest.csv")
    qe = pd.read_csv(RUN / "qe_job_manifest.csv")
    selection_path = MILESTONE / "selection_frozen_v4.csv"

    assert set(qe["dft_job_id"].astype(str)) == set(package["dft_job_id"].astype(str))
    assert selection_path.exists()
    assert "selection_frozen_v4.csv" not in (RUN / "MANIFEST_SHA256.txt").read_text(encoding="utf-8")
