#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
import yaml


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame()


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)


def combine_detector(detector_dir: Path, out_dir: Path, detector_name: str, shards: int) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    universe_parts = []
    node_parts = []
    score_parts = []
    audit_parts = []
    label_parts = []
    manifests = []
    for offset in range(shards):
        shard = detector_dir / f"shard_{offset}"
        universe = _read_csv(shard / "candidate_universe.csv")
        nodes = _read_csv(shard / "candidate_nodes.csv")
        scores = _read_csv(shard / "candidate_scores.csv")
        audit = _read_csv(shard / "audit_candidates.csv")
        labels = _read_csv(shard / "audit_labels.csv")
        if not universe.empty:
            universe["detector"] = detector_name
            universe_parts.append(universe)
        if not nodes.empty:
            nodes["detector"] = detector_name
            node_parts.append(nodes)
        if not scores.empty:
            scores["detector"] = detector_name
            score_parts.append(scores)
        if not audit.empty:
            audit["detector"] = detector_name
            audit_parts.append(audit)
        if not labels.empty:
            labels["detector"] = detector_name
            label_parts.append(labels)
        manifest = shard / "audit_manifest.json"
        if manifest.exists():
            manifests.append(str(manifest))
    universe = pd.concat(universe_parts, ignore_index=True, sort=False) if universe_parts else pd.DataFrame()
    if not universe.empty:
        sort_cols = [col for col in ("score", "candidate_rank") if col in universe.columns]
        ascending = [False if col == "score" else True for col in sort_cols]
        universe = universe.sort_values(sort_cols, ascending=ascending).reset_index(drop=True) if sort_cols else universe
        universe["candidate_rank"] = range(1, len(universe) + 1)
    nodes = pd.concat(node_parts, ignore_index=True, sort=False) if node_parts else pd.DataFrame()
    scores = pd.concat(score_parts, ignore_index=True, sort=False) if score_parts else pd.DataFrame()
    audit = pd.concat(audit_parts, ignore_index=True, sort=False) if audit_parts else pd.DataFrame()
    labels = pd.concat(label_parts, ignore_index=True, sort=False) if label_parts else pd.DataFrame()
    if not audit.empty:
        audit = audit.sort_values("score", ascending=False).head(500)
    if not labels.empty and "path_id" in labels.columns and not audit.empty and "path_id" in audit.columns:
        labels = labels[labels["path_id"].astype(str).isin(set(audit["path_id"].astype(str)))].copy()
    universe.to_csv(out_dir / "candidate_universe.csv", index=False)
    nodes.to_csv(out_dir / "candidate_nodes.csv", index=False)
    scores.to_csv(out_dir / "candidate_scores.csv", index=False)
    audit.to_csv(out_dir / "audit_candidates.csv", index=False)
    labels.to_csv(out_dir / "audit_labels.csv", index=False)
    summary = {
        "detector": detector_name,
        "candidate_universe": str(out_dir / "candidate_universe.csv"),
        "candidate_nodes": str(out_dir / "candidate_nodes.csv"),
        "candidate_scores": str(out_dir / "candidate_scores.csv"),
        "audit_candidates": str(out_dir / "audit_candidates.csv"),
        "audit_labels": str(out_dir / "audit_labels.csv"),
        "num_paths": int(len(universe)),
        "num_nodes": int(len(nodes)),
        "num_audit_candidates": int(len(audit)),
        "shard_manifests": manifests,
    }
    (out_dir / "combine_report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary


def write_matrix_config(detector_summary: dict, output_dir: Path, config_path: Path, detector_name: str) -> dict:
    cfg = {
        "dataset": {"name": "LVIS"},
        "splits": {"tune_ratio": 0.10, "cal_ratio": 0.50, "test_ratio": 0.40, "seed": 0},
        "risk": {"alpha1": 0.10},
        "release_grid": {"times_sec": [2.0], "weights": "uniform"},
        "calibration": {
            "type": "null_superset_block",
            "empty_block_policy": "coverage_conditional",
            "use_verified_positive_for_calibration": True,
            "fallback": "global_first",
        },
        "e_calibrator": {
            "type": "power",
            "gamma_selection": "effective_finite_resolution_tuned",
            "gamma_candidates": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.50],
        },
        "selector": {"type": "uniform_scs_greedy", "candidate_budget_sweep": [150]},
        "matrix": {"alpha1": [0.10, 0.20], "seeds": [0, 1, 2], "candidate_budget_M": [150]},
        "input": {
            "candidate_universe": detector_summary["candidate_universe"],
            "audit_labels": detector_summary["audit_labels"],
        },
        "output": {
            "output_dir": str(output_dir),
            "candidate_nodes": detector_summary["candidate_nodes"],
        },
        "reporting": {"generator": detector_name, "scope": "lvis_detection_length1"},
    }
    _write_yaml(config_path, cfg)
    return {"matrix_config": str(config_path), "matrix_output_dir": str(output_dir)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Combine 4-GPU LVIS detector shards and write matrix configs.")
    track_root = Path(os.environ.get("PARC_TRACK_ROOT", "."))
    repo_root = Path(os.environ.get("PARC_REPO_ROOT", "."))
    parser.add_argument("--root", default=str(track_root / "outputs/phase11_nmi/lvis_detection"))
    parser.add_argument("--config-dir", default=str(repo_root / "configs"))
    parser.add_argument("--shards", type=int, default=4)
    args = parser.parse_args()
    root = Path(args.root)
    config_dir = Path(args.config_dir)
    outputs = []
    for detector_slug, detector_name in (("groundingdino", "GroundingDINO"), ("owlv2", "OWLv2")):
        combined_dir = root / detector_slug
        summary = combine_detector(root / detector_slug, combined_dir, detector_name, args.shards)
        matrix_dir = combined_dir / "matrix"
        cfg_path = config_dir / f"phase11_lvis_{detector_slug}_matrix.yaml"
        summary.update(write_matrix_config(summary, matrix_dir, cfg_path, detector_name))
        outputs.append(summary)
    report = root / "lvis_shard_combine_report.json"
    report.write_text(json.dumps({"detectors": outputs}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"detectors": outputs, "report": str(report)}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
