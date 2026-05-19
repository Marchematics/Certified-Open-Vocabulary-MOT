from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CLEANUP = ROOT / "outputs" / "milestones" / "pre_release_repository_cleanup"


def git_ls_files() -> list[str]:
    output = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [line.strip() for line in output.splitlines() if line.strip()]


def test_cleanup_milestone_documents_removed_and_kept_artifacts() -> None:
    removed = pd.read_csv(CLEANUP / "table_pre_release_removed_artifacts.csv")
    kept = pd.read_csv(CLEANUP / "table_pre_release_kept_artifacts.csv")
    closeout = (CLEANUP / "PRE_RELEASE_REPOSITORY_CLEANUP.md").read_text(encoding="utf-8")

    assert {
        "legacy_internal_results",
        "generated_archive_packages",
        "ctc_prefill_package",
        "spacenet_prefill_sheets",
        "iwildcam_second_review_drafts",
        "prefill_draft_helper_scripts",
        "local_runtime_scratch",
    }.issubset(set(removed["artifact_group"]))
    assert {
        "ctc_final_audit",
        "iwildcam_final_audit",
        "spacenet_final_audit",
        "a3_formal_gate",
        "a3_runtime_outputs",
    }.issubset(set(kept["artifact_group"]))
    assert "does not create new evidence" in closeout
    assert "does not modify A3-v4 selection or DFT manifests" in closeout


def test_no_tracked_prefill_draft_or_legacy_artifacts_remain() -> None:
    tracked = git_ls_files()
    forbidden_substrings = [
        "outputs/milestones/legacy_core_results/",
        "outputs/milestones/ctc_strict_human_audit_prefill/",
        "outputs/spacenet7_real_audit/",
        "outputs/packages/",
        "ctc_strict_audit_private_key",
        "second_review_draft_for_human_confirmation",
        "second_review_corrected_draft_for_human_confirmation",
        "table_iwildcam_second_review_draft_",
        "table_iwildcam_second_review_corrected_draft_",
        "_review_prefill.csv",
        "raw_mattergen_candidates.csv",
        "generated_5k_",
        "public_label_free_pilot_4039",
        "candidate_scores_chgnet_smoke.csv",
        "candidate_scores_consensus_smoke.csv",
        "candidate_scores_mace_smoke.csv",
        "candidate_universe_public_label_free_smoke.csv",
        "table_mattergen_smoke_",
        "generality_reliability/candidate_universe.csv",
        "generality_reliability/candidate_nodes.csv",
        "generality_reliability/candidate_scores.csv",
        "lvvis_mask_certification/mask_shards/mask_nodes_shard0.csv",
        "lvvis_mask_certification/mask_shards/mask_nodes_shard1.csv",
        "lvvis_mask_certification/mask_shards/mask_nodes_shard2.csv",
        "lvvis_mask_certification/mask_shards/mask_nodes_shard3.csv",
        "A3_QE_LOCAL_RUN/pseudos/",
    ]
    offenders = [path for path in tracked if any(token in path for token in forbidden_substrings)]
    assert offenders == []


def test_runtime_outputs_are_ignored_not_tracked() -> None:
    tracked = git_ls_files()
    assert not any("/qe_outputs/" in path for path in tracked)
    assert not any(path.endswith("/CRASH") or path == "CRASH" for path in tracked)
    assert "input_tmp.in" not in tracked
    assert not any("__pycache__" in path or path.endswith(".pyc") for path in tracked)


def test_a3_claim_boundary_survives_cleanup() -> None:
    claim_text = (ROOT / "docs" / "claim_table.md").read_text(encoding="utf-8")
    scope_text = (ROOT / "docs" / "abstract_claim_scope.md").read_text(encoding="utf-8")

    assert "No DFT outcome or prospective discovery claim is made" in claim_text
    assert "Do not claim prospective materials discovery" in scope_text
    assert "dft_completed_n >= 25" in scope_text
