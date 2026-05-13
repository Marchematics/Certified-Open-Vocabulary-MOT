from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .adapters.datasets import ensure_data_output, write_json


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()
RELIABILITY_DIR = DATA_ROOT / "outputs/milestones/reliability_fortress"
GENERALITY_DIR = DATA_ROOT / "outputs/milestones/generality_reliability"
PAPER_TABLE_DIR = RELIABILITY_DIR / "paper_tables"
SCALEUP_DIR = RELIABILITY_DIR / "statistical_scaleup"

TARGET_SEED_COUNT = 30
TARGET_SEEDS = list(range(TARGET_SEED_COUNT))
MAIN_DATASETS = ["OVT-B", "TAO", "BURST", "LVIS", "scientific_domain_dataset"]
MAIN_ALPHA = 0.10
MAIN_M = 150
SENSITIVITY_ALPHA = [0.05, 0.10, 0.20]
SENSITIVITY_M = [50, 100, 150, 300]


def _read_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=DATA_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def _rel(path: str | Path) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(DATA_ROOT).as_posix()
    except Exception:
        return path.as_posix()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value)


def _write_provenance(path: Path, sources: list[Path], started: float, notes: str = "") -> None:
    existing = [source for source in sources if source.exists()]
    write_json(
        path.with_suffix(path.suffix + ".provenance.json"),
        {
            "table": path.name,
            "repo_commit": _git_commit(),
            "command": "python -m parc_track.cli phase18 statistical-scaleup",
            "runtime_sec": round(time.time() - started, 6),
            "environment": "python",
            "random_seed": "bootstrap_seed_20260513_where_applicable",
            "source_files": [{"path": _rel(source), "sha256": _sha256(source)} for source in existing],
            "output_sha256": _sha256(path),
            "notes": notes,
        },
    )


def _write_csv(frame: pd.DataFrame, path: Path, sources: list[Path], started: float, notes: str = "") -> Path:
    out = ensure_data_output(path)
    frame.to_csv(out, index=False)
    _write_provenance(out, sources, started, notes)
    return out


def _bootstrap_ci(values: list[float], *, n_boot: int = 10_000, seed: int = 20260513) -> tuple[float, float, float]:
    clean = np.array([float(v) for v in values if v is not None and np.isfinite(float(v))], dtype=float)
    if clean.size == 0:
        return (float("nan"), float("nan"), float("nan"))
    mean = float(clean.mean())
    if clean.size == 1:
        return (mean, mean, mean)
    rng = np.random.default_rng(seed)
    samples = rng.choice(clean, size=(n_boot, clean.size), replace=True).mean(axis=1)
    low, high = np.percentile(samples, [2.5, 97.5])
    return (mean, float(low), float(high))


def _protocol_rows() -> list[dict[str, Any]]:
    return [
        {
            "requirement": "seed_count",
            "target": "30+ seeds for main statistical evidence",
            "current_protocol": "seeds 0/1/2 are current real-data main-result seeds; some synthetic checks use 100 seeds",
            "status": "scaleup_required",
            "next_action": "run main datasets/generators for seeds 0-29; keep current 3-seed tables as frozen preliminary evidence",
            "paper_use": "methods_protocol_and_limitations_until_30seed_rerun_completes",
        },
        {
            "requirement": "main_datasets",
            "target": "OVT-B + TAO + BURST + LVIS + one scientific domain dataset",
            "current_protocol": "OVT-B/TAO/BURST tracking and LVIS detection are present; scientific-domain dataset is not yet completed",
            "status": "one_dataset_missing",
            "next_action": "add a biodiversity/camera-trap or other scientific-domain release-time certification case study",
            "paper_use": "broad-journal desk-fit closeout requirement",
        },
        {
            "requirement": "baseline_families",
            "target": "raw top-M, thresholds, split conformal, CRC family, post-filter e-values, e-BH family, oracle upper bound",
            "current_protocol": "raw/top-M, score thresholds, split conformal p-value threshold, post-filter e-value, e-BH style, oracle rows are present; recent CRC/e-value variants need explicit family mapping and optional rerun",
            "status": "partially_complete",
            "next_action": "keep existing baselines; add CRC-family and e-value-family rows as paper-facing mappings or run full variants if needed",
            "paper_use": "main baseline table plus appendix related-method mapping",
        },
        {
            "requirement": "statistical_reporting",
            "target": "bootstrap 95% confidence intervals, not only mean/std",
            "current_protocol": "bootstrap CI generated from available seeds with status marking underpowered 3-seed groups",
            "status": "implemented_for_current_results_but_underpowered_until_30seed",
            "next_action": "refresh the CI table after 30-seed reruns",
            "paper_use": "current appendix/reviewer closeout; main once seed count reaches target",
        },
    ]


def _dataset_scope_rows() -> list[dict[str, Any]]:
    return [
        {
            "dataset": "OVT-B",
            "task": "open_vocabulary_multi_object_tracking",
            "domain_role": "main_tracking_benchmark",
            "current_status": "completed_main_results",
            "journal_target_status": "included",
            "next_action": "extend from 3 to 30 seeds for final statistical evidence",
        },
        {
            "dataset": "TAO",
            "task": "open_vocabulary_multi_object_tracking",
            "domain_role": "main_tracking_benchmark_and_stress_regime",
            "current_status": "completed_main_or_refusal_results",
            "journal_target_status": "included",
            "next_action": "extend from 3 to 30 seeds and keep refusal framing explicit",
        },
        {
            "dataset": "BURST",
            "task": "tracking_any_object_scaffold",
            "domain_role": "third_visual_tracking_dataset",
            "current_status": "completed_main_or_refusal_results",
            "journal_target_status": "included",
            "next_action": "extend from 3 to 30 seeds if used in main statistical table",
        },
        {
            "dataset": "LVIS",
            "task": "single_frame_open_vocabulary_detection",
            "domain_role": "non_tracking_cross_task_instantiation",
            "current_status": "completed_generality_positive_with_audit_pending_for_human_FTR",
            "journal_target_status": "included_as_cross_task_evidence",
            "next_action": "keep as main-text cross-task instantiation; do not claim human-audited LVIS FTR until LVIS audit is complete",
        },
        {
            "dataset": "scientific_domain_dataset",
            "task": "release_time_certification_case_study",
            "domain_role": "scientific_domain_anchor",
            "current_status": "missing",
            "journal_target_status": "required_for_strong_broad_journal_fit",
            "next_action": "run a small biodiversity/camera-trap or other scientific-domain release/refusal case study with public-safe artifacts",
        },
    ]


def _baseline_family_rows() -> list[dict[str, Any]]:
    return [
        {
            "baseline_family": "raw_topM_no_risk",
            "representative_method": "Raw top-M",
            "current_coverage": "implemented",
            "source_table": "table_baseline_comparison.csv; table_main_raw_vs_parc.csv",
            "journal_status": "main_baseline",
            "reference_anchor": "score-ranked deployment without statistical control",
            "notes": "No alpha control; used as utility/risk reference.",
        },
        {
            "baseline_family": "fixed_score_threshold",
            "representative_method": "Fixed score threshold",
            "current_coverage": "implemented",
            "source_table": "table_baseline_comparison.csv",
            "journal_status": "main_baseline",
            "reference_anchor": "fixed score filtering",
            "notes": "Does not assume cross-generator score comparability.",
        },
        {
            "baseline_family": "calibrated_score_threshold",
            "representative_method": "Per-generator calibrated score threshold",
            "current_coverage": "implemented",
            "source_table": "table_baseline_comparison.csv",
            "journal_status": "main_baseline",
            "reference_anchor": "per-generator calibration",
            "notes": "Score threshold calibrated independently per generator.",
        },
        {
            "baseline_family": "split_conformal_p_value",
            "representative_method": "Split conformal p-value threshold",
            "current_coverage": "implemented",
            "source_table": "table_baseline_comparison.csv",
            "journal_status": "main_baseline",
            "reference_anchor": "split conformal prediction / conformal p-values",
            "notes": "Path-level baseline; does not enforce SCS compatibility.",
        },
        {
            "baseline_family": "conformal_risk_control_crc",
            "representative_method": "CRC / selective conformal risk control family",
            "current_coverage": "mapped_to_existing_split_conformal_and_threshold_rows",
            "source_table": "table_baseline_family_mapping.csv",
            "journal_status": "reference_family_mapping_or_future_full_rerun",
            "reference_anchor": "Bates-style CRC and Angelopoulos-style risk-control variants",
            "notes": "Included as a family-level positioning row; full recent variant rerun remains optional before submission.",
        },
        {
            "baseline_family": "post_filter_e_value",
            "representative_method": "Post-filter e-value threshold",
            "current_coverage": "implemented",
            "source_table": "table_baseline_comparison.csv",
            "journal_status": "main_baseline",
            "reference_anchor": "e-value filtering without set-level SCS",
            "notes": "Separates e-value evidence from SCS selection.",
        },
        {
            "baseline_family": "e_bh_and_e_value_family",
            "representative_method": "e-BH style selection / tracklet e-BH",
            "current_coverage": "implemented_as_e_BH_style_selection; broader family mapped",
            "source_table": "table_baseline_comparison.csv",
            "journal_status": "main_baseline_plus_related_family_mapping",
            "reference_anchor": "Vovk-Wang e-values and Wang-Ramdas e-BH style control",
            "notes": "Current evidence includes e-BH style baseline; paper should distinguish from full dependence-aware variants.",
        },
        {
            "baseline_family": "oracle_true_upper_bound",
            "representative_method": "Oracle true upper bound",
            "current_coverage": "implemented_appendix",
            "source_table": "table_oracle_true_upper_bound_appendix.csv",
            "journal_status": "appendix_upper_bound",
            "reference_anchor": "oracle utility ceiling",
            "notes": "Not a deployable baseline; quantifies remaining utility gap.",
        },
    ]


def _main_rows_from_raw_vs_parc(source: Path) -> pd.DataFrame:
    frame = _read_csv(source)
    rows: list[dict[str, Any]] = []
    if frame.empty:
        return pd.DataFrame()
    for _, row in frame.iterrows():
        dataset = _text(row.get("dataset"))
        generator = _text(row.get("generator"))
        alpha = _num(row.get("certified_risk_level_alpha", row.get("alpha", MAIN_ALPHA)), MAIN_ALPHA)
        m = int(_num(row.get("M", MAIN_M), MAIN_M))
        seed = row.get("seed", "")
        if _text(seed) == "":
            continue
        seed_int = int(float(seed))
        rows.append(
            {
                "source_table": _rel(source),
                "dataset": dataset,
                "generator": generator,
                "policy": "PARC certified release",
                "certified_risk_level_alpha": alpha,
                "M": m,
                "seed": seed_int,
                "released": _num(row.get("parc_released"), float("nan")),
                "empirical_audited_FTR": _num(row.get("empirical_audited_FTR", row.get("parc_audited_FTR")), float("nan")),
                "conservative_label_uncertainty_FTR": _num(
                    row.get("conservative_label_uncertainty_FTR", row.get("parc_conservative_FTR")), float("nan")
                ),
                "mass_ratio": _num(row.get("mass_ratio", row.get("best_mass_ratio")), float("nan")),
                "HOTA_or_proxy": _num(row.get("HOTA_or_proxy"), float("nan")),
            }
        )
        rows.append(
            {
                "source_table": _rel(source),
                "dataset": dataset,
                "generator": generator,
                "policy": "Raw top-M/no risk",
                "certified_risk_level_alpha": alpha,
                "M": m,
                "seed": seed_int,
                "released": _num(row.get("raw_topM_released"), float("nan")),
                "empirical_audited_FTR": _num(row.get("raw_topM_audited_false_rate"), float("nan")),
                "conservative_label_uncertainty_FTR": _num(row.get("raw_topM_unsupported_rate"), float("nan")),
                "mass_ratio": float("nan"),
                "HOTA_or_proxy": _num(row.get("HOTA_or_proxy"), float("nan")),
            }
        )
    return pd.DataFrame(rows)


def _rows_from_baseline(source: Path) -> pd.DataFrame:
    frame = _read_csv(source)
    rows: list[dict[str, Any]] = []
    if frame.empty:
        return pd.DataFrame()
    for _, row in frame.iterrows():
        seed = row.get("seed", "")
        if _text(seed) == "":
            continue
        rows.append(
            {
                "source_table": _rel(source),
                "dataset": _text(row.get("dataset")),
                "generator": _text(row.get("generator")),
                "policy": _text(row.get("baseline")),
                "certified_risk_level_alpha": _num(row.get("certified_risk_level_alpha"), MAIN_ALPHA),
                "M": int(_num(row.get("M"), MAIN_M)),
                "seed": int(float(seed)),
                "released": _num(row.get("released"), float("nan")),
                "empirical_audited_FTR": _num(row.get("empirical_audited_FTR"), float("nan")),
                "conservative_label_uncertainty_FTR": _num(
                    row.get("conservative_FTR", row.get("conservative_label_uncertainty_FTR")), float("nan")
                ),
                "mass_ratio": _num(row.get("mass_ratio"), float("nan")),
                "HOTA_or_proxy": float("nan"),
            }
        )
    return pd.DataFrame(rows)


def _rows_from_lvis(source: Path) -> pd.DataFrame:
    frame = _read_csv(source)
    rows: list[dict[str, Any]] = []
    if frame.empty:
        return pd.DataFrame()
    for _, row in frame.iterrows():
        seed = row.get("seed", "")
        if _text(seed) in {"", "pooled"}:
            continue
        rows.append(
            {
                "source_table": _rel(source),
                "dataset": "LVIS",
                "generator": _text(row.get("detector")),
                "policy": _text(row.get("policy", "PARC certified release")),
                "certified_risk_level_alpha": _num(row.get("certified_risk_target_alpha"), MAIN_ALPHA),
                "M": int(_num(row.get("M"), MAIN_M)),
                "seed": int(float(seed)),
                "released": _num(row.get("released"), float("nan")),
                "empirical_audited_FTR": _num(row.get("empirical_audited_false_rate"), float("nan")),
                "conservative_label_uncertainty_FTR": _num(row.get("conservative_unknown_as_false_rate"), float("nan")),
                "mass_ratio": _num(row.get("mass_ratio"), float("nan")),
                "HOTA_or_proxy": float("nan"),
            }
        )
    return pd.DataFrame(rows)


def _collect_current_rows() -> tuple[pd.DataFrame, list[Path]]:
    sources = [
        PAPER_TABLE_DIR / "table_main_raw_vs_parc.csv",
        PAPER_TABLE_DIR / "table_baseline_comparison.csv",
        GENERALITY_DIR / "paper_tables/table_lvis_detection_main.csv",
        GENERALITY_DIR / "paper_tables/table_lvis_raw_detector_vs_parc.csv",
    ]
    parts = [
        _main_rows_from_raw_vs_parc(sources[0]),
        _rows_from_baseline(sources[1]),
        _rows_from_lvis(sources[2]),
        _rows_from_lvis(sources[3]),
    ]
    parts = [part for part in parts if not part.empty]
    if not parts:
        return pd.DataFrame(), sources
    combined = pd.concat(parts, ignore_index=True, sort=False)
    return combined, sources


def _seed_coverage(combined: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not combined.empty:
        group_cols = ["dataset", "generator", "policy", "certified_risk_level_alpha", "M"]
        for keys, group in combined.groupby(group_cols, dropna=False):
            seeds = sorted({int(s) for s in group["seed"].dropna().astype(int).tolist()})
            status = "meets_30_seed_target" if len(seeds) >= TARGET_SEED_COUNT else "needs_30_seed_rerun"
            rows.append(
                {
                    "dataset": keys[0],
                    "generator": keys[1],
                    "policy": keys[2],
                    "certified_risk_level_alpha": keys[3],
                    "M": keys[4],
                    "completed_seed_count": len(seeds),
                    "target_seed_count": TARGET_SEED_COUNT,
                    "missing_seed_count": max(0, TARGET_SEED_COUNT - len(seeds)),
                    "completed_seeds": " ".join(map(str, seeds)),
                    "target_seeds": "0-29",
                    "status": status,
                }
            )
    for dataset in MAIN_DATASETS:
        present = any(row.get("dataset") == dataset for row in rows)
        if not present:
            rows.append(
                {
                    "dataset": dataset,
                    "generator": "to_be_selected",
                    "policy": "PARC certified release",
                    "certified_risk_level_alpha": MAIN_ALPHA,
                    "M": MAIN_M,
                    "completed_seed_count": 0,
                    "target_seed_count": TARGET_SEED_COUNT,
                    "missing_seed_count": TARGET_SEED_COUNT,
                    "completed_seeds": "",
                    "target_seeds": "0-29",
                    "status": "missing_dataset_or_generator_for_journal_target",
                }
            )
    return pd.DataFrame(rows)


def _bootstrap_table(combined: pd.DataFrame) -> pd.DataFrame:
    if combined.empty:
        return pd.DataFrame(
            columns=[
                "dataset",
                "generator",
                "policy",
                "certified_risk_level_alpha",
                "M",
                "metric",
                "seed_count",
                "mean",
                "ci_low_95",
                "ci_high_95",
                "ci_status",
            ]
        )
    metrics = [
        "released",
        "empirical_audited_FTR",
        "conservative_label_uncertainty_FTR",
        "mass_ratio",
        "HOTA_or_proxy",
    ]
    rows: list[dict[str, Any]] = []
    group_cols = ["dataset", "generator", "policy", "certified_risk_level_alpha", "M"]
    for keys, group in combined.groupby(group_cols, dropna=False):
        seed_count = int(group["seed"].nunique())
        ci_status = "30seed_ready" if seed_count >= TARGET_SEED_COUNT else "current_completed_ci_not_30seed_final"
        for metric in metrics:
            if metric not in group.columns:
                continue
            values = pd.to_numeric(group[metric], errors="coerce").dropna().tolist()
            if not values:
                continue
            metric_seed = int(hashlib.sha256(metric.encode("utf-8")).hexdigest()[:6], 16)
            mean, low, high = _bootstrap_ci(values, seed=20260513 + metric_seed % 10_000)
            rows.append(
                {
                    "dataset": keys[0],
                    "generator": keys[1],
                    "policy": keys[2],
                    "certified_risk_level_alpha": keys[3],
                    "M": keys[4],
                    "metric": metric,
                    "seed_count": seed_count,
                    "mean": mean,
                    "ci_low_95": low,
                    "ci_high_95": high,
                    "ci_status": ci_status,
                    "statistical_reporting_note": "bootstrap over completed seeds; refresh after 30-seed rerun",
                }
            )
    return pd.DataFrame(rows)


def _write_markdown(scaleup_dir: Path, summary: dict[str, Any], started: float) -> Path:
    path = ensure_data_output(scaleup_dir / "STATISTICAL_SCALEUP_README.md")
    text = f"""# Statistical Scale-Up Protocol Closeout

This folder records the gap between the current frozen evidence and the requested
journal-scale evidence standard. It intentionally does not relabel current 3-seed
experiments as 30-seed experiments.

## Targets

- Main real-data seed target: **{TARGET_SEED_COUNT}+ seeds** (`0-29`).
- Main dataset target: OVT-B, TAO, BURST, LVIS, plus one scientific-domain dataset.
- Main protocol: `M={MAIN_M}`, `alpha={MAIN_ALPHA}`, with sensitivity `M={SENSITIVITY_M}` and `alpha={SENSITIVITY_ALPHA}`.
- Statistical reporting: bootstrap 95% confidence intervals with explicit seed-count status.

## Current Machine-Generated Tables

- `table_statistical_scaleup_protocol.csv`: target requirements, current status, and next actions.
- `table_seed_coverage.csv`: completed seed counts for each available dataset/generator/policy cell.
- `table_main_bootstrap_ci.csv`: bootstrap CIs over completed seeds; rows with fewer than 30 seeds are marked as preliminary.
- `table_dataset_scope_journal.csv`: dataset/task coverage and the missing scientific-domain anchor.
- `table_baseline_family_mapping.csv`: implemented and mapped baseline families, including CRC/e-value families.

## Status

Current completed seed groups: {summary.get("seed_groups", 0)}.
Groups already meeting the 30-seed target: {summary.get("groups_meeting_30_seed_target", 0)}.
Groups requiring 30-seed reruns: {summary.get("groups_needing_30_seed_rerun", 0)}.

The scientific-domain dataset row is deliberately marked as missing until a real
domain case study is run and frozen.
"""
    path.write_text(text, encoding="utf-8")
    _write_provenance(path, [], started, notes="Statistical scale-up protocol README.")
    return path


def run_phase18_statistical_scaleup(output_dir: str | None = None) -> dict[str, Any]:
    started = time.time()
    out_dir = Path(output_dir) if output_dir else SCALEUP_DIR
    out_dir = ensure_data_output(out_dir)

    combined, sources = _collect_current_rows()

    artifacts: list[Path] = []
    artifacts.append(
        _write_csv(
            pd.DataFrame(_protocol_rows()),
            out_dir / "table_statistical_scaleup_protocol.csv",
            sources,
            started,
            notes="Journal-scale requirements and current completion status.",
        )
    )
    seed_coverage = _seed_coverage(combined)
    artifacts.append(
        _write_csv(
            seed_coverage,
            out_dir / "table_seed_coverage.csv",
            sources,
            started,
            notes="Seed coverage against 30+ seed journal target; missing rows are explicit.",
        )
    )
    ci_table = _bootstrap_table(combined)
    artifacts.append(
        _write_csv(
            ci_table,
            out_dir / "table_main_bootstrap_ci.csv",
            sources,
            started,
            notes="Bootstrap 95% confidence intervals over completed seeds.",
        )
    )
    artifacts.append(
        _write_csv(
            pd.DataFrame(_dataset_scope_rows()),
            out_dir / "table_dataset_scope_journal.csv",
            sources,
            started,
            notes="Dataset coverage table for broad-journal fit; scientific-domain row is not fabricated.",
        )
    )
    artifacts.append(
        _write_csv(
            pd.DataFrame(_baseline_family_rows()),
            out_dir / "table_baseline_family_mapping.csv",
            sources,
            started,
            notes="Baseline family mapping including CRC and e-value/e-BH families.",
        )
    )
    summary = {
        "status": "completed",
        "output_dir": _rel(out_dir),
        "seed_groups": int(len(seed_coverage)),
        "groups_meeting_30_seed_target": int(seed_coverage["status"].eq("meets_30_seed_target").sum()) if not seed_coverage.empty else 0,
        "groups_needing_30_seed_rerun": int(seed_coverage["status"].ne("meets_30_seed_target").sum()) if not seed_coverage.empty else 0,
        "bootstrap_ci_rows": int(len(ci_table)),
        "scientific_domain_dataset_status": "missing",
        "artifacts": [_rel(path) for path in artifacts],
    }
    artifacts.append(_write_markdown(out_dir, summary, started))
    write_json(
        out_dir / "statistical_scaleup_summary.json",
        {
            **summary,
            "artifacts": [_rel(path) for path in artifacts],
            "repo_commit": _git_commit(),
            "runtime_sec": round(time.time() - started, 6),
        },
    )
    return {
        **summary,
        "artifacts": [_rel(path) for path in artifacts] + [_rel(out_dir / "statistical_scaleup_summary.json")],
    }
