from __future__ import annotations

import tarfile
from pathlib import Path

import pandas as pd

from parc_track import phase11
from parc_track.phase11 import (
    _count_mask_conflicts,
    run_phase11_audit_consistency,
    run_phase11_freeze_nmi,
    run_phase11_lvis_detection,
    run_phase11_ovvis_extension,
    run_phase11_stratified_reliability,
)


def _patch_phase11_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))
    monkeypatch.setattr(phase11, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(phase11, "V2_DIR", tmp_path / "outputs/milestones/tpami_reliability_fortress_v2")
    monkeypatch.setattr(phase11, "PHASE11_DIR", tmp_path / "outputs/phase11_nmi")
    monkeypatch.setattr(phase11, "MILESTONE_DIR", tmp_path / "outputs/milestones/nmi_generality_reliability_v1")
    monkeypatch.setattr(phase11, "PACKAGE_PATH", tmp_path / "outputs/packages/nmi_generality_reliability_v1.tar.gz")


def _write_v2_fixture(root: Path) -> None:
    v2 = root / "outputs/milestones/tpami_reliability_fortress_v2"
    v2.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"dataset": "OVT-B", "path_id": "o1", "label": "actually_true", "verified_positive_for_calibration": "yes"},
            {"dataset": "OVT-B", "path_id": "o2", "label": "actually_false", "verified_positive_for_calibration": "no"},
            {"dataset": "TAO", "path_id": "t1", "label": "actually_true", "verified_positive_for_calibration": "yes"},
            {"dataset": "BURST", "path_id": "b1", "label": "uncertain", "verified_positive_for_calibration": "no"},
        ]
    ).to_csv(v2 / "audit_labels_2000_human_reviewed_v1.csv", index=False)
    pd.DataFrame(
        [
            {"dataset": "BURST", "alpha1": 0.10, "seed": 0, "released": 1, "UTR": 0.0, "conservative_FTR": 0.0},
        ]
    ).to_csv(v2 / "table_ovvis_mask_certification.csv", index=False)
    pd.DataFrame(
        [
            {"path_id": "a", "score": 1.0, "candidate_rank": 1},
            {"path_id": "b", "score": 0.9, "candidate_rank": 2},
            {"path_id": "c", "score": 0.8, "candidate_rank": 3},
        ]
    ).to_csv(v2 / "mask_path_universe.csv", index=False)
    pd.DataFrame(
        [
            {"path_id": "a", "frame_index": 0, "bbox_x": 0, "bbox_y": 0, "bbox_w": 10, "bbox_h": 10},
            {"path_id": "b", "frame_index": 0, "bbox_x": 1, "bbox_y": 1, "bbox_w": 10, "bbox_h": 10},
            {"path_id": "c", "frame_index": 0, "bbox_x": 30, "bbox_y": 30, "bbox_w": 10, "bbox_h": 10},
        ]
    ).to_csv(v2 / "mask_path_nodes.csv", index=False)
    pd.DataFrame([{"generator": "fixture", "dataset": "OVT-B", "alpha1": 0.10}]).to_csv(
        v2 / "table_blackbox_generator_certification.csv", index=False
    )
    pd.DataFrame([{"generator": "fixture", "mass_ratio": 1.2}]).to_csv(v2 / "table_prop5_three_generator.csv", index=False)
    (v2 / "second_rater_kappa_report.md").write_text("# fixture\n", encoding="utf-8")


def _write_candidate_sources(root: Path) -> None:
    for rel, prefix in (("outputs/phase2_1000", "o"), ("outputs/phase3_tao_full", "t")):
        out = root / rel
        out.mkdir(parents=True, exist_ok=True)
        universe = pd.DataFrame(
            [
                {
                    "dataset": "OVT-B" if prefix == "o" else "TAO",
                    "path_id": f"{prefix}{idx}",
                    "query": "object" if idx < 2 else "rare",
                    "category_id": 1 if idx < 2 else 2,
                    "score": 0.9 - idx * 0.1,
                    "path_length": idx + 1,
                    "is_unmatched": idx % 2 == 0,
                    "is_released": idx == 0,
                }
                for idx in range(4)
            ]
        )
        nodes = pd.DataFrame(
            [
                {
                    "path_id": f"{prefix}{idx}",
                    "frame_index": frame,
                    "bbox_x": idx * 10 + frame,
                    "bbox_y": idx * 5,
                    "bbox_w": 10 + idx,
                    "bbox_h": 8 + idx,
                }
                for idx in range(4)
                for frame in range(2)
            ]
        )
        universe.to_csv(out / "candidate_universe.csv", index=False)
        nodes.to_csv(out / "candidate_nodes.csv", index=False)


def test_audit_consistency_outputs_cross_dataset_rates(tmp_path: Path, monkeypatch) -> None:
    _patch_phase11_roots(tmp_path, monkeypatch)
    _write_v2_fixture(tmp_path)

    summary = run_phase11_audit_consistency()

    table = pd.read_csv(summary["table"])
    assert set(table["dataset"]) == {"OVT-B", "TAO", "BURST"}
    assert "human_valid_rate" in table.columns
    assert Path(summary["doc"]).exists()


def test_lvis_detection_missing_detectors_is_loud_and_schema_stable(tmp_path: Path, monkeypatch) -> None:
    _patch_phase11_roots(tmp_path, monkeypatch)

    summary = run_phase11_lvis_detection()

    table = pd.read_csv(summary["table"])
    assert {"dataset", "detector", "alpha1", "seed", "M", "released", "result_status"}.issubset(table.columns)
    assert set(table["detector"]) == {"GroundingDINO", "OWLv2"}
    assert set(table["result_status"]) == {"not_run_missing_detector_candidates_or_matrix"}
    labels = pd.read_csv(summary["audit_labels"])
    assert "verified_positive_for_calibration" in labels.columns


def test_stratified_reliability_contains_visual_difficulty_dimensions(tmp_path: Path, monkeypatch) -> None:
    _patch_phase11_roots(tmp_path, monkeypatch)
    _write_v2_fixture(tmp_path)
    _write_candidate_sources(tmp_path)

    summary = run_phase11_stratified_reliability()

    table = pd.read_csv(summary["table"])
    assert {"object_size", "occlusion_level", "motion_speed", "track_length", "category_frequency"}.issubset(
        set(table["stratification_dimension"])
    )
    assert {
        "official_support_rate",
        "official_unmatched_rate",
        "human_valid_rate",
        "PARC_certified_release_rate",
        "PARC_refusal_rate",
    }.issubset(table.columns)
    assert Path(summary["support_vs_human_valid_figure_csv"]).exists()
    assert Path(summary["release_refusal_figure_csv"]).exists()


def test_ovvis_mask_conflict_thresholds(tmp_path: Path, monkeypatch) -> None:
    _patch_phase11_roots(tmp_path, monkeypatch)
    _write_v2_fixture(tmp_path)

    summary = run_phase11_ovvis_extension()

    table = pd.read_csv(summary["table"])
    assert set(table["mask_iou_threshold"]) == {0.3, 0.5}
    assert table["paper_scope"].astype(str).str.contains("proof_of_principle").all()
    nodes = pd.read_csv(tmp_path / "outputs/milestones/tpami_reliability_fortress_v2/mask_path_nodes.csv")
    assert _count_mask_conflicts(nodes, {"a", "b", "c"}, threshold=0.5) == 1


def test_freeze_nmi_package_is_public_safe(tmp_path: Path, monkeypatch) -> None:
    _patch_phase11_roots(tmp_path, monkeypatch)
    _write_v2_fixture(tmp_path)
    _write_candidate_sources(tmp_path)

    summary = run_phase11_freeze_nmi()

    milestone = tmp_path / "outputs/milestones/nmi_generality_reliability_v1"
    package = tmp_path / "outputs/packages/nmi_generality_reliability_v1.tar.gz"
    assert milestone.exists()
    assert package.exists()
    assert Path(milestone / "MANIFEST_SHA256.txt").exists()
    for path in milestone.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".csv", ".json", ".md", ".txt"}:
            text = path.read_text(encoding="utf-8")
            assert "/home/" + "waas" not in text
            assert "/" + "root/" not in text
            forbidden_claims = ("medical", "autonomous-driving", "autonomous driving", "fairness")
            assert not any(term in text.lower() for term in forbidden_claims)
    with tarfile.open(package, "r:gz") as tar:
        names = tar.getnames()
    assert not any(name.endswith((".mp4", ".pth", ".pt", ".safetensors")) for name in names)
    assert summary["package_sha256"]
