from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import yaml

from parc_track.ovtrack_adapter import convert_published_tracker_predictions
from parc_track.phase8 import run_published_tracker_matrix


def _data_disk_tmp(tmp_path: Path, name: str) -> Path:
    out = Path("./outputs/test_tmp") / tmp_path.name / name
    out.mkdir(parents=True, exist_ok=True)
    return out


def _write_tiny_tracker_universe(tmp_path: Path) -> tuple[Path, Path, Path]:
    images = []
    annotations = []
    predictions = []
    for idx in range(6):
        image_id = idx + 1
        video_id = idx + 10
        images.append({"id": image_id, "video_id": video_id, "file_name": f"v{video_id}/000001.jpg", "frame_index": 0})
        annotations.append(
            {"image_id": image_id, "video_id": video_id, "track_id": 100 + idx, "category_id": 1, "bbox": [0, 0, 10, 10]}
        )
        predictions.append(
            {
                "image_id": image_id,
                "video_id": video_id,
                "track_id": 7 + idx,
                "category_id": 1,
                "bbox": [0, 0, 10, 10],
                "score": 0.95 - idx * 0.05,
            }
        )
    ann = {"images": images, "annotations": annotations, "categories": [{"id": 1, "name": "object"}]}
    ann_path = tmp_path / "ann.json"
    pred_path = tmp_path / "pred.json"
    out_dir = _data_disk_tmp(tmp_path, "converted")
    ann_path.write_text(json.dumps(ann), encoding="utf-8")
    pred_path.write_text(json.dumps(predictions), encoding="utf-8")
    convert_published_tracker_predictions(
        pred_path,
        ann_path,
        out_dir,
        tracker_name="ovtrack",
        dataset_name="OVT-B",
        dataset_root=tmp_path,
    )
    return out_dir, ann_path, pred_path


def test_published_tracker_matrix_records_effective_m(tmp_path: Path) -> None:
    out_dir, ann_path, _ = _write_tiny_tracker_universe(tmp_path)
    cfg = {
        "tracker": {"name": "ovtrack", "display_name": "OVTrack"},
        "dataset": {"name": "OVT-B", "root": str(tmp_path), "ann_file": str(ann_path)},
        "splits": {"tune_ratio": 0.10, "cal_ratio": 0.50, "test_ratio": 0.40, "seed": 0},
        "risk": {"alpha1": 0.10},
        "release_grid": {"times_sec": [2.0], "weights": "uniform"},
        "calibration": {"empty_block_policy": "coverage_conditional", "use_verified_positive_for_calibration": True},
        "e_calibrator": {"type": "power", "gamma_selection": "effective_finite_resolution_tuned"},
        "selector": {"type": "uniform_scs_greedy", "candidate_budget_sweep": [150]},
        "matrix": {"alpha1": [0.10], "seeds": [0], "candidate_budget_M": [150]},
        "input": {
            "candidate_universe": str(out_dir / "candidate_universe.csv"),
            "audit_labels": str(out_dir / "audit_labels.csv"),
        },
        "output": {"output_dir": str(out_dir), "candidate_nodes": str(out_dir / "candidate_nodes.csv")},
    }
    cfg_path = tmp_path / "phase8_matrix.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    summary = run_published_tracker_matrix(cfg_path)

    assert summary["status"] == "completed"
    matrix = pd.read_csv(out_dir / "published_tracker_alpha_seed_matrix.csv")
    assert set(matrix["method"]) == {"raw_tracker_topM", "parc_wrapped"}
    assert int(matrix["M_requested"].iloc[0]) == 150
    assert int(matrix["M_effective"].iloc[0]) == int(matrix["real_test_candidates"].iloc[0])
    assert int(matrix["M_effective"].iloc[0]) < 150
