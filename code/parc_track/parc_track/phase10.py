from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .adapters.datasets import ensure_data_output, write_json
from .phase3 import run_ovtb_matrix


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()


def _write_yaml(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _dataset_spec(dataset: str) -> dict[str, Any]:
    key = dataset.lower()
    if key in {"ovt-b", "ovtb"}:
        return {
            "dataset": {
                "name": "OVT-B",
                "root": str(DATA_ROOT / "data/OVT-B"),
                "ann_file": str(DATA_ROOT / "data/OVT-B/ovtb_ann.json"),
                "format_hint": "tao_or_coco_video",
            },
            "input": {
                "candidate_universe": str(DATA_ROOT / "outputs/phase2_full/candidate_universe.csv"),
                "audit_labels": "",
            },
            "output_nodes": str(DATA_ROOT / "outputs/phase2_full/candidate_nodes.csv"),
            "dataset_slug": "ovtb",
        }
    if key == "tao":
        return {
            "dataset": {
                "name": "TAO",
                "root": str(DATA_ROOT / "data/TAO"),
                "ann_file": str(DATA_ROOT / "data/TAO/annotations/trainval.json"),
                "format_hint": "tao",
            },
            "input": {
                "candidate_universe": str(DATA_ROOT / "outputs/phase3_tao_full/candidate_universe.csv"),
                "audit_labels": "",
            },
            "output_nodes": str(DATA_ROOT / "outputs/phase3_tao_full/candidate_nodes.csv"),
            "dataset_slug": "tao",
        }
    raise ValueError(f"unsupported dataset: {dataset}")


def _base_matrix_config(dataset: str, output_dir: Path, labels_path: Path, *, split_strategy: str = "random") -> dict[str, Any]:
    spec = _dataset_spec(dataset)
    return {
        "dataset": spec["dataset"],
        "splits": {
            "tune_ratio": 0.10,
            "cal_ratio": 0.50,
            "test_ratio": 0.40,
            "seed": 0,
            "strategy": split_strategy,
        },
        "risk": {"alpha1": 0.10},
        "release_grid": {"times_sec": [2.0], "weights": "uniform"},
        "calibration": {
            "empty_block_policy": "coverage_conditional",
            "use_verified_positive_for_calibration": True,
        },
        "e_calibrator": {
            "type": "power",
            "gamma_selection": "effective_finite_resolution_tuned",
            "gamma_candidates": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.50],
        },
        "selector": {"type": "uniform_scs_greedy", "candidate_budget_sweep": [150]},
        "matrix": {"alpha1": [0.10, 0.20], "seeds": [0, 1, 2], "candidate_budget_M": [150]},
        "input": {
            "candidate_universe": spec["input"]["candidate_universe"],
            "audit_labels": str(labels_path),
        },
        "output": {"output_dir": str(output_dir), "candidate_nodes": spec["output_nodes"]},
    }


def _read_final_audit_labels() -> pd.DataFrame:
    path = DATA_ROOT / "outputs/phase9_audit_benchmark/audit_labels_2000_human_reviewed.csv"
    labels = pd.read_csv(path)
    for column in ("dataset", "video_id", "path_id", "label", "verified_positive_for_calibration"):
        if column not in labels:
            labels[column] = ""
    labels["dataset"] = labels["dataset"].astype(str)
    labels["video_id"] = labels["video_id"].astype(str)
    labels["path_id"] = labels["path_id"].astype(str)
    labels["verified_positive_for_calibration"] = labels["verified_positive_for_calibration"].fillna("").astype(str).str.lower()
    labels["verified_positive_for_calibration"] = labels["verified_positive_for_calibration"].where(
        labels["verified_positive_for_calibration"].isin(["yes", "true", "1"]), "no"
    )
    return labels


def _write_dataset_labels(dataset: str, out_path: Path, *, removal_ratio: float = 1.0) -> Path:
    labels = _read_final_audit_labels()
    dataset_name = "OVT-B" if dataset.lower() in {"ovtb", "ovt-b"} else dataset.upper()
    labels = labels[labels["dataset"].astype(str).str.lower().eq(dataset_name.lower())].copy()
    labels = labels.drop_duplicates(["dataset", "video_id", "path_id"], keep="last")
    verified = labels["verified_positive_for_calibration"].isin(["yes", "true", "1"])
    verified_ids = labels.loc[verified, ["dataset", "video_id", "path_id"]].astype(str)
    keep_count = int(round(len(verified_ids) * float(removal_ratio)))
    keep_keys = set(
        tuple(row)
        for row in verified_ids.sort_values(["video_id", "path_id"]).head(keep_count).itertuples(index=False, name=None)
    )
    new_verified = []
    for row in labels[["dataset", "video_id", "path_id", "label", "verified_positive_for_calibration"]].astype(str).itertuples(index=False, name=None):
        key = row[:3]
        label = row[3]
        was_verified = row[4].lower() in {"yes", "true", "1"}
        new_verified.append("yes" if was_verified and key in keep_keys and label == "actually_true" else "no")
    labels["verified_positive_for_calibration"] = new_verified
    labels["review_status"] = "human_reviewed_v1_phase10_ratio"
    labels["auditor"] = labels.get("auditor", "user_human_review_v1")
    out = ensure_data_output(out_path)
    labels.to_csv(out, index=False)
    return out


def _parc_rows(matrix_path: Path, *, dataset: str, scenario: str, extra: dict[str, Any] | None = None) -> pd.DataFrame:
    frame = pd.read_csv(matrix_path)
    if "method" in frame:
        frame = frame[frame["method"].astype(str).eq("parc_track_gamma_tuned_uniform_scs")].copy()
    if "candidate_budget_M" in frame:
        frame = frame[pd.to_numeric(frame["candidate_budget_M"], errors="coerce").fillna(-1).astype(int).eq(150)].copy()
    rows = []
    for _, row in frame.iterrows():
        released = float(row.get("released", 0) or 0)
        alpha = float(row.get("alpha1", 0) or 0)
        m = float(row.get("candidate_budget_M", 150) or 150)
        selected_e = float(row.get("selected_e_min", 0) or 0)
        mass_ratio = alpha * released * selected_e / m if released > 0 and selected_e > 0 and m > 0 else 0.0
        out = {
            "dataset": dataset,
            "scenario": scenario,
            "alpha1": alpha,
            "seed": int(float(row.get("seed", -1))) if str(row.get("seed", "")).strip() != "" else -1,
            "method": row.get("method", ""),
            "M": int(m),
            "released": released,
            "UTR": float(row.get("utr", 0) or 0),
            "audited_FTR": row.get("audited_ftr_on_labeled_released", ""),
            "conservative_FTR": row.get("conservative_ftr_uncertain_and_unlabeled_false", ""),
            "unsupported_true": float(row.get("unsupported_actually_true", 0) or 0),
            "unsupported_false": float(row.get("unsupported_actually_false", 0) or 0),
            "unsupported_uncertain": float(row.get("unsupported_uncertain", 0) or 0),
            "unsupported_unlabeled": float(row.get("unsupported_unlabeled", 0) or 0),
            "mass_ratio": mass_ratio,
            "emax": row.get("emax_effective", row.get("max_observed_e", "")),
            "empty_reason": row.get("empty_reason", ""),
            "self_consistency_margin": row.get("self_consistency_margin", ""),
            "result_status": "actual_rerun",
        }
        if extra:
            out.update(extra)
        rows.append(out)
    return pd.DataFrame(rows)


def run_phase10_nonexchangeability_reruns(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase10_nonexchangeability")
    config_dir = ensure_data_output(DATA_ROOT / "configs/phase10")
    results = []
    runs = []
    for dataset in ("OVT-B", "TAO"):
        ds_slug = "ovtb" if dataset == "OVT-B" else "tao"
        labels_path = _write_dataset_labels(dataset, output_dir / f"{ds_slug}_final_human_labels.csv", removal_ratio=1.0)
        run_dir = output_dir / f"{ds_slug}_severe_sparse_annotation_shift"
        cfg = _base_matrix_config(dataset, run_dir, labels_path, split_strategy="severe_sparse_annotation_shift")
        cfg_path = _write_yaml(config_dir / f"phase10_{ds_slug}_severe_nonexchangeability.yaml", cfg)
        summary = run_ovtb_matrix(cfg_path)
        matrix_path = Path(summary["matrix_csv"])
        rows = _parc_rows(
            matrix_path,
            dataset=dataset,
            scenario="severe_sparse_annotation_shift",
            extra={"assumption_status": "assumption_boundary_actual_rerun", "split_strategy": "severe_sparse_annotation_shift"},
        )
        results.append(rows)
        runs.append({"dataset": dataset, "config": str(cfg_path), "summary": summary})
    table = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    out = ensure_data_output(output_dir / "table_nonexchangeability_severe_actual_results.csv")
    table.to_csv(out, index=False)
    manifest = {"status": "completed", "table": str(out), "runs": runs}
    write_json(output_dir / "phase10_nonexchangeability_manifest.json", manifest)
    return manifest


def run_phase10_null_inflation_reruns(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase10_null_inflation")
    config_dir = ensure_data_output(DATA_ROOT / "configs/phase10")
    results = []
    runs = []
    for ratio in (0.0, 0.25, 0.50, 0.75, 1.0):
        ratio_tag = str(ratio).replace(".", "p")
        labels_path = _write_dataset_labels("OVT-B", output_dir / f"ovtb_verified_ratio_{ratio_tag}_labels.csv", removal_ratio=ratio)
        run_dir = output_dir / f"ovtb_verified_ratio_{ratio_tag}"
        cfg = _base_matrix_config("OVT-B", run_dir, labels_path, split_strategy="random")
        cfg_path = _write_yaml(config_dir / f"phase10_ovtb_verified_ratio_{ratio_tag}.yaml", cfg)
        summary = run_ovtb_matrix(cfg_path)
        matrix_path = Path(summary["matrix_csv"])
        rows = _parc_rows(
            matrix_path,
            dataset="OVT-B",
            scenario="verified_positive_removal_ratio",
            extra={"verified_positive_removal_ratio": ratio, "label_interpretation": "uncertain_as_unknown"},
        )
        results.append(rows)
        runs.append({"ratio": ratio, "config": str(cfg_path), "summary": summary})
    table = pd.concat(results, ignore_index=True) if results else pd.DataFrame()
    out = ensure_data_output(output_dir / "table_null_inflation_verified_removal_actual_results.csv")
    table.to_csv(out, index=False)
    manifest = {"status": "completed", "table": str(out), "runs": runs}
    write_json(output_dir / "phase10_null_inflation_manifest.json", manifest)
    return manifest


def run_phase10_rerun_suite(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase10_reruns")
    nonex = run_phase10_nonexchangeability_reruns(DATA_ROOT / "outputs/phase10_nonexchangeability")
    null = run_phase10_null_inflation_reruns(DATA_ROOT / "outputs/phase10_null_inflation")
    summary = {"status": "completed", "nonexchangeability": nonex, "null_inflation": null}
    write_json(output_dir / "phase10_rerun_suite_summary.json", summary)
    return summary
