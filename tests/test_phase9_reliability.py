from __future__ import annotations

from pathlib import Path

import pandas as pd

from parc_track import phase9
from parc_track.phase9 import (
    _box_iou,
    _count_mask_conflicts,
    _taxonomy_from_reason,
    run_audit_benchmark_industrialization,
    run_certification_api_package,
)


def test_false_taxonomy_mapping() -> None:
    assert _taxonomy_from_reason("background texture hallucination") == "background_hallucination"
    assert _taxonomy_from_reason("wrong_category") == "wrong_category"
    assert _taxonomy_from_reason("id drift after occlusion") == "id_drift"
    assert _taxonomy_from_reason("multi object merge") == "multi_object_merge"
    assert _taxonomy_from_reason("part box only") == "part_box"
    assert _taxonomy_from_reason("temporal fragment") == "temporal_fragment"
    assert _taxonomy_from_reason("misc") == "other_false"


def _write_candidate_fixture(root: Path) -> None:
    for rel in (
        "outputs/phase2_1000",
        "outputs/phase3_tao_full",
        "outputs/phase7_burst",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
    for rel in (
        "outputs/phase2_500",
        "outputs/phase3_tao_full",
        "outputs/phase7_burst",
    ):
        (root / rel).mkdir(parents=True, exist_ok=True)
    rows = []
    for idx in range(12):
        rows.append(
            {
                "video_id": f"v{idx}",
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 1,
                "score": 1.0 - idx * 0.05,
                "is_unmatched": True,
                "matched_gt_id": "",
                "matched_iou": 0.0,
                "temporal_overlap": 0.0,
                "frame_start": 0,
                "frame_end": 1,
                "path_length": 2,
                "candidate_rank": idx + 1,
                "cell_id": "global",
            }
        )
    candidate_frame = pd.DataFrame(rows)
    audit_frame = candidate_frame[["video_id", "path_id"]].copy()
    audit_frame["dataset"] = ""
    audit_frame["montage_path"] = ""
    audit_frame["clip_path"] = ""
    for path in (
        root / "outputs/phase2_1000/candidate_universe.csv",
        root / "outputs/phase3_tao_full/candidate_universe.csv",
        root / "outputs/phase7_burst/candidate_universe.csv",
    ):
        candidate_frame.to_csv(path, index=False)
    for path in (
        root / "outputs/phase2_500/audit_candidates.csv",
        root / "outputs/phase3_tao_full/audit_candidates.csv",
        root / "outputs/phase7_burst/audit_candidates.csv",
    ):
        audit_frame.to_csv(path, index=False)
    labels_dir = root / "outputs/phase3_ovtb_full"
    labels_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "dataset": "BURST",
                "video_id": "v0",
                "path_id": "p0",
                "label": "uncertain",
                "reason": "too_small",
                "auditor": "fixture",
                "confidence": "medium",
                "review_status": "reviewed",
                "verified_positive_for_calibration": "yes",
            },
            {
                "dataset": "BURST",
                "video_id": "v1",
                "path_id": "p1",
                "label": "uncertain",
                "reason": "too_small",
                "auditor": "fixture",
                "confidence": "medium",
                "review_status": "reviewed",
                "verified_positive_for_calibration": "yes",
            },
        ]
    ).to_csv(labels_dir / "combined_audit_labels.csv", index=False)


def test_audit_benchmark_keeps_uncertain_unverified(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))
    monkeypatch.setattr(phase9, "DATA_ROOT", tmp_path)
    _write_candidate_fixture(tmp_path)

    summary = run_audit_benchmark_industrialization(tmp_path / "out", total=10, second_rater_total=2)

    labels = pd.read_csv(summary["audit_labels_gold"])
    uncertain = labels[labels["label"].eq("uncertain")]
    assert not uncertain.empty
    assert set(uncertain["verified_positive_for_calibration"]) == {"no"}
    assert Path(summary["second_rater_blind_template"]).exists()
    assert int(summary["second_rater_template_rows"]) <= 2


def test_certification_api_package_writes_fixture(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))

    summary = run_certification_api_package(tmp_path / "api")

    fixture = Path(summary["tiny_fixture"])
    assert (fixture / "candidate_universe.csv").exists()
    assert (fixture / "candidate_nodes.csv").exists()
    assert (fixture / "audit_labels.csv").exists()
    assert Path(summary["api_doc"]).exists()


def test_ovvis_mask_conflict_fixture() -> None:
    assert _box_iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert _box_iou((0, 0, 10, 10), (20, 20, 10, 10)) == 0.0
    nodes = pd.DataFrame(
        [
            {"path_id": "a", "frame_index": 0, "bbox_x": 0, "bbox_y": 0, "bbox_w": 10, "bbox_h": 10},
            {"path_id": "b", "frame_index": 0, "bbox_x": 1, "bbox_y": 1, "bbox_w": 10, "bbox_h": 10},
            {"path_id": "c", "frame_index": 0, "bbox_x": 50, "bbox_y": 50, "bbox_w": 10, "bbox_h": 10},
            {"path_id": "a", "frame_index": 1, "bbox_x": 0, "bbox_y": 0, "bbox_w": 10, "bbox_h": 10},
            {"path_id": "b", "frame_index": 1, "bbox_x": 50, "bbox_y": 50, "bbox_w": 10, "bbox_h": 10},
        ]
    )
    assert _count_mask_conflicts(nodes, {"a", "b", "c"}, threshold=0.5) == 1
