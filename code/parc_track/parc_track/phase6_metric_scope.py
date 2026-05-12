from __future__ import annotations

import hashlib
import json
import tarfile
import time
from pathlib import Path
from typing import Any

import pandas as pd

from .adapters.datasets import ensure_data_output, write_json
from .phase2 import _best_mass_summary, _load_universe_with_labels, _scs_release_count
from .phase3 import _label_metrics
from .phase4 import _base_entries, _load_cfg, _method_evalues, _select_from_evalues, _test_pool
from .phase5_trackeval import CONF_MATCHED_METHOD, CONF_METHOD, PARC_METHOD, run_trackeval_grid, run_trackeval_motchallenge


DATA_ROOT = Path(".")


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    return pd.read_csv(path) if path.exists() and path.stat().st_size > 0 else pd.DataFrame()


def _grounding_entries() -> list[dict[str, Any]]:
    return [entry for entry in _base_entries() if entry["generator"] == "GroundingDINO"]


def _entry(dataset: str) -> dict[str, Any]:
    for item in _grounding_entries():
        if item["dataset"] == dataset:
            return item
    raise ValueError(f"unknown GroundingDINO dataset: {dataset}")


def _load_labeled_universe(cfg: dict[str, Any]) -> pd.DataFrame:
    return _load_universe_with_labels(cfg)


def _evalue_pool(entry: dict[str, Any], alpha: float, seed: int, budget: int) -> tuple[pd.DataFrame, list[float]]:
    cfg = _load_cfg(entry)
    universe = _load_labeled_universe(cfg)
    e_alpha = alpha if alpha in {0.05, 0.10, 0.20} else 0.10
    evalues = _method_evalues(entry, e_alpha, seed)
    pool = _test_pool(cfg, universe, seed, budget)
    if pool.empty:
        return pool, []
    frame = pool.merge(evalues[["path_id", "e_value"]], on="path_id", how="left") if not evalues.empty else pool.copy()
    frame["e_value"] = pd.to_numeric(frame.get("e_value", 0.0), errors="coerce").fillna(0.0)
    return frame, frame["e_value"].astype(float).tolist()


def _controllability_rows(budget: int = 150) -> pd.DataFrame:
    alphas = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    rows: list[dict[str, Any]] = []
    for entry in _grounding_entries():
        cfg = _load_cfg(entry)
        universe = _load_labeled_universe(cfg)
        for alpha in alphas:
            for seed in [0, 1, 2]:
                pool, values = _evalue_pool(entry, alpha, seed, budget)
                k, tau, margin = _scs_release_count(values, alpha1=alpha, candidate_budget_m=budget)
                selected = pool.sort_values("e_value", ascending=False).head(k).copy() if k else pool.iloc[[]].copy()
                mass = _best_mass_summary(values, alpha1=alpha, candidate_budget_m=budget)
                rows.append(
                    {
                        "dataset": entry["dataset"],
                        "generator": entry["generator"],
                        "strategy": "PARC_certified_release",
                        "alpha1": alpha,
                        "seed": seed,
                        "candidate_budget_M": budget,
                        "tau_k": tau if k else None,
                        "self_consistency_margin": margin if k else None,
                        **mass,
                        **_label_metrics(selected, budget),
                    }
                )
                top_m = _test_pool(cfg, universe, seed, budget).copy()
                rows.append(
                    {
                        "dataset": entry["dataset"],
                        "generator": entry["generator"],
                        "strategy": "confidence_top_m_no_alpha_control",
                        "alpha1": alpha,
                        "seed": seed,
                        "candidate_budget_M": budget,
                        "tau_k": None,
                        "self_consistency_margin": None,
                        "best_mass_ratio": None,
                        "best_margin": None,
                        "released_unconstrained": None,
                        **_label_metrics(top_m, budget),
                    }
                )
    return pd.DataFrame(rows)


def _tao_m_scaling_rows() -> pd.DataFrame:
    entry = _entry("TAO")
    budget_grid = [150, 300, 500, 1000, 2000]
    rows: list[dict[str, Any]] = []
    for budget in budget_grid:
        for seed in [0, 1, 2]:
            pool, values = _evalue_pool(entry, 0.10, seed, budget)
            k, tau, margin = _scs_release_count(values, alpha1=0.10, candidate_budget_m=budget)
            selected = pool.sort_values("e_value", ascending=False).head(k).copy() if k else pool.iloc[[]].copy()
            mass = _best_mass_summary(values, alpha1=0.10, candidate_budget_m=budget)
            rows.append(
                {
                    "dataset": "TAO",
                    "generator": "GroundingDINO",
                    "alpha1": 0.10,
                    "seed": seed,
                    "candidate_budget_M": budget,
                    "tau_k": tau if k else None,
                    "self_consistency_margin": margin if k else None,
                    "feasible_by_mass_ratio": bool(float(mass["best_mass_ratio"]) >= 1.0),
                    **mass,
                    **_label_metrics(selected, budget),
                }
            )
    return pd.DataFrame(rows)


def _summarize_grouped(frame: pd.DataFrame, group_cols: list[str], out_path: Path) -> None:
    if frame.empty:
        pd.DataFrame().to_csv(out_path, index=False)
        return
    numeric = [
        col
        for col in [
            "released",
            "utr",
            "conservative_ftr_uncertain_and_unlabeled_false",
            "audited_ftr_on_labeled_released",
            "best_mass_ratio",
            "self_consistency_margin",
            "HOTA",
            "IDF1",
            "MOTA",
            "DetA",
            "AssA",
        ]
        if col in frame.columns
    ]
    grouped = frame.groupby(group_cols, dropna=False)[numeric].agg(["mean", "std"]).reset_index()
    grouped.columns = [
        "_".join(str(part) for part in col if str(part)) if isinstance(col, tuple) else str(col)
        for col in grouped.columns
    ]
    grouped.to_csv(out_path, index=False)


def _package_output(output_dir: Path) -> tuple[Path, str]:
    packages = ensure_data_output(DATA_ROOT / "outputs/packages")
    tar_path = packages / "metric_scope.tar.gz"
    if tar_path.exists():
        tar_path.unlink()
    with tarfile.open(tar_path, "w:gz") as tar:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                tar.add(path, arcname=str(path.relative_to(DATA_ROOT)))
    digest = hashlib.sha256(tar_path.read_bytes()).hexdigest()
    (tar_path.with_suffix(tar_path.suffix + ".sha256")).write_text(f"{digest}  {tar_path.name}\n", encoding="utf-8")
    return tar_path, digest


def run_metric_scope_report(out_dir: str | Path | None = None) -> dict[str, Any]:
    output_dir = ensure_data_output(out_dir or DATA_ROOT / "outputs/phase6_metric_scope")
    start = time.perf_counter()

    hota_frames: list[pd.DataFrame] = []
    trackeval_runs: list[dict[str, Any]] = []
    # Standard full-GT numbers were already produced in phase5. Reuse them to
    # avoid re-running the slow TAO TrackEval path; this keeps Phase-6 focused on
    # the new scope diagnostics.
    phase5_standard = _read_csv(DATA_ROOT / "outputs/phase5_trackeval/table_trackeval_cross_dataset.csv")
    if not phase5_standard.empty:
        standard = phase5_standard.copy()
        standard["metric_scope"] = "standard"
        hota_frames.append(standard)
    else:
        for dataset in ["OVT-B", "TAO"]:
            result = run_trackeval_grid(output_dir, dataset=dataset, scope="standard")
            trackeval_runs.append(result)
            table = _read_csv(result["table"])
            if not table.empty:
                table["metric_scope"] = "standard"
                hota_frames.append(table)

    # OVT-B needs an explicit supported/category-relevant diagnostic. TAO's
    # standard phase5 table is already a supported-subset scaffold because TAO is
    # federated; duplicate those rows with a supported label for a clean paper
    # table.
    result = run_trackeval_grid(output_dir, dataset="OVT-B", scope="supported")
    trackeval_runs.append(result)
    ovtb_supported = _read_csv(result["table"])
    if not ovtb_supported.empty:
        ovtb_supported["metric_scope"] = "supported"
        hota_frames.append(ovtb_supported)
    if not phase5_standard.empty:
        tao_supported = phase5_standard[phase5_standard["dataset"].astype(str) == "TAO"].copy()
        if not tao_supported.empty:
            tao_supported["metric_scope"] = "supported"
            tao_supported["scope_note"] = "TAO supported scope reuses the phase5 supported-subset TrackEval export."
            hota_frames.append(tao_supported)

    size_frames: list[pd.DataFrame] = []
    for dataset in ["OVT-B", "TAO"]:
        for alpha in [0.10, 0.20]:
            for seed in [0, 1, 2]:
                parc_selected = _select_from_evalues(_entry(dataset), alpha, seed, 150)
                if len(parc_selected) == 0 or dataset == "TAO":
                    size_frames.append(
                        pd.DataFrame(
                            [
                                {
                                    "dataset": dataset,
                                    "generator": "GroundingDINO",
                                    "alpha1": alpha,
                                    "seed": seed,
                                    "candidate_budget_M": 150,
                                    "scope": "release_size",
                                    "metric_scope": "release_size",
                                    "method": PARC_METHOD,
                                    "status": "skipped_empty_parc_release"
                                    if len(parc_selected) == 0
                                    else "skipped_tao_release_size_trackeval_slow_path",
                                    "selected_count": int(len(parc_selected)),
                                    "release_size_k": int(len(parc_selected)),
                                }
                            ]
                        )
                    )
                    continue
                summary = run_trackeval_motchallenge(
                    dataset=dataset,
                    alpha=alpha,
                    seed=seed,
                    budget=150,
                    out_dir=output_dir,
                    methods=[PARC_METHOD, CONF_MATCHED_METHOD],
                    scope="release_size",
                    release_size_k=len(parc_selected),
                )
                table = _read_csv(summary["summary_csv"])
                if not table.empty:
                    table["metric_scope"] = "release_size"
                    size_frames.append(table)
    size_table = pd.concat(size_frames, ignore_index=True, sort=False) if size_frames else pd.DataFrame()
    if not size_table.empty:
        hota_frames.append(size_table.copy())

    hota_scope = pd.concat(hota_frames, ignore_index=True, sort=False) if hota_frames else pd.DataFrame()
    hota_csv = ensure_data_output(output_dir / "table_hota_scope.csv")
    hota_scope.to_csv(hota_csv, index=False)
    _summarize_grouped(
        hota_scope,
        ["dataset", "generator", "method", "alpha1", "metric_scope"],
        ensure_data_output(output_dir / "table_hota_scope_meanstd.csv"),
    )

    size_csv = ensure_data_output(output_dir / "table_size_matched_baseline.csv")
    size_table.to_csv(size_csv, index=False)
    _summarize_grouped(
        size_table,
        ["dataset", "generator", "method", "alpha1", "metric_scope"],
        ensure_data_output(output_dir / "table_size_matched_baseline_meanstd.csv"),
    )

    controllability = _controllability_rows(150)
    controllability_csv = ensure_data_output(output_dir / "table_alpha_controllability.csv")
    controllability.to_csv(controllability_csv, index=False)
    _summarize_grouped(
        controllability,
        ["dataset", "generator", "strategy", "alpha1"],
        ensure_data_output(output_dir / "table_alpha_controllability_meanstd.csv"),
    )

    tao_scaling = _tao_m_scaling_rows()
    tao_scaling_csv = ensure_data_output(output_dir / "table_tao_m_scaling.csv")
    tao_scaling.to_csv(tao_scaling_csv, index=False)
    _summarize_grouped(
        tao_scaling,
        ["dataset", "generator", "alpha1", "candidate_budget_M"],
        ensure_data_output(output_dir / "table_tao_m_scaling_meanstd.csv"),
    )

    feasible = tao_scaling[(tao_scaling["released"] > 0) & (tao_scaling["feasible_by_mass_ratio"].astype(bool))]
    tao_trackeval_summary = None
    if not feasible.empty:
        first_m = int(feasible.sort_values(["candidate_budget_M", "seed"]).iloc[0]["candidate_budget_M"])
        tao_trackeval_summary = run_trackeval_motchallenge(
            dataset="TAO",
            alpha=0.10,
            seed=0,
            budget=first_m,
            out_dir=output_dir,
            methods=[PARC_METHOD, CONF_METHOD],
            scope="supported",
        )

    runtime = time.perf_counter() - start
    run_report = "\n".join(
        [
            "# IJCV Metric-Scope Report",
            "",
            "PARC-Track is evaluated here as a certified release layer, not as a standalone HOTA-maximizing tracker.",
            "",
            "Generated files:",
            f"- {hota_csv.relative_to(DATA_ROOT)}",
            f"- {size_csv.relative_to(DATA_ROOT)}",
            f"- {controllability_csv.relative_to(DATA_ROOT)}",
            f"- {tao_scaling_csv.relative_to(DATA_ROOT)}",
            "",
            "Metric scope notes:",
            "- `standard`: honest full-GT OVT-B denominator; TAO remains supported-subset because of federated annotations.",
            "- `supported`: paper-facing supported/category-relevant scope.",
            "- `release_size`: appendix-only HOTA@K with GT limited to release-size matched longest tracks.",
            "",
            f"Runtime seconds: {runtime:.2f}",
            "",
        ]
    )
    report_path = ensure_data_output(output_dir / "RUN_REPORT.md")
    report_path.write_text(run_report, encoding="utf-8")

    tar_path, digest = _package_output(output_dir)
    summary = {
        "status": "completed",
        "output_dir": str(output_dir),
        "table_hota_scope": str(hota_csv),
        "table_size_matched_baseline": str(size_csv),
        "table_alpha_controllability": str(controllability_csv),
        "table_tao_m_scaling": str(tao_scaling_csv),
        "tao_first_feasible_trackeval": tao_trackeval_summary,
        "trackeval_runs": trackeval_runs,
        "package": str(tar_path),
        "package_sha256": digest,
        "runtime_sec": runtime,
    }
    write_json(output_dir / "metric_scope_summary.json", summary)
    return summary
