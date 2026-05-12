from __future__ import annotations

import tarfile
from pathlib import Path

import pandas as pd

from parc_track import phase13
from parc_track.phase13 import run_phase13_release_story


def _patch_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))
    monkeypatch.setattr(phase13, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(phase13, "RELIABILITY_DIR", tmp_path / "outputs/milestones/reliability_fortress")
    monkeypatch.setattr(phase13, "GENERALITY_DIR", tmp_path / "outputs/milestones/generality_reliability")
    monkeypatch.setattr(phase13, "LVVIS_DIR", tmp_path / "outputs/milestones/lvvis_certification")
    monkeypatch.setattr(phase13, "LVVIS_MASK_DIR", tmp_path / "outputs/milestones/lvvis_mask_certification")
    monkeypatch.setattr(phase13, "LEGACY_DIR", tmp_path / "outputs/milestones/legacy_core_results")
    monkeypatch.setattr(phase13, "PHASE13_DIR", tmp_path / "outputs/phase13_release_story")
    monkeypatch.setattr(phase13, "MILESTONE_DIR", tmp_path / "outputs/milestones/release_story")
    monkeypatch.setattr(phase13, "PACKAGE_PATH", tmp_path / "outputs/packages/release_story.tar.gz")


def _write_sources(root: Path) -> None:
    generality = root / "outputs/milestones/generality_reliability"
    reliability = root / "outputs/milestones/reliability_fortress"
    lvvis = root / "outputs/milestones/lvvis_certification"
    mask = root / "outputs/milestones/lvvis_mask_certification"
    legacy = root / "outputs/milestones/legacy_core_results"
    for path in (generality, reliability, lvvis, mask, legacy / "phase2h_first_real_nonempty", legacy / "phase4_third_generator_and_owlv2_audit"):
        path.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {"dataset": "LVIS", "detector": "GroundingDINO", "method": "parc", "alpha1": 0.1, "seed": 0, "M": 150, "released": 150, "UTR": 0.0, "conservative_FTR": 0.0, "mass_ratio": 1.2, "empty_reason": ""},
            {"dataset": "LVIS", "detector": "OWLv2", "method": "parc", "alpha1": 0.1, "seed": 0, "M": 150, "released": 0, "UTR": 0.0, "conservative_FTR": 0.0, "mass_ratio": 0.2, "empty_reason": "no_k_satisfies_uniform_self_consistency"},
        ]
    ).to_csv(generality / "table_lvis_detection_certification.csv", index=False)
    pd.DataFrame(
        [
            {"alpha1": 0.1, "seeds": 3, "released_mean": 150, "released_min": 150, "released_max": 150, "utr_mean": 0.01, "conservative_ftr_mean": 0.01, "margin_mean": 2.0},
        ]
    ).to_csv(lvvis / "table_lvvis_parc_summary.csv", index=False)
    pd.DataFrame(
        [
            {"method": "confidence_threshold", "alpha1": 0.1, "seed": 0, "released": 150, "utr": 0.2, "conservative_ftr_uncertain_and_unlabeled_false": 0.2},
            {"method": "greedy_score_no_risk", "alpha1": 0.1, "seed": 0, "released": 150, "utr": 0.25, "conservative_ftr_uncertain_and_unlabeled_false": 0.25},
            {"method": "parc_track_gamma_tuned_uniform_scs", "alpha1": 0.1, "seed": 0, "released": 150, "utr": 0.01, "conservative_ftr_uncertain_and_unlabeled_false": 0.01, "mass_ratio": 1.5},
        ]
    ).to_csv(lvvis / "table_baseline_expanded.csv", index=False)
    pd.DataFrame(
        [
            {"dataset": "LVVIS", "task": "mask", "alpha1": 0.1, "seed": 0, "candidate_budget_M": 150, "mask_iou_threshold": 0.5, "released": 150, "utr": 0.02, "conservative_ftr": 0.02, "best_mass_ratio": 1.4, "empty_reason": ""},
        ]
    ).to_csv(mask / "table_lvvis_mask_certification.csv", index=False)
    pd.DataFrame(
        [
            {"generator": "OWLv2", "dataset": "OVT-B", "alpha1": 0.1, "seed": 0, "released": 0, "UTR": 0.0, "conservative_FTR": 0.0, "mass_ratio": 0.2, "empty_reason": "no_k_satisfies_uniform_self_consistency"},
        ]
    ).to_csv(reliability / "table_blackbox_generator_certification.csv", index=False)
    pd.DataFrame(
        [
            {"tracker": "ovtb_baseline", "dataset": "ovtb", "method": "raw_tracker_topM", "alpha1": 0.1, "seed": 0, "released": 150, "utr": 0.4, "conservative_ftr_uncertain_and_unlabeled_false": 0.4},
            {"tracker": "ovtb_baseline", "dataset": "ovtb", "method": "parc_wrapped", "alpha1": 0.1, "seed": 0, "parc_release": 0, "mass_ratio": 0.3, "empty_reason": "no_k_satisfies_uniform_self_consistency"},
        ]
    ).to_csv(reliability / "table_published_tracker_certification.csv", index=False)
    pd.DataFrame(
        [
            {"dataset": "OVT-B", "video_id": "1", "path_id": "p_true", "label": "actually_true", "verified_positive_for_calibration": "yes", "score": 0.9},
            {"dataset": "OVT-B", "video_id": "2", "path_id": "p_unc", "label": "uncertain", "verified_positive_for_calibration": "no", "score": 0.8},
            {"dataset": "OVT-B", "video_id": "3", "path_id": "p_false", "label": "actually_false", "verified_positive_for_calibration": "no", "score": 0.7},
        ]
    ).to_csv(reliability / "audit_labels_2000_human_reviewed.csv", index=False)
    pd.DataFrame(
        [
            {"dataset": "OVT-B", "video_id": "4", "path_id": "p_rel", "query": "dog", "score": 0.95, "is_unmatched": "False", "montage_path": "/root/raw/should_not_leak.png"},
        ]
    ).to_csv(legacy / "phase2h_first_real_nonempty/released_tracks.csv", index=False)
    pd.DataFrame(
        [
            {"dataset": "OVT-B", "video_id": "5", "path_id": "p_owl", "query": "bird", "score": 0.88, "label": "actually_true", "montage_path": "outputs/montages/not_packaged.jpg"},
        ]
    ).to_csv(legacy / "phase4_third_generator_and_owlv2_audit/owlv2_top150_mini_audit_labels_with_montages.csv", index=False)


def test_release_story_freezes_public_safe_tables(tmp_path: Path, monkeypatch) -> None:
    _patch_roots(tmp_path, monkeypatch)
    _write_sources(tmp_path)

    summary = run_phase13_release_story()

    milestone = tmp_path / "outputs/milestones/release_story"
    assert summary["status"] == "completed"
    assert (milestone / "table_release_story_nontracking_positive.csv").exists()
    assert (milestone / "table_release_policy_value.csv").exists()
    assert (milestone / "figure_release_story_teaser_manifest.csv").exists()
    nontracking = pd.read_csv(milestone / "table_release_story_nontracking_positive.csv")
    assert {"single_frame_open_vocabulary_detection", "mask_path_certification"}.issubset(set(nontracking["task"]))
    policy = pd.read_csv(milestone / "table_release_policy_value.csv")
    assert policy["policy"].astype(str).str.contains("topM|threshold", regex=True).any()
    assert policy["policy"].astype(str).str.contains("PARC", regex=True).any()
    refusals = policy[policy["release_decision"].astype(str).eq("refusal")]
    assert not refusals.empty
    assert refusals["mass_ratio_mean"].notna().any() or refusals["empty_reason_examples"].astype(str).str.len().gt(0).any()
    teaser = pd.read_csv(milestone / "figure_release_story_teaser_manifest.csv")
    assert teaser["visual_asset_ref"].fillna("").astype(str).str.startswith("/").sum() == 0
    assert "missing_visual_asset" in set(teaser["visual_asset_status"])
    with tarfile.open(tmp_path / "outputs/packages/release_story.tar.gz", "r:gz") as tar:
        names = tar.getnames()
    assert not any(name.endswith((".mp4", ".png", ".jpg", ".jpeg", ".pth", ".pt", ".safetensors")) for name in names)
    report_text = (milestone / "RUN_REPORT.md").read_text(encoding="utf-8").lower()
    assert "medical" not in report_text
    assert "autonomous-driving" not in report_text
    assert "fairness" not in report_text
