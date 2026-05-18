from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "mattergen_parc_prospective_dft_followup"
PACKAGE = MILESTONE / "A3_DFT_RUN_PACKAGE"


def test_a3_dft_run_package_contains_expected_cifs_and_manifests() -> None:
    release_cifs = sorted((PACKAGE / "cifs" / "PARC-release-full").glob("*.cif"))
    extra_cifs = sorted((PACKAGE / "cifs" / "raw_top100_extra_tail").glob("*.cif"))
    release = pd.read_csv(PACKAGE / "manifests" / "PARC_release_full_manifest.csv")
    extra = pd.read_csv(PACKAGE / "manifests" / "raw_top100_extra_tail_manifest.csv")
    combined = pd.read_csv(PACKAGE / "package_job_manifest.csv")

    assert len(release_cifs) == 75
    assert len(extra_cifs) == 25
    assert len(release) == 75
    assert len(extra) == 25
    assert len(combined) == 100
    assert set(combined["arm"]) == {"PARC-release-full", "raw_top100_extra_tail"}
    assert combined["package_cif_sha256"].astype(str).str.len().eq(64).all()
    assert combined["package_cif_path"].map(lambda p: (PACKAGE / p).exists()).all()


def test_a3_dft_run_package_is_pre_outcome_and_keeps_claim_boundary() -> None:
    combined = pd.read_csv(PACKAGE / "package_job_manifest.csv")
    status = pd.read_csv(PACKAGE / "LOCAL_EXECUTION_STATUS.csv")
    readme = (PACKAGE / "README.md").read_text(encoding="utf-8")
    protocol = (PACKAGE / "DFT_PROTOCOL.md").read_text(encoding="utf-8")

    assert combined["completed_positive_result"].astype(bool).sum() == 0
    assert combined["claim_scope"].eq("DFT_execution_package_only_no_outcomes").all()
    assert status.loc[0, "claim_scope"] == "execution_package_only_not_DFT_evidence"
    assert "not DFT evidence" in protocol
    assert "does not support a prospective materials discovery claim" in readme


def test_a3_dft_run_package_has_package_hash_and_conservative_policy() -> None:
    package_hash = (PACKAGE / "PACKAGE_HASH.txt").read_text(encoding="utf-8")
    manifest = (PACKAGE / "MANIFEST_SHA256.txt").read_text(encoding="utf-8")
    settings = (PACKAGE / "SETTINGS_TEMPLATE.yaml").read_text(encoding="utf-8")
    outcome_template = pd.read_csv(PACKAGE / "DFT_OUTCOME_TEMPLATE.csv")

    assert "A3_DFT_RUN_PACKAGE manifest-content-sha256" in package_hash
    assert "DFT_PROTOCOL.md" in manifest
    assert "SETTINGS_TEMPLATE.yaml" in manifest
    assert "failed_DFT_counted_not_certified_stable" in settings or "not-certified-stable" in settings
    assert {"completed", "failed", "e_above_hull_ev_per_atom", "stable_exact"}.issubset(outcome_template.columns)


def test_a3_dft_run_package_does_not_modify_selection_source() -> None:
    combined = pd.read_csv(PACKAGE / "package_job_manifest.csv")
    selection_hashes = set(combined["selection_frozen_v4_sha256"].dropna().astype(str))
    if not selection_hashes:
        # Extra-tail-only rows still come through the phase29c manifest; release rows always include this hash.
        release = pd.read_csv(PACKAGE / "manifests" / "PARC_release_full_manifest.csv")
        selection_hashes = set(release["selection_frozen_v4_sha256"].dropna().astype(str))
    selection_path = MILESTONE / "selection_frozen_v4.csv"
    import hashlib

    digest = hashlib.sha256(selection_path.read_bytes()).hexdigest()
    assert selection_hashes == {digest}
