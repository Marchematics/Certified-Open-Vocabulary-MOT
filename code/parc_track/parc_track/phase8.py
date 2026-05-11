from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from .adapters.datasets import ensure_data_output, load_yaml, write_json
from .ovtrack_adapter import PUBLISHED_DATASETS, PUBLISHED_TRACKERS, convert_published_tracker_predictions
from .phase2 import (
    AUDIT_LABEL_COLUMNS,
    _best_mass_summary,
    _load_universe_with_labels,
    _scs_release_count,
    _split_video_ids,
    run_real_certify,
)
from .phase3 import _label_metrics


DATA_ROOT = Path(".")
PARC_METHOD = "parc_track_gamma_tuned_uniform_scs"
TRACKERS = ("ovtrack", "ovtb_baseline", "ovtr")
DATASETS = ("ovtb", "tao")


def _safe_name(value: Any) -> str:
    return str(value).replace("/", "_").replace(" ", "_").replace(".", "p").replace("+", "plus")


def _write_yaml(path: Path, data: dict[str, Any]) -> Path:
    out = ensure_data_output(path)
    with out.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    return out


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    return pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame()


def _dataset_spec(dataset: str) -> dict[str, Any]:
    key = dataset.lower().replace("-", "")
    if key in {"ovtb", "ovt_b"}:
        return PUBLISHED_DATASETS["ovtb"]
    if key == "tao":
        return PUBLISHED_DATASETS["tao"]
    raise ValueError(f"unknown published-tracker dataset: {dataset}")


def _tracker_spec(tracker: str) -> dict[str, Any]:
    key = tracker.lower()
    if key not in PUBLISHED_TRACKERS:
        raise ValueError(f"unknown published tracker: {tracker}")
    return PUBLISHED_TRACKERS[key]


def _default_pair_dir(output_root: str | Path | None, tracker: str, dataset: str) -> Path:
    root = Path(output_root or DATA_ROOT / "outputs/phase8_published_trackers")
    return root / tracker / dataset


def _matrix_config(
    *,
    tracker: str,
    dataset: str,
    out_dir: Path,
    candidate_universe: Path | None = None,
    audit_labels: Path | None = None,
    alphas: list[float] | None = None,
    seeds: list[int] | None = None,
    requested_m: int = 150,
) -> dict[str, Any]:
    ds = _dataset_spec(dataset)
    tracker_display = _tracker_spec(tracker)["display_name"]
    return {
        "tracker": {"name": tracker, "display_name": tracker_display},
        "dataset": {
            "name": ds["display_name"],
            "root": str(ds["root"]),
            "ann_file": str(ds["ann_file"]),
            "format_hint": ds.get("format_hint", "tao_or_coco_video"),
        },
        "splits": {"tune_ratio": 0.10, "cal_ratio": 0.50, "test_ratio": 0.40, "seed": 0},
        "risk": {"alpha1": 0.10},
        "release_grid": {"times_sec": [2.0], "weights": "uniform"},
        "calibration": {"empty_block_policy": "coverage_conditional", "use_verified_positive_for_calibration": True},
        "e_calibrator": {
            "type": "power",
            "gamma_selection": "effective_finite_resolution_tuned",
            "gamma_candidates": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.50],
        },
        "selector": {"type": "uniform_scs_greedy", "candidate_budget_sweep": [requested_m]},
        "matrix": {"alpha1": alphas or [0.10, 0.20], "seeds": seeds or [0, 1, 2], "candidate_budget_M": [requested_m]},
        "input": {
            "candidate_universe": str(candidate_universe or out_dir / "candidate_universe.csv"),
            "audit_labels": str(audit_labels or out_dir / "audit_labels.csv"),
        },
        "output": {"output_dir": str(out_dir), "candidate_nodes": str(out_dir / "candidate_nodes.csv")},
    }


def write_published_tracker_matrix_config(
    tracker: str,
    dataset: str,
    out_dir: str | Path,
    *,
    config_path: str | Path | None = None,
    requested_m: int = 150,
) -> dict[str, Any]:
    out = ensure_data_output(out_dir)
    cfg = _matrix_config(tracker=tracker, dataset=dataset, out_dir=out, requested_m=requested_m)
    cfg_path = Path(config_path or DATA_ROOT / f"configs/phase8_published_{tracker}_{dataset}_matrix.yaml")
    _write_yaml(cfg_path, cfg)
    return {"status": "completed", "config": str(cfg_path), "output_dir": str(out)}


def convert_published_tracker(
    *,
    tracker: str,
    dataset: str,
    pred_path: str | Path,
    out_dir: str | Path | None = None,
    ann_file: str | Path | None = None,
    dataset_root: str | Path | None = None,
    frame_subdir: str | None = None,
    config_out: str | Path | None = None,
) -> dict[str, Any]:
    tracker = tracker.lower()
    dataset = dataset.lower().replace("-", "")
    ds = _dataset_spec(dataset)
    out = ensure_data_output(out_dir or _default_pair_dir(None, tracker, dataset))
    summary = convert_published_tracker_predictions(
        pred_path=pred_path,
        ann_file=ann_file or ds["ann_file"],
        out_dir=out,
        tracker_name=tracker,
        dataset_name=ds["display_name"],
        dataset_root=dataset_root or ds["root"],
        frame_subdir=ds["frame_subdir"] if frame_subdir is None else frame_subdir,
    )
    config_summary = write_published_tracker_matrix_config(
        tracker,
        dataset,
        out,
        config_path=config_out,
    )
    summary["matrix_config"] = config_summary["config"]
    return summary


def inspect_published_tracker_sources(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = ensure_data_output(output_dir or DATA_ROOT / "outputs/phase8_published_trackers")
    local_repos = {
        "ovtrack": DATA_ROOT / "repos/ovtrack",
        "ovtb_baseline": DATA_ROOT / "repos/OVT-B-Dataset",
        "ovtr": DATA_ROOT / "repos/OVTR",
    }
    rows: list[dict[str, Any]] = []
    for tracker in TRACKERS:
        spec = _tracker_spec(tracker)
        repo_path = local_repos[tracker]
        candidate_files: list[str] = []
        if repo_path.exists():
            for child in repo_path.rglob("*"):
                if not child.is_file():
                    continue
                name = child.name.lower()
                rel = str(child.relative_to(repo_path))
                if child.suffix.lower() in {".json", ".pkl", ".pickle", ".zip"} and any(
                    token in name or token in rel.lower() for token in ("pred", "result", "eval", "teta")
                ):
                    candidate_files.append(rel)
        for dataset in DATASETS:
            pair_dir = _default_pair_dir(out, tracker, dataset)
            rows.append(
                {
                    "tracker": tracker,
                    "tracker_display_name": spec["display_name"],
                    "dataset": dataset,
                    "repo": spec.get("repo"),
                    "local_repo": str(repo_path),
                    "local_repo_status": "present" if repo_path.exists() else "missing_local_clone",
                    "candidate_prediction_files": candidate_files[:200],
                    "expected_pair_dir": str(pair_dir),
                    "status": "requires_prediction_or_official_model_run",
                }
            )
    report = {
        "status": "completed",
        "note": "This inspection never fabricates tracker outputs. Missing predictions require official model runs in separate tracker environments.",
        "rows": rows,
    }
    write_json(out / "published_tracker_source_report.json", report)
    return report


def scaffold_published_tracker_experiments(output_dir: str | Path | None = None) -> dict[str, Any]:
    root = ensure_data_output(output_dir or DATA_ROOT / "outputs/phase8_published_trackers")
    run_rows: list[dict[str, Any]] = []
    for tracker in TRACKERS:
        for dataset in DATASETS:
            out = ensure_data_output(root / tracker / dataset)
            config = write_published_tracker_matrix_config(
                tracker,
                dataset,
                out,
                config_path=DATA_ROOT / f"configs/phase8_published_{tracker}_{dataset}_matrix.yaml",
            )
            tracker_spec = _tracker_spec(tracker)
            dataset_spec = _dataset_spec(dataset)
            manifest = {
                "status": "requires_prediction_or_official_model_run",
                "tracker": tracker,
                "tracker_display_name": tracker_spec["display_name"],
                "tracker_repo": tracker_spec["repo"],
                "dataset": dataset,
                "dataset_display_name": dataset_spec["display_name"],
                "expected_prediction_format": "TAO/TETA COCO-VID rows: image_id, video_id, track_id, category_id, bbox, score.",
                "matrix_config": config["config"],
                "conversion_command_template": (
                    "python -m parc_track.cli phase8 published-trackers convert "
                    f"--tracker {tracker} --dataset {dataset} --pred PATH_TO_PREDICTIONS "
                    f"--out-dir {out}"
                ),
                "official_run_note": "Run the official tracker in an isolated environment; write command logs here before conversion.",
            }
            write_json(out / "run_manifest.json", manifest)
            (out / "official_command_log.md").write_text(
                f"# {tracker_spec['display_name']} on {dataset_spec['display_name']}\n\n"
                "Status: requires official prediction generation or a public prediction file.\n\n"
                "Do not silently substitute another proposal generator.\n",
                encoding="utf-8",
            )
            run_rows.append(manifest)
    report = {"status": "completed", "output_root": str(root), "pairs": len(run_rows), "runs": run_rows}
    write_json(root / "RUN_REPORT.json", report)
    (root / "RUN_REPORT.md").write_text(
        "# Published OVMOT Tracker Certification Scaffold\n\n"
        "This scaffold prepares all tracker/dataset directories, but it does not fabricate official predictions. "
        "Each pair remains `requires_prediction_or_official_model_run` until a tracker JSON/PKL is converted.\n",
        encoding="utf-8",
    )
    return report


def _m_effective_for_seed(cfg: dict[str, Any], requested_m: int, seed: int) -> tuple[int, int, pd.DataFrame]:
    universe = _load_universe_with_labels(cfg)
    if universe.empty:
        return 0, 0, universe
    split_cfg = json.loads(json.dumps(cfg))
    split_cfg.setdefault("splits", {})["seed"] = seed
    split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), split_cfg)
    universe["split"] = universe["video_id"].astype(int).map(split_map)
    test = universe[universe["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).copy()
    test_count = int(len(test))
    return min(int(requested_m), test_count), test_count, test


def _raw_topm_row(
    *,
    cfg: dict[str, Any],
    tracker: str,
    dataset: str,
    alpha: float,
    seed: int,
    requested_m: int,
    m_effective: int,
    test_count: int,
    test_pool: pd.DataFrame,
) -> dict[str, Any]:
    budget_for_math = max(1, int(m_effective))
    selected = test_pool.head(int(m_effective)).copy() if m_effective > 0 else test_pool.iloc[[]].copy()
    metrics = _label_metrics(selected, budget_for_math)
    return {
        "tracker": tracker,
        "dataset": dataset,
        "method": "raw_tracker_topM",
        "base_method": "raw_tracker_topM",
        "alpha1": alpha,
        "seed": seed,
        "M_requested": requested_m,
        "M_effective": m_effective,
        "candidate_budget_M": budget_for_math,
        "real_test_candidates": test_count,
        "raw_release": int(metrics["released"]),
        "parc_release": None,
        "mass_ratio": None,
        "best_mass_ratio": None,
        "self_consistency_margin": None,
        "HOTA": None,
        "IDF1": None,
        "MOTA": None,
        **metrics,
    }


def _parc_rows_from_run(
    *,
    cfg: dict[str, Any],
    run_cfg: dict[str, Any],
    tracker: str,
    dataset: str,
    alpha: float,
    seed: int,
    requested_m: int,
    m_effective: int,
    test_count: int,
    test_pool: pd.DataFrame,
) -> list[dict[str, Any]]:
    summary_path = Path(run_cfg["output"]["real_cert_summary"])
    evalue_path = Path(run_cfg["output"]["candidate_evalues"])
    cert = _read_csv(summary_path)
    evalues = _read_csv(evalue_path)
    rows: list[dict[str, Any]] = []
    if cert.empty:
        return rows
    budget_for_math = max(1, int(m_effective))
    parc_e = evalues[evalues["method"].astype(str) == PARC_METHOD].copy() if not evalues.empty and "method" in evalues else pd.DataFrame()
    values: list[float] = []
    if not parc_e.empty and not test_pool.empty:
        merged = test_pool.head(int(m_effective)).merge(parc_e[["path_id", "e_value"]], on="path_id", how="left")
        merged["e_value"] = pd.to_numeric(merged.get("e_value", 0.0), errors="coerce").fillna(0.0)
        values = merged["e_value"].astype(float).tolist()
    mass = _best_mass_summary(values, alpha1=alpha, candidate_budget_m=budget_for_math)
    for _, source in cert.iterrows():
        if str(source.get("method", "")) != PARC_METHOD:
            continue
        row = source.to_dict()
        row.update(
            {
                "tracker": tracker,
                "dataset": dataset,
                "method": "parc_wrapped",
                "base_method": PARC_METHOD,
                "alpha1": alpha,
                "seed": seed,
                "M_requested": requested_m,
                "M_effective": m_effective,
                "candidate_budget_M": budget_for_math,
                "real_test_candidates": test_count,
                "raw_release": None,
                "parc_release": int(pd.to_numeric(source.get("released", 0), errors="coerce") or 0),
                "mass_ratio": mass["best_mass_ratio"],
                "best_mass_ratio": mass["best_mass_ratio"],
                "HOTA": None,
                "IDF1": None,
                "MOTA": None,
            }
        )
        rows.append(row)
    return rows


def run_published_tracker_matrix(config_path: str | Path) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    tracker = str(cfg.get("tracker", {}).get("name", "published_tracker")).lower()
    dataset_name = str(cfg.get("dataset", {}).get("name", "dataset"))
    dataset = "tao" if "tao" in dataset_name.lower() else "ovtb" if "ovt" in dataset_name.lower() else dataset_name.lower()
    matrix = cfg.get("matrix", {})
    alphas = [float(value) for value in matrix.get("alpha1", [cfg.get("risk", {}).get("alpha1", 0.10)])]
    seeds = [int(value) for value in matrix.get("seeds", [cfg.get("splits", {}).get("seed", 0)])]
    requested_ms = [int(value) for value in matrix.get("candidate_budget_M", [150])]
    requested_m = int(requested_ms[0])
    output_dir = ensure_data_output(cfg.get("output", {}).get("output_dir", _default_pair_dir(None, tracker, dataset)))
    config_dir = ensure_data_output(output_dir / "run_configs")

    universe_path = Path(cfg.get("input", {}).get("candidate_universe", output_dir / "candidate_universe.csv"))
    if not universe_path.exists():
        summary = {
            "status": "requires_converted_candidate_universe",
            "config": str(config_path),
            "candidate_universe": str(universe_path),
        }
        write_json(output_dir / "published_tracker_matrix_summary.json", summary)
        return summary

    all_rows: list[dict[str, Any]] = []
    for alpha in alphas:
        for seed in seeds:
            m_effective, test_count, test_pool = _m_effective_for_seed(cfg, requested_m, seed)
            budget_for_math = max(1, int(m_effective))
            all_rows.append(
                _raw_topm_row(
                    cfg=cfg,
                    tracker=tracker,
                    dataset=dataset,
                    alpha=alpha,
                    seed=seed,
                    requested_m=requested_m,
                    m_effective=m_effective,
                    test_count=test_count,
                    test_pool=test_pool,
                )
            )
            run_cfg = json.loads(json.dumps(cfg))
            run_cfg.setdefault("risk", {})["alpha1"] = alpha
            run_cfg.setdefault("splits", {})["seed"] = seed
            run_cfg.setdefault("selector", {})["candidate_budget_sweep"] = [budget_for_math]
            run_cfg.setdefault("matrix", {})["candidate_budget_M"] = [budget_for_math]
            run_name = f"alpha{_safe_name(alpha)}_seed{seed}_Meff{budget_for_math}"
            run_cfg.setdefault("output", {})
            run_cfg["output"].update(
                {
                    "summary": str(output_dir / f"real_cert_{run_name}.json"),
                    "real_cert_summary": str(output_dir / f"real_cert_{run_name}.csv"),
                    "candidate_evalues": str(output_dir / f"candidate_evalues_{run_name}.csv"),
                    "cell_effective_n": str(output_dir / f"cell_effective_n_{run_name}.csv"),
                    "per_video_candidate_coverage": str(output_dir / f"per_video_candidate_coverage_{run_name}.csv"),
                }
            )
            run_cfg_path = _write_yaml(config_dir / f"{run_name}.yaml", run_cfg)
            run_real_certify(run_cfg_path)
            all_rows.extend(
                _parc_rows_from_run(
                    cfg=cfg,
                    run_cfg=run_cfg,
                    tracker=tracker,
                    dataset=dataset,
                    alpha=alpha,
                    seed=seed,
                    requested_m=requested_m,
                    m_effective=m_effective,
                    test_count=test_count,
                    test_pool=test_pool,
                )
            )

    table = pd.DataFrame(all_rows)
    matrix_csv = ensure_data_output(output_dir / "published_tracker_alpha_seed_matrix.csv")
    table.to_csv(matrix_csv, index=False)
    summary = {
        "status": "completed",
        "config": str(config_path),
        "tracker": tracker,
        "dataset": dataset,
        "matrix_csv": str(matrix_csv),
        "rows": int(len(table)),
        "alphas": alphas,
        "seeds": seeds,
        "M_requested": requested_m,
    }
    write_json(output_dir / "published_tracker_matrix_summary.json", summary)
    return summary


def export_published_tracker_release_audit(
    config_path: str | Path,
    *,
    out_csv: str | Path | None = None,
    labels_out: str | Path | None = None,
    unsupported_only: bool = True,
) -> dict[str, Any]:
    cfg = load_yaml(config_path)
    tracker = str(cfg.get("tracker", {}).get("name", "published_tracker")).lower()
    dataset_name = str(cfg.get("dataset", {}).get("name", "dataset"))
    output_dir = ensure_data_output(cfg.get("output", {}).get("output_dir", _default_pair_dir(None, tracker, dataset_name)))
    matrix = _read_csv(output_dir / "published_tracker_alpha_seed_matrix.csv")
    universe = _load_universe_with_labels(cfg)
    if matrix.empty or universe.empty:
        summary = {
            "status": "requires_matrix_and_universe",
            "matrix": str(output_dir / "published_tracker_alpha_seed_matrix.csv"),
        }
        write_json(output_dir / "release_audit_manifest.json", summary)
        return summary
    rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for _, result in matrix[matrix["method"].astype(str) == "parc_wrapped"].iterrows():
        released = int(pd.to_numeric(result.get("parc_release", result.get("released", 0)), errors="coerce") or 0)
        if released <= 0:
            continue
        alpha = float(result["alpha1"])
        seed = int(result["seed"])
        m_eff = int(result["M_effective"])
        run_name = f"alpha{_safe_name(alpha)}_seed{seed}_Meff{max(1, m_eff)}"
        evalues = _read_csv(output_dir / f"candidate_evalues_{run_name}.csv")
        if evalues.empty:
            continue
        method_e = evalues[evalues["method"].astype(str) == PARC_METHOD].copy()
        if method_e.empty:
            continue
        split_cfg = json.loads(json.dumps(cfg))
        split_cfg.setdefault("splits", {})["seed"] = seed
        split_map = _split_video_ids(universe["video_id"].astype(int).tolist(), split_cfg)
        scoped = universe.copy()
        scoped["split"] = scoped["video_id"].astype(int).map(split_map)
        test = scoped[scoped["split"] == "test"].sort_values(["candidate_rank", "score"], ascending=[True, False]).head(m_eff).copy()
        merged = test.merge(method_e[["path_id", "e_value"]], on="path_id", how="left")
        merged["e_value"] = pd.to_numeric(merged.get("e_value", 0.0), errors="coerce").fillna(0.0)
        k, tau, margin = _scs_release_count(merged["e_value"].astype(float).tolist(), alpha1=alpha, candidate_budget_m=max(1, m_eff))
        selected = merged.sort_values("e_value", ascending=False).head(k).copy() if k else merged.iloc[[]].copy()
        if unsupported_only and not selected.empty:
            selected = selected[
                (~selected["is_matched_to_gt"].astype(bool)) & (~selected["is_verified_positive"].astype(bool))
            ].copy()
        for rank, (_, row) in enumerate(selected.iterrows(), start=1):
            key = (str(row.get("dataset", dataset_name)), str(row["video_id"]), str(row["path_id"]))
            if key in seen:
                continue
            seen.add(key)
            label = str(row.get("label", "") or "").strip()
            needs_audit = label not in {"actually_true", "actually_false", "uncertain"}
            audit_row = {
                "tracker": tracker,
                "dataset": row.get("dataset", dataset_name),
                "video_id": row.get("video_id", ""),
                "path_id": row.get("path_id", ""),
                "query": row.get("query", ""),
                "category_id": row.get("category_id", ""),
                "score": row.get("score", ""),
                "matched_gt_id": row.get("matched_gt_id", ""),
                "matched_iou": row.get("matched_iou", ""),
                "temporal_overlap": row.get("temporal_overlap", ""),
                "frame_start": row.get("frame_start", ""),
                "frame_end": row.get("frame_end", ""),
                "method": "parc_wrapped",
                "alpha1": alpha,
                "seed": seed,
                "M_requested": int(result["M_requested"]),
                "M_effective": m_eff,
                "selected_rank": rank,
                "e_value": row.get("e_value", ""),
                "tau_k": tau if k else "",
                "self_consistency_margin": margin if k else "",
                "audit_label": label,
                "needs_audit": needs_audit,
                "verified_positive_for_calibration": row.get("verified_positive_for_calibration", ""),
            }
            rows.append(audit_row)
            if needs_audit:
                label_rows.append(
                    {
                        "dataset": audit_row["dataset"],
                        "video_id": audit_row["video_id"],
                        "path_id": audit_row["path_id"],
                        "label": "",
                        "reason": "",
                        "auditor": "",
                        "confidence": "",
                        "review_status": "",
                        "verified_positive_for_calibration": "",
                    }
                )
    out = ensure_data_output(out_csv or output_dir / "published_tracker_release_audit_unsupported.csv")
    labels = ensure_data_output(labels_out or output_dir / "published_tracker_release_audit_unsupported_labels.csv")
    pd.DataFrame(rows).to_csv(out, index=False)
    label_frame = pd.DataFrame(label_rows, columns=AUDIT_LABEL_COLUMNS)
    if not label_frame.empty:
        label_frame = label_frame.drop_duplicates(["dataset", "video_id", "path_id"], keep="last")
    label_frame.to_csv(labels, index=False)
    manifest = {
        "status": "completed",
        "config": str(config_path),
        "release_audit_csv": str(out),
        "label_template_csv": str(labels),
        "rows": int(len(rows)),
        "needs_audit_rows": int(len(label_rows)),
        "unsupported_only": unsupported_only,
    }
    write_json(output_dir / "release_audit_manifest.json", manifest)
    return manifest


def run_published_tracker_report(output_dir: str | Path | None = None) -> dict[str, Any]:
    root = ensure_data_output(output_dir or DATA_ROOT / "outputs/phase8_published_trackers")
    frames: list[pd.DataFrame] = []
    missing: list[str] = []
    for tracker in TRACKERS:
        for dataset in DATASETS:
            path = root / tracker / dataset / "published_tracker_alpha_seed_matrix.csv"
            if path.exists():
                frame = pd.read_csv(path)
                frame["source_matrix"] = str(path)
                frames.append(frame)
            else:
                missing.append(str(path))
    table = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    cert_csv = ensure_data_output(root / "table_published_tracker_certification.csv")
    table.to_csv(cert_csv, index=False)
    if table.empty:
        meanstd = pd.DataFrame()
    else:
        numeric_cols = [
            col
            for col in [
                "released",
                "parc_release",
                "raw_release",
                "utr",
                "audited_ftr_on_labeled_released",
                "conservative_ftr_uncertain_and_unlabeled_false",
                "mass_ratio",
                "self_consistency_margin",
                "HOTA",
                "IDF1",
                "MOTA",
            ]
            if col in table
        ]
        meanstd = (
            table.groupby(["tracker", "dataset", "method", "alpha1"], dropna=False)[numeric_cols]
            .agg(["mean", "std"])
            .reset_index()
        )
        meanstd.columns = [
            "_".join(str(part) for part in col if str(part)) if isinstance(col, tuple) else str(col)
            for col in meanstd.columns
        ]
    meanstd_csv = ensure_data_output(root / "table_published_tracker_meanstd.csv")
    meanstd.to_csv(meanstd_csv, index=False)
    report = {
        "status": "completed" if not missing else "completed_with_missing_pairs",
        "table_published_tracker_certification": str(cert_csv),
        "table_published_tracker_meanstd": str(meanstd_csv),
        "rows": int(len(table)),
        "missing_matrices": missing,
    }
    write_json(root / "published_tracker_report_manifest.json", report)
    return report
