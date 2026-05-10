from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from parc_track.ovtrack_adapter import convert_ovtrack_predictions


def test_convert_ovtrack_coco_vid_predictions_to_candidate_schema(tmp_path: Path) -> None:
    ann = {
        "images": [
            {"id": 1, "video_id": 10, "file_name": "seq/000001.jpg", "frame_index": 0},
            {"id": 2, "video_id": 10, "file_name": "seq/000002.jpg", "frame_index": 1},
        ],
        "videos": [{"id": 10, "name": "seq"}],
        "categories": [{"id": 1, "name": "dog"}, {"id": 2, "name": "cat"}],
        "annotations": [
            {"image_id": 1, "video_id": 10, "track_id": 100, "category_id": 1, "bbox": [0, 0, 10, 10]},
            {"image_id": 2, "video_id": 10, "track_id": 100, "category_id": 1, "bbox": [1, 0, 10, 10]},
        ],
    }
    pred = [
        {"image_id": 1, "video_id": 10, "track_id": 7, "category_id": 1, "bbox": [0, 0, 10, 10], "score": 0.9},
        {"image_id": 2, "video_id": 10, "track_id": 7, "category_id": 1, "bbox": [1, 0, 10, 10], "score": 0.8},
        {"image_id": 1, "video_id": 10, "track_id": 8, "category_id": 2, "bbox": [50, 50, 10, 10], "score": 0.7},
    ]
    ann_path = tmp_path / "ann.json"
    pred_path = tmp_path / "pred.json"
    ann_path.write_text(json.dumps(ann), encoding="utf-8")
    pred_path.write_text(json.dumps(pred), encoding="utf-8")

    summary = convert_ovtrack_predictions(
        pred_path,
        ann_path,
        tmp_path / "out",
        dataset_root=tmp_path,
        frame_subdir="frames",
    )

    assert summary["status"] == "completed"
    assert summary["num_prediction_rows"] == 3
    assert summary["num_candidate_paths"] == 2

    universe = pd.read_csv(tmp_path / "out" / "candidate_universe.csv")
    nodes = pd.read_csv(tmp_path / "out" / "candidate_nodes.csv")
    scores = pd.read_csv(tmp_path / "out" / "candidate_scores.csv")
    assert {"dataset", "video_id", "path_id", "score", "is_matched_to_gt", "is_unmatched"}.issubset(universe.columns)
    assert len(nodes) == 3
    assert len(scores) == 2
    matched = universe[universe["query"] == "dog"].iloc[0]
    assert bool(matched["is_matched_to_gt"]) is True
    assert int(matched["matched_frames"]) == 2
    unmatched = universe[universe["query"] == "cat"].iloc[0]
    assert bool(unmatched["is_unmatched"]) is True


def test_convert_ovtrack_missing_prediction_writes_report(tmp_path: Path) -> None:
    ann_path = tmp_path / "ann.json"
    ann_path.write_text(json.dumps({"images": [], "annotations": [], "categories": []}), encoding="utf-8")
    summary = convert_ovtrack_predictions(tmp_path / "missing.json", ann_path, tmp_path / "out")
    assert summary["status"] == "requires_ovtrack_prediction_file"
    assert (tmp_path / "out" / "ovtrack_conversion_report.json").exists()
