from __future__ import annotations

import csv
import json
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
import yaml

from parc_track.adapters.datasets import (
    inspect_bdd100k_mot_layout,
    inspect_coco_video_dataset,
    inspect_dataset_from_config,
)
from parc_track.phase2 import (
    AUDIT_COLUMNS,
    AUDIT_LABEL_COLUMNS,
    CANDIDATE_UNIVERSE_COLUMNS,
    RELEASE_AUDIT_COLUMNS,
    compute_cell_effective_n,
    emax,
    export_release_audit_candidates,
    gamma_star,
    groundingdino_status,
    iou_xywh,
    owlv2_status,
    _best_mass_summary,
    run_phase2_propose,
    run_real_certify,
    run_real_coverage_sweep,
    run_real_high_e_diagnostics,
    summarize_audit,
)
from parc_track.phase3 import (
    evaluate_clear_mot_idsw,
    export_matrix_release_audit_candidates,
    run_idsw_eval,
    run_ovtb_matrix,
    run_release_core_report,
    run_tuned_m_selection,
)


DATA_ROOT = Path(".")


def _test_root(name: str) -> Path:
    root = DATA_ROOT / "tmp" / "phase2_tests" / f"{name}_{uuid4().hex}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_yaml(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    return path


def _write_tiny_tracking_dataset(root: Path, ann_name: str = "ann.json", videos: int = 6) -> Path:
    frame = root / "frames" / "v001" / "000001.jpg"
    frame.parent.mkdir(parents=True, exist_ok=True)
    frame.write_bytes(b"not-a-real-jpeg-but-path-exists")
    annotation = {
        "videos": [{"id": idx + 1, "name": f"v{idx + 1:03d}"} for idx in range(videos)],
        "images": [
            {
                "id": 1,
                "video_id": 1,
                "frame_id": 0,
                "file_name": "frames/v001/000001.jpg",
            }
        ],
        "annotations": [
            {
                "id": 1,
                "image_id": 1,
                "video_id": 1,
                "track_id": 7,
                "category_id": 3,
                "bbox": [10, 20, 30, 40],
            }
        ],
        "categories": [{"id": 3, "name": "novel-object"}],
    }
    ann_path = root / ann_name
    with ann_path.open("w", encoding="utf-8") as handle:
        json.dump(annotation, handle)
    return ann_path


def test_ovtb_like_json_schema_detection_on_tiny_fixture() -> None:
    root = _test_root("ovtb")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json")
    report = inspect_coco_video_dataset("OVT-B", root, ann_path, "tao_or_coco_video")
    assert report["status"] == "tracking_layout_ok"
    assert report["has_video_frames"]
    assert report["has_track_ids"]
    assert report["has_category_labels"]
    assert report["has_frame_indices"]
    assert report["has_video_ids"]


def test_tao_config_schema_detection_on_tiny_fixture() -> None:
    root = _test_root("tao")
    ann_path = _write_tiny_tracking_dataset(root, "train.json")
    cfg_path = _write_yaml(
        root / "phase2_tao_fixture.yaml",
        {
            "dataset": {
                "name": "TAO",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao",
            }
        },
    )
    report = inspect_dataset_from_config(cfg_path)
    assert report["status"] == "tracking_layout_ok"
    assert report["num_tracks"] == 1
    assert report["num_categories"] == 1


def test_bdd_current_package_root_remains_not_mot_tracking_layout() -> None:
    report = inspect_bdd100k_mot_layout("/datasets/MoGuiMianJu")
    assert report["status"] == "not_mot_tracking_layout"
    assert "missing_images_track" in report["errors"]


def test_groundingdino_backend_locates_local_config_and_weights() -> None:
    root = _test_root("gd")
    gd_root = root / "grounding-dino"
    gd_root.mkdir(parents=True, exist_ok=True)
    local_config = gd_root / "GroundingDINO_SwinT_OGC.cfg.py"
    local_weights = gd_root / "groundingdino_swint_ogc.pth"
    local_config.write_text("# fixture config\n", encoding="utf-8")
    local_weights.write_bytes(b"fixture weights")
    cfg_path = _write_yaml(
        root / "phase2_audit_fixture.yaml",
        {
            "groundingdino": {
                "config": str(local_config),
                "weights": str(local_weights),
            }
        },
    )
    status = groundingdino_status(cfg_path)
    assert status["config_exists"]
    assert status["weights_exists"]
    assert "import_ready" in status
    assert isinstance(status["missing_imports"], list)


def test_candidate_matching_iou_threshold_behavior() -> None:
    assert iou_xywh((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou_xywh((0, 0, 10, 10), (20, 20, 10, 10)) == 0.0
    assert iou_xywh((0, 0, 10, 10), (5, 0, 10, 10)) < 0.5


def test_audit_summarizer_counts_labels_and_true_rate() -> None:
    root = _test_root("audit_summary")
    candidates = root / "audit_candidates.csv"
    labels = root / "audit_labels.csv"
    out = root / "audit_summary.csv"
    with candidates.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_COLUMNS)
        writer.writeheader()
        for idx in range(3):
            row = {column: "" for column in AUDIT_COLUMNS}
            row.update({"dataset": "OVT-B", "video_id": "v1", "path_id": f"p{idx}", "is_unmatched": True})
            writer.writerow(row)
    with labels.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
        writer.writeheader()
        writer.writerow({"dataset": "OVT-B", "video_id": "v1", "path_id": "p0", "label": "actually_true"})
        writer.writerow({"dataset": "OVT-B", "video_id": "v1", "path_id": "p1", "label": "actually_false"})
        writer.writerow({"dataset": "OVT-B", "video_id": "v1", "path_id": "p2", "label": "uncertain"})
    summarize_audit(candidates, labels, out)
    summary = pd.read_csv(out)
    assert int(summary["Actually true"].iloc[0]) == 1
    assert int(summary["Actually false"].iloc[0]) == 1
    assert int(summary["Uncertain"].iloc[0]) == 1
    assert abs(float(summary["Actually true %"].iloc[0]) - (1 / 3)) < 1e-12


def test_cell_effective_n_gamma_star_and_fallback_fields() -> None:
    root = _test_root("cell_n")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=20)
    cfg_path = _write_yaml(
        root / "phase2_real_mini_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "release_grid": {"times_sec": [0.5, 1.0, 2.0, 4.0, 8.0]},
            "input": {"candidate_universe": str(root / "missing_candidate_universe.csv")},
        },
    )
    out = root / "cell_effective_n.csv"
    result = compute_cell_effective_n(cfg_path, out)
    rows = pd.read_csv(out)
    assert result["rows"] == 1
    assert int(rows["n_dataset_total"].iloc[0]) == 20
    assert int(rows["n_rank_denominator"].iloc[0]) == 0
    assert pd.isna(rows["gamma_star"].iloc[0])
    assert int(rows["fallback_level"].iloc[0]) == 0


def _write_candidate_universe(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CANDIDATE_UNIVERSE_COLUMNS)
        writer.writeheader()
        for row in rows:
            full = {column: "" for column in CANDIDATE_UNIVERSE_COLUMNS}
            full.update(row)
            writer.writerow(full)


def test_cell_effective_n_uses_scored_calibration_not_dataset_total() -> None:
    root = _test_root("cell_n_scored")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=20)
    universe = root / "candidate_universe.csv"
    rows = []
    for idx, video_id in enumerate(range(1, 7)):
        rows.append(
            {
                "dataset": "OVT-B",
                "video_id": video_id,
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 3,
                "score": 0.9 - idx * 0.05,
                "candidate_rank": idx + 1,
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "cell_id": "global",
                "verified_positive_for_calibration": "no",
            }
        )
    _write_candidate_universe(universe, rows)
    cfg_path = _write_yaml(
        root / "phase2_real_cert_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "splits": {"tune_ratio": 0.0, "cal_ratio": 0.5, "seed": 0},
            "release_grid": {"times_sec": [1.0, 2.0]},
            "input": {"candidate_universe": str(universe), "audit_labels": str(root / "missing_labels.csv")},
        },
    )
    out = root / "cell_effective_n.csv"
    compute_cell_effective_n(cfg_path, out)
    effective = pd.read_csv(out)
    assert int(effective["n_dataset_total"].iloc[0]) == 20
    assert int(effective["n_processed_videos"].iloc[0]) == 6
    assert int(effective["n_rank_denominator"].iloc[0]) == 3
    assert int(effective["n_rank_denominator"].iloc[0]) <= int(effective["n_processed_videos"].iloc[0])


def test_real_certify_removes_verified_positive_and_preserves_uncertain() -> None:
    root = _test_root("real_cert")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=8)
    universe = root / "candidate_universe.csv"
    labels = root / "audit_labels.csv"
    rows = []
    for idx, video_id in enumerate(range(1, 9)):
        rows.append(
            {
                "dataset": "OVT-B",
                "video_id": video_id,
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 3,
                "score": 1.0 - idx * 0.05,
                "candidate_rank": idx + 1,
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "cell_id": "global",
                "verified_positive_for_calibration": "no",
            }
        )
    _write_candidate_universe(universe, rows)
    with labels.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "dataset": "OVT-B",
                "video_id": 1,
                "path_id": "p0",
                "label": "actually_true",
                "verified_positive_for_calibration": "yes",
            }
        )
        writer.writerow(
            {
                "dataset": "OVT-B",
                "video_id": 2,
                "path_id": "p1",
                "label": "uncertain",
                "verified_positive_for_calibration": "no",
            }
        )
    cfg_path = _write_yaml(
        root / "phase2_real_cert_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "splits": {"tune_ratio": 0.0, "cal_ratio": 1.0, "seed": 0},
            "risk": {"alpha1": 0.10},
            "release_grid": {"times_sec": [1.0, 2.0]},
            "selector": {"candidate_budget_sweep": [4]},
            "input": {"candidate_universe": str(universe), "audit_labels": str(labels)},
            "output": {
                "summary": str(root / "real_certify_summary.json"),
                "real_cert_summary": str(root / "real_cert_summary.csv"),
                "candidate_evalues": str(root / "candidate_evalues.csv"),
                "cell_effective_n": str(root / "cell_effective_n.csv"),
            },
        },
    )
    summary = run_real_certify(cfg_path)
    assert summary["status"] == "completed_full_universe_scaffold"
    cert = pd.read_csv(root / "real_cert_summary.csv")
    parc = cert[cert["method"] == "parc_track_gamma_tuned_uniform_scs"].iloc[0]
    no_audit = cert[cert["method"] == "null_superset_no_audit"].iloc[0]
    assert int(parc["verified_positive_removed"]) == 1
    assert int(no_audit["verified_positive_removed"]) == 0
    assert int(parc["null_superset_size"]) <= int(no_audit["null_superset_size"])
    if int(parc["audited_released"]):
        assert float(parc["utr"]) >= 0.0


def test_cell_effective_n_reports_coverage_conditional_fields() -> None:
    root = _test_root("cell_n_cov")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=4)
    universe = root / "candidate_universe.csv"
    _write_candidate_universe(
        universe,
        [
            {
                "dataset": "OVT-B",
                "video_id": 1,
                "path_id": "p1",
                "score": 0.9,
                "candidate_rank": 1,
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            },
            {
                "dataset": "OVT-B",
                "video_id": 2,
                "path_id": "p2",
                "score": 0.8,
                "candidate_rank": 2,
                "is_unmatched": False,
                "is_matched_to_gt": True,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            },
            {
                "dataset": "OVT-B",
                "video_id": 3,
                "path_id": "p3",
                "score": 0.7,
                "candidate_rank": 3,
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            },
            {
                "dataset": "OVT-B",
                "video_id": 4,
                "path_id": "p4",
                "score": 0.6,
                "candidate_rank": 4,
                "is_unmatched": False,
                "is_matched_to_gt": True,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            },
        ],
    )
    cfg_path = _write_yaml(
        root / "phase2_real_cert_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "splits": {"tune_ratio": 0.0, "cal_ratio": 1.0, "seed": 0},
            "risk": {"alpha1": 0.10},
            "release_grid": {"times_sec": [2.0]},
            "input": {"candidate_universe": str(universe), "audit_labels": str(root / "missing_labels.csv")},
        },
    )
    out = root / "cell_effective_n.csv"
    compute_cell_effective_n(cfg_path, out)
    row = pd.read_csv(out).iloc[0]
    assert int(row["n_rank_denominator"]) == 4
    assert int(row["n_nonempty_null_videos"]) == 2
    assert int(row["n_empty_null_videos"]) == 2
    assert abs(float(row["p_min_block_conservative"]) - 0.6) < 1e-12
    assert abs(float(row["p_min_block_cov"]) - (1 / 3)) < 1e-12
    assert float(row["p_min_cov"]) < float(row["p_min_any_conservative"])


def test_real_certify_records_coverage_policy_and_per_video_coverage() -> None:
    root = _test_root("real_cert_policy")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=6)
    universe = root / "candidate_universe.csv"
    rows = []
    for idx, video_id in enumerate(range(1, 7)):
        rows.append(
            {
                "dataset": "OVT-B",
                "video_id": video_id,
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 3,
                "score": 1.0 - idx * 0.05,
                "candidate_rank": idx + 1,
                "is_unmatched": idx % 2 == 0,
                "is_matched_to_gt": idx % 2 != 0,
                "cell_id": "global",
                "verified_positive_for_calibration": "no",
            }
        )
    _write_candidate_universe(universe, rows)
    cfg_path = _write_yaml(
        root / "phase2_real_cert_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "splits": {"tune_ratio": 0.0, "cal_ratio": 0.5, "seed": 0},
            "risk": {"alpha1": 0.10},
            "release_grid": {"times_sec": [2.0]},
            "calibration": {"empty_block_policy": "coverage_conditional"},
            "selector": {"candidate_budget_sweep": [4]},
            "input": {"candidate_universe": str(universe), "audit_labels": str(root / "missing_labels.csv")},
            "output": {
                "summary": str(root / "real_certify_summary.json"),
                "real_cert_summary": str(root / "real_cert_summary.csv"),
                "candidate_evalues": str(root / "candidate_evalues.csv"),
                "cell_effective_n": str(root / "cell_effective_n.csv"),
                "per_video_candidate_coverage": str(root / "per_video_candidate_coverage.csv"),
            },
        },
    )
    run_real_certify(cfg_path)
    cert = pd.read_csv(root / "real_cert_summary.csv")
    assert set(cert["empty_block_policy"]) == {"coverage_conditional"}
    assert "p_min_block" in cert.columns
    assert "required_emax" in cert.columns
    assert "release_feasible" in cert.columns
    assert "n_cal_total" in cert.columns
    assert "n_covered" in cert.columns
    assert "n_excluded_empty" in cert.columns
    assert "n_rank_denominator" in cert.columns
    parc = cert[cert["method"] == "parc_track_gamma_tuned_uniform_scs"].iloc[0]
    assert int(parc["n_cal_total"]) == int(parc["n_covered"]) + int(parc["n_excluded_empty"])
    assert int(parc["n_rank_denominator"]) == int(parc["n_covered"])
    coverage = pd.read_csv(root / "per_video_candidate_coverage.csv")
    assert len(coverage) == 6
    assert "has_null_block" in coverage.columns


def test_coverage_sweep_feasibility_matches_emax_threshold() -> None:
    root = _test_root("coverage_sweep")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=8)
    universe = root / "candidate_universe.csv"
    rows = []
    for idx, video_id in enumerate(range(1, 9)):
        rows.append(
            {
                "dataset": "OVT-B",
                "video_id": video_id,
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 3,
                "score": 1.0 - idx * 0.05,
                "candidate_rank": idx + 1,
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "cell_id": "global",
                "verified_positive_for_calibration": "no",
            }
        )
    _write_candidate_universe(universe, rows)
    cfg_path = _write_yaml(
        root / "phase2_real_cert_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "splits": {"tune_ratio": 0.0, "cal_ratio": 0.5, "seed": 0},
            "risk": {"alpha1": 0.10},
            "release_grid": {"times_sec": [2.0]},
            "coverage_sweep": {
                "processed_videos": [8, 1000],
                "cal_ratios": [0.5],
                "release_grids": [[2.0]],
                "empty_block_policy": ["conservative_infinity", "coverage_conditional"],
            },
            "input": {"candidate_universe": str(universe), "audit_labels": str(root / "missing_labels.csv")},
            "output": {"coverage_sweep": str(root / "coverage_sweep.csv")},
        },
    )
    run_real_coverage_sweep(cfg_path)
    sweep = pd.read_csv(root / "coverage_sweep.csv")
    assert not sweep.empty
    for _, row in sweep.iterrows():
        feasible = bool(row["release_feasible"])
        emax_value = row["emax_eff"]
        expected = pd.notna(emax_value) and float(emax_value) >= float(row["required_emax"])
        assert feasible == expected


def test_coverage_sweep_writes_projection_vs_observed() -> None:
    root = _test_root("coverage_projection")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=8)
    universe = root / "candidate_universe.csv"
    rows = []
    for idx, video_id in enumerate(range(1, 9)):
        rows.append(
            {
                "dataset": "OVT-B",
                "video_id": video_id,
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 3,
                "score": 1.0 - idx * 0.05,
                "candidate_rank": idx + 1,
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "cell_id": "global",
                "verified_positive_for_calibration": "no",
            }
        )
    _write_candidate_universe(universe, rows)
    baseline = root / "baseline_coverage_sweep.csv"
    with baseline.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "processed_videos",
                "cal_ratio",
                "grid_size",
                "release_grid",
                "empty_block_policy",
                "n_rank",
                "n_nonempty",
                "n_empty",
                "p_min_block",
                "p_min_any",
                "gamma_star_eff",
                "emax_eff",
                "required_emax",
                "release_feasible",
                "observed_nonempty_rate",
                "projection",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "processed_videos": 8,
                "cal_ratio": 0.5,
                "grid_size": 1,
                "release_grid": "2.0",
                "empty_block_policy": "coverage_conditional",
                "n_rank": 4,
                "n_nonempty": 3,
                "n_empty": 1,
                "p_min_block": 0.25,
                "p_min_any": 0.25,
                "gamma_star_eff": 0.7,
                "emax_eff": 2.0,
                "required_emax": 10.0,
                "release_feasible": False,
                "observed_nonempty_rate": 0.75,
                "projection": True,
            }
        )
    cfg_path = _write_yaml(
        root / "phase2_real_cert_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "splits": {"tune_ratio": 0.0, "cal_ratio": 0.5, "seed": 0},
            "risk": {"alpha1": 0.10},
            "coverage_sweep": {
                "processed_videos": [8],
                "cal_ratios": [0.5],
                "release_grids": [[2.0]],
                "empty_block_policy": ["coverage_conditional"],
                "projection_baseline": str(baseline),
            },
            "input": {"candidate_universe": str(universe), "audit_labels": str(root / "missing_labels.csv")},
            "output": {
                "coverage_sweep": str(root / "coverage_sweep.csv"),
                "projection_vs_observed": str(root / "projection_vs_observed.csv"),
            },
        },
    )
    run_real_coverage_sweep(cfg_path)
    projection = pd.read_csv(root / "projection_vs_observed.csv")
    assert len(projection) == 1
    assert int(projection["processed_videos"].iloc[0]) == 8
    assert int(projection["projected_n_nonempty"].iloc[0]) == 3
    assert int(projection["observed_n_nonempty"].iloc[0]) == 4


def test_phase2_500_configs_route_outputs_to_phase2_500_and_reuse_labels() -> None:
    audit_cfg = yaml.safe_load(Path("./configs/phase2_audit_500.yaml").read_text())
    single_cfg = yaml.safe_load(Path("./configs/phase2_real_cert_500_single.yaml").read_text())
    two_cfg = yaml.safe_load(Path("./configs/phase2_real_cert_500_two.yaml").read_text())
    assert int(audit_cfg["proposal"]["max_videos"]) == 500
    assert "/outputs/phase2_500/" in audit_cfg["output"]["candidate_universe"]
    assert audit_cfg["output"]["labels"] == "./outputs/phase2/audit_labels.csv"
    for cfg in (single_cfg, two_cfg):
        assert cfg["input"]["audit_labels"] == "./outputs/phase2/audit_labels.csv"
        assert "/outputs/phase2_500/" in cfg["input"]["candidate_universe"]
        assert "/outputs/phase2_500/" in cfg["output"]["real_cert_summary"]
        assert cfg["calibration"]["empty_block_policy"] == "coverage_conditional"


def test_phase2_1000_configs_route_outputs_to_phase2_1000_and_reuse_labels() -> None:
    audit_cfg = yaml.safe_load(Path("./configs/phase2_audit_1000.yaml").read_text())
    cert_cfg = yaml.safe_load(Path("./configs/phase2_real_cert_1000_single.yaml").read_text())
    assert int(audit_cfg["proposal"]["max_videos"]) == 1000
    assert "/outputs/phase2_1000/" in audit_cfg["output"]["candidate_universe"]
    assert audit_cfg["output"]["labels"] == "./outputs/phase2/audit_labels.csv"
    assert cert_cfg["input"]["audit_labels"] == "./outputs/phase2/audit_labels.csv"
    assert "/outputs/phase2_1000/" in cert_cfg["input"]["candidate_universe"]
    assert "/outputs/phase2_1000/" in cert_cfg["output"]["real_cert_summary"]
    assert cert_cfg["calibration"]["empty_block_policy"] == "coverage_conditional"
    assert cert_cfg["coverage_sweep"]["projection_baseline"] == "./outputs/phase2_500/coverage_sweep_500_single.csv"


def test_best_mass_summary_matches_self_consistency_ratio() -> None:
    summary = _best_mass_summary([12.0, 11.0, 2.0], alpha1=0.10, candidate_budget_m=2)
    assert summary["best_k"] == 2
    assert abs(float(summary["best_mass_ratio"]) - 1.1) < 1e-12
    assert summary["released_unconstrained"]
    weak = _best_mass_summary([9.0, 8.0, 7.0], alpha1=0.10, candidate_budget_m=3)
    assert float(weak["best_mass_ratio"]) < 1.0
    assert not weak["released_unconstrained"]


def test_real_high_e_diagnostics_outputs_budget_and_gamma_rows() -> None:
    root = _test_root("high_e_diag")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=4)
    universe = root / "candidate_universe.csv"
    _write_candidate_universe(
        universe,
        [
            {
                "dataset": "OVT-B",
                "video_id": 1,
                "path_id": "p1",
                "score": 0.9,
                "candidate_rank": 1,
                "split": "test",
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            },
            {
                "dataset": "OVT-B",
                "video_id": 2,
                "path_id": "p2",
                "score": 0.8,
                "candidate_rank": 2,
                "split": "test",
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            },
            {
                "dataset": "OVT-B",
                "video_id": 3,
                "path_id": "p3",
                "score": 0.7,
                "candidate_rank": 3,
                "split": "test",
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            },
        ],
    )
    evalues = root / "candidate_evalues.csv"
    with evalues.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "dataset",
                "video_id",
                "path_id",
                "release_checkpoint",
                "cell_id",
                "score",
                "p_block",
                "p_any",
                "e_value",
                "gamma",
                "gamma_star",
                "empty_block_policy",
                "p_min_block",
                "p_min_effective",
                "emax_effective",
                "score_source",
                "method",
                "audit_policy",
            ],
        )
        writer.writeheader()
        for path_id, p_any, e_value in [("p1", 0.01, 12.0), ("p2", 0.02, 11.0), ("p3", 0.5, 1.0)]:
            writer.writerow(
                {
                    "dataset": "OVT-B",
                    "video_id": 1,
                    "path_id": path_id,
                    "release_checkpoint": "final",
                    "cell_id": "global",
                    "score": 0.9,
                    "p_block": p_any,
                    "p_any": p_any,
                    "e_value": e_value,
                    "gamma": 0.2,
                    "gamma_star": 0.2,
                    "empty_block_policy": "coverage_conditional",
                    "p_min_block": 0.01,
                    "p_min_effective": 0.01,
                    "emax_effective": 12.0,
                    "score_source": "final_score_proxy",
                    "method": "parc_track_gamma_tuned_uniform_scs",
                    "audit_policy": "fixture",
                }
            )
    cfg_path = _write_yaml(
        root / "phase2_high_e_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "risk": {"alpha1": 0.10},
            "high_e_diagnostics": {
                "candidate_budget_sweep": [2, 3],
                "gamma_candidates": [0.2, 0.5],
            },
            "input": {"candidate_universe": str(universe), "audit_labels": str(root / "missing_labels.csv")},
            "output": {
                "candidate_evalues": str(evalues),
                "high_e_mass_diagnostics": str(root / "high_e_mass_diagnostics.csv"),
                "gamma_mass_sweep": str(root / "gamma_mass_sweep.csv"),
            },
        },
    )
    summary = run_real_high_e_diagnostics(cfg_path)
    assert summary["status"] == "completed"
    diagnostics = pd.read_csv(root / "high_e_mass_diagnostics.csv")
    gamma = pd.read_csv(root / "gamma_mass_sweep.csv")
    curve = pd.read_csv(root / "scs_feasibility_curve_M2.csv")
    assert set(diagnostics["candidate_budget_M"]) == {2, 3}
    assert set(gamma["gamma"]) == {0.2, 0.5}
    assert not curve.empty
    assert "mass_ratio_k" in curve.columns
    assert bool(diagnostics.loc[diagnostics["candidate_budget_M"] == 2, "released_unconstrained"].iloc[0])


def test_export_release_audit_reconstructs_selected_candidates_and_preserves_labels() -> None:
    root = _test_root("release_audit")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=6)
    universe = root / "candidate_universe.csv"
    rows = []
    for idx, video_id in enumerate(range(1, 7)):
        rows.append(
            {
                "dataset": "OVT-B",
                "video_id": video_id,
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 3,
                "score": 1.0 - idx * 0.01,
                "candidate_rank": idx + 1,
                "is_unmatched": True,
                "is_matched_to_gt": False,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            }
        )
    _write_candidate_universe(universe, rows)
    evalues = root / "candidate_evalues.csv"
    with evalues.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "dataset",
                "video_id",
                "path_id",
                "release_checkpoint",
                "cell_id",
                "score",
                "p_block",
                "p_any",
                "e_value",
                "gamma",
                "gamma_star",
                "empty_block_policy",
                "p_min_block",
                "p_min_effective",
                "emax_effective",
                "score_source",
                "method",
                "audit_policy",
            ],
        )
        writer.writeheader()
        for idx in range(6):
            writer.writerow(
                {
                    "dataset": "OVT-B",
                    "video_id": idx + 1,
                    "path_id": f"p{idx}",
                    "release_checkpoint": "final",
                    "cell_id": "global",
                    "score": 1.0 - idx * 0.01,
                    "p_block": 0.01,
                    "p_any": 0.01,
                    "e_value": 12.0,
                    "gamma": 0.2,
                    "gamma_star": 0.2,
                    "empty_block_policy": "coverage_conditional",
                    "p_min_block": 0.01,
                    "p_min_effective": 0.01,
                    "emax_effective": 12.0,
                    "score_source": "final_score_proxy",
                    "method": "parc_track_gamma_tuned_uniform_scs",
                    "audit_policy": "fixture",
                }
            )
    labels = root / "release_labels.csv"
    with labels.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "dataset": "OVT-B",
                "video_id": 99,
                "path_id": "already_labeled",
                "label": "actually_true",
                "verified_positive_for_calibration": "yes",
            }
        )
    cfg_path = _write_yaml(
        root / "phase2_release_audit_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "splits": {"tune_ratio": 0.0, "cal_ratio": 0.0, "seed": 0},
            "risk": {"alpha1": 0.10},
            "selector": {"candidate_budget_sweep": [5]},
            "input": {"candidate_universe": str(universe), "audit_labels": str(root / "missing_labels.csv")},
            "output": {
                "candidate_evalues": str(evalues),
                "candidate_nodes": str(root / "missing_nodes.csv"),
                "real_cert_summary": str(root / "real_cert_summary.csv"),
            },
        },
    )
    out = root / "release_audit.csv"
    summary = export_release_audit_candidates(
        cfg_path,
        method="parc_track_gamma_tuned_uniform_scs",
        budget=5,
        out_csv=out,
        labels_out=labels,
        viewer_path=root / "release_viewer",
        unsupported_only=True,
    )
    exported = pd.read_csv(out)
    preserved = pd.read_csv(labels)
    assert summary["status"] == "completed"
    assert int(summary["released"]) == 5
    assert int(summary["released_total"]) == 5
    assert summary["unsupported_only"]
    assert len(exported) == 5
    assert set(RELEASE_AUDIT_COLUMNS).issubset(set(exported.columns))
    assert float(exported["self_consistency_margin"].iloc[0]) >= 0.0
    assert list(preserved["path_id"]) == ["already_labeled"]


def test_phase3_config_routes_outputs_to_phase3_and_reuses_frozen_labels() -> None:
    cfg = yaml.safe_load(Path("./configs/phase3_ovtb_matrix.yaml").read_text())
    assert cfg["input"]["audit_labels"] == "./outputs/phase2/audit_labels.csv"
    assert "extra_audit_labels" in cfg["input"]
    assert "/outputs/phase3_ovtb" in cfg["output"]["output_dir"]
    assert cfg["tune_selection"]["out"] == "./outputs/phase3_ovtb/tuned_m_selection.csv"
    assert cfg["matrix"]["alpha1"] == [0.05, 0.10, 0.20]
    assert cfg["matrix"]["seeds"] == [0, 1, 2]
    assert 150 in cfg["matrix"]["candidate_budget_M"]


def test_phase3_ovtb_matrix_writes_expanded_baseline_schema() -> None:
    root = _test_root("phase3_matrix")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=10)
    universe = root / "candidate_universe.csv"
    rows = []
    for idx, video_id in enumerate(range(1, 11)):
        rows.append(
            {
                "dataset": "OVT-B",
                "video_id": video_id,
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 3,
                "score": 1.0 - idx * 0.02,
                "candidate_rank": idx + 1,
                "is_unmatched": idx % 3 != 0,
                "is_matched_to_gt": idx % 3 == 0,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            }
        )
    _write_candidate_universe(universe, rows)
    labels = root / "audit_labels.csv"
    with labels.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
        writer.writeheader()
        writer.writerow({"dataset": "OVT-B", "video_id": 1, "path_id": "p0", "label": "actually_true", "verified_positive_for_calibration": "yes"})
        writer.writerow({"dataset": "OVT-B", "video_id": 2, "path_id": "p1", "label": "actually_false", "verified_positive_for_calibration": "no"})
    cfg_path = _write_yaml(
        root / "phase3_ovtb_matrix_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "splits": {"tune_ratio": 0.0, "cal_ratio": 0.5, "seed": 0},
            "risk": {"alpha1": 0.10},
            "release_grid": {"times_sec": [2.0]},
            "calibration": {"empty_block_policy": "coverage_conditional", "use_verified_positive_for_calibration": True},
            "selector": {"candidate_budget_sweep": [3]},
            "matrix": {"alpha1": [0.10, 0.20], "seeds": [0, 1], "candidate_budget_M": [3]},
            "input": {"candidate_universe": str(universe), "audit_labels": str(labels)},
            "output": {"output_dir": str(root / "phase3_ovtb")},
        },
    )
    summary = run_ovtb_matrix(cfg_path)
    assert summary["status"] == "completed"
    matrix = pd.read_csv(root / "phase3_ovtb" / "ovtb_alpha_seed_m_matrix.csv")
    assert set(["method", "alpha1", "seed", "candidate_budget_M", "released", "utr", "recall_proxy", "runtime_sec"]).issubset(matrix.columns)
    assert {"confidence_threshold", "tracklet_p_bh", "tracklet_e_bh", "post_filter_e_bh", "greedy_score_no_risk"}.issubset(set(matrix["method"]))
    assert matrix.groupby(["alpha1", "seed"]).size().shape[0] == 4


def test_owlv2_configs_route_to_isolated_outputs_and_backend() -> None:
    ovtb = yaml.safe_load(Path("./configs/phase3_ovtb_owlv2_audit.yaml").read_text())
    tao = yaml.safe_load(Path("./configs/phase3_tao_owlv2_audit.yaml").read_text())
    for cfg, marker in ((ovtb, "/outputs/phase3_ovtb_owlv2/"), (tao, "/outputs/phase3_tao_owlv2/")):
        assert cfg["proposal"]["backend"] == "owlv2_hf"
        assert cfg["proposal"]["backbone"] == "owlv2_hf"
        assert cfg["owlv2"]["device"].startswith("cuda")
        assert marker in cfg["output"]["candidate_universe"]
        assert marker in cfg["output"]["candidate_scores"]
        assert marker in cfg["output"]["candidate_nodes"]
        assert marker in cfg["audit_export"]["output_viewer"]


def test_owlv2_phase2_propose_fails_loudly_when_dataset_missing() -> None:
    root = _test_root("owlv2_loud_fail")
    cfg = _write_yaml(
        root / "owlv2_missing_dataset.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root / "missing_root"),
                "ann_file": str(root / "missing_ann.json"),
                "format_hint": "tao_or_coco_video",
            },
            "proposal": {"backend": "owlv2_hf", "backbone": "owlv2_hf"},
            "owlv2": {"device": "cuda:0"},
            "output": {"candidates": str(root / "audit_candidates.csv")},
        },
    )
    with pytest.raises(RuntimeError, match="dataset_not_ready"):
        run_phase2_propose(cfg)


def test_owlv2_status_reports_runtime_requirements() -> None:
    root = _test_root("owlv2_status")
    cfg = _write_yaml(
        root / "owlv2_status.yaml",
        {
            "proposal": {"backend": "owlv2_hf"},
            "owlv2": {
                "model": "google/owlv2-base-patch16-ensemble",
                "device": "cuda:0",
                "cache_dir": str(root / "hf_cache"),
            },
        },
    )
    status = owlv2_status(cfg)
    assert status["backend"] == "OWLv2"
    assert status["model"] == "google/owlv2-base-patch16-ensemble"
    assert status["cuda_required"] is True
    assert "ready" in status


def test_phase3_matrix_release_audit_exports_unsupported_template() -> None:
    root = _test_root("matrix_release_audit")
    universe = root / "candidate_universe.csv"
    rows = []
    for idx, video_id in enumerate(range(1, 5)):
        rows.append(
            {
                "dataset": "OVT-B",
                "video_id": video_id,
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 3,
                "score": 1.0 - idx * 0.05,
                "candidate_rank": idx + 1,
                "is_unmatched": idx == 0,
                "is_matched_to_gt": idx != 0,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            }
        )
    _write_candidate_universe(universe, rows)
    output_dir = root / "phase3_owlv2"
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"method": "parc_track_gamma_tuned_uniform_scs", "path_id": "p0", "e_value": 20.0, "p_any": 0.01, "p_block": 0.01},
            {"method": "parc_track_gamma_tuned_uniform_scs", "path_id": "p1", "e_value": 20.0, "p_any": 0.01, "p_block": 0.01},
            {"method": "parc_track_gamma_tuned_uniform_scs", "path_id": "p2", "e_value": 1.0, "p_any": 1.0, "p_block": 1.0},
            {"method": "parc_track_gamma_tuned_uniform_scs", "path_id": "p3", "e_value": 1.0, "p_any": 1.0, "p_block": 1.0},
        ]
    ).to_csv(output_dir / "candidate_evalues_alpha0p1_seed0.csv", index=False)
    cfg = _write_yaml(
        root / "phase3_owlv2_matrix.yaml",
        {
            "dataset": {"name": "OVT-B"},
            "splits": {"tune_ratio": 0.0, "cal_ratio": 0.0, "seed": 0},
            "risk": {"alpha1": 0.10},
            "matrix": {"alpha1": [0.10], "seeds": [0], "candidate_budget_M": [2]},
            "input": {"candidate_universe": str(universe), "audit_labels": str(root / "missing_labels.csv")},
            "output": {"output_dir": str(output_dir)},
            "release_audit": {
                "candidate_budget_M": 2,
                "alpha1": [0.10],
                "seeds": [0],
                "out": str(output_dir / "release_audit_unsupported.csv"),
                "labels_out": str(output_dir / "release_audit_unsupported_labels.csv"),
            },
        },
    )
    summary = export_matrix_release_audit_candidates(cfg, unsupported_only=True)
    audit_rows = pd.read_csv(output_dir / "release_audit_unsupported.csv")
    label_rows = pd.read_csv(output_dir / "release_audit_unsupported_labels.csv")
    assert summary["rows"] == 1
    assert summary["needs_audit_rows"] == 1
    assert audit_rows["path_id"].tolist() == ["p0"]
    assert label_rows["path_id"].tolist() == ["p0"]


def test_tuned_m_selection_uses_tune_split_and_writes_protocol() -> None:
    root = _test_root("tuned_m")
    ann_path = _write_tiny_tracking_dataset(root, "ovtb_ann.json", videos=18)
    universe = root / "candidate_universe.csv"
    rows = []
    for idx, video_id in enumerate(range(1, 19)):
        rows.append(
            {
                "dataset": "OVT-B",
                "video_id": video_id,
                "path_id": f"p{idx}",
                "query": "object",
                "category_id": 3,
                "score": 1.0 - idx * 0.01,
                "candidate_rank": idx + 1,
                "is_unmatched": idx % 4 != 0,
                "is_matched_to_gt": idx % 4 == 0,
                "verified_positive_for_calibration": "no",
                "cell_id": "global",
            }
        )
    _write_candidate_universe(universe, rows)
    labels = root / "audit_labels.csv"
    with labels.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_LABEL_COLUMNS)
        writer.writeheader()
    cfg_path = _write_yaml(
        root / "phase3_tune_m_fixture.yaml",
        {
            "dataset": {
                "name": "OVT-B",
                "root": str(root),
                "ann_file": str(ann_path),
                "format_hint": "tao_or_coco_video",
            },
            "splits": {"tune_ratio": 0.5, "cal_ratio": 0.25, "seed": 0},
            "risk": {"alpha1": 0.20},
            "release_grid": {"times_sec": [2.0]},
            "calibration": {"empty_block_policy": "coverage_conditional", "use_verified_positive_for_calibration": True},
            "selector": {"candidate_budget_sweep": [3, 5]},
            "matrix": {"alpha1": [0.20], "seeds": [0], "candidate_budget_M": [3, 5]},
            "tune_selection": {"internal_cal_ratio": 0.5, "fallback_M": 5, "out": str(root / "tuned_m_selection.csv")},
            "input": {"candidate_universe": str(universe), "audit_labels": str(labels)},
            "output": {"output_dir": str(root / "phase3_ovtb")},
        },
    )
    summary = run_tuned_m_selection(cfg_path)
    assert summary["status"] == "completed"
    table = pd.read_csv(root / "tuned_m_selection.csv")
    assert {"alpha", "alpha1", "seed", "method", "selected_M_by_tune", "selection_protocol", "selection_status"}.issubset(table.columns)
    assert "best_on_test_grid" not in set(table["selection_protocol"].astype(str))
    assert "parc_track_gamma_tuned_uniform_scs" in set(table["method"])


def test_clear_mot_idsw_evaluator_counts_switches_and_tightness() -> None:
    events = pd.DataFrame(
        [
            {"variant": "full", "video_id": "v1", "frame_index": 0, "gt_id": "g1", "pred_id": "p1", "badlink_ub": 1, "misscont_ub": 0, "gap_sensor": 0},
            {"variant": "full", "video_id": "v1", "frame_index": 1, "gt_id": "g1", "pred_id": "p1", "badlink_ub": 0, "misscont_ub": 0, "gap_sensor": 0},
            {"variant": "full", "video_id": "v1", "frame_index": 2, "gt_id": "g1", "pred_id": "p2", "badlink_ub": 1, "misscont_ub": 1, "gap_sensor": 0},
            {"variant": "full", "video_id": "v1", "frame_index": 3, "gt_id": "g1", "pred_id": "p2", "badlink_ub": 0, "misscont_ub": 0, "gap_sensor": 0},
        ]
    )
    per_video, summary = evaluate_clear_mot_idsw(events, fps=30.0)
    row = per_video.iloc[0]
    assert int(row["actual_idsw"]) == 1
    assert float(row["certified_ub"]) == 3.0
    assert float(row["tightness"]) == 3.0
    assert int(summary["actual_idsw"].iloc[0]) == 1


def test_run_idsw_eval_writes_required_rows() -> None:
    root = _test_root("idsw_eval")
    events = root / "events.csv"
    with events.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["variant", "video_id", "frame_index", "gt_id", "pred_id", "badlink_ub", "misscont_ub", "gap_sensor"])
        writer.writeheader()
        writer.writerow({"variant": "no_skeleton", "video_id": "v1", "frame_index": 0, "gt_id": "g1", "pred_id": "p1", "badlink_ub": 1, "misscont_ub": 0, "gap_sensor": 0})
        writer.writerow({"variant": "no_skeleton", "video_id": "v1", "frame_index": 1, "gt_id": "g1", "pred_id": "p2", "badlink_ub": 1, "misscont_ub": 0, "gap_sensor": 0})
    cfg_path = _write_yaml(
        root / "phase3_idsw.yaml",
        {"input": {"idsw_events": str(events)}, "evaluator": {"fps": 30.0}, "output": {"output_dir": str(root / "idsw")}},
    )
    result = run_idsw_eval(cfg_path)
    assert result["status"] == "completed"
    table = pd.read_csv(root / "idsw" / "idsw_summary.csv")
    assert {"actual_idsw_per_min", "badlink_ub", "misscont_ub", "gap_sensor", "certified_ub", "tightness_median"}.issubset(table.columns)


def test_release_core_report_copies_sources_and_writes_latex() -> None:
    root = _test_root("release_core_report")
    source = root / "table.csv"
    pd.DataFrame([{"method": "PARC full", "released": 1}]).to_csv(source, index=False)
    matrix = root / "matrix.csv"
    pd.DataFrame(
        [
            {
                "method": "PARC full",
                "alpha1": 0.10,
                "seed": 0,
                "candidate_budget_M": 150,
                "released": 2,
                "utr": 0.0,
                "conservative_ftr_uncertain_and_unlabeled_false": 0.0,
                "self_consistency_margin": 1.0,
                "empty_diagnostic": "",
            },
            {
                "method": "PARC full",
                "alpha1": 0.10,
                "seed": 1,
                "candidate_budget_M": 150,
                "released": 0,
                "utr": 0.0,
                "conservative_ftr_uncertain_and_unlabeled_false": "",
                "self_consistency_margin": "",
                "empty_diagnostic": "insufficient_high_e_mass_for_uniform_scs",
            },
        ]
    ).to_csv(matrix, index=False)
    cfg_path = _write_yaml(
        root / "phase3_report.yaml",
        {
            "sources": [str(source), str(root / "missing.csv")],
            "matrix_csv": str(matrix),
            "reporting": {"fixed_main_M": 150, "main_alpha1": 0.10},
            "output": {
                "output_dir": str(root / "milestone"),
                "docs_summary": str(root / "paper_results_summary.md"),
            },
        },
    )
    result = run_release_core_report(cfg_path)
    assert result["status"] == "completed"
    assert (root / "milestone" / "table.csv").exists()
    assert (root / "milestone" / "latex" / "table.tex").exists()
    assert (root / "milestone" / "table_main_fixed_m.csv").exists()
    assert (root / "milestone" / "table_main_tuned_m.csv").exists()
    assert (root / "milestone" / "table_best_m_diagnostic.csv").exists()
    assert (root / "milestone" / "table_seed_empty_diagnostics.csv").exists()
    tuned = pd.read_csv(root / "milestone" / "table_main_tuned_m.csv")
    assert set(tuned["selection_protocol"]) == {"requires_tune_selection_using_fixed_M_placeholder"}
    assert (root / "paper_results_summary.md").exists()
