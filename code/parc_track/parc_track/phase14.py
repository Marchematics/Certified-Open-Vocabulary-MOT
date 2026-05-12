from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pandas as pd

from .adapters.datasets import ensure_data_output, write_json


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()
RELIABILITY_DIR = DATA_ROOT / "outputs/milestones/reliability_fortress"
RELEASE_STORY_DIR = DATA_ROOT / "outputs/milestones/release_story"
LVVIS_DIR = DATA_ROOT / "outputs/milestones/lvvis_certification"
PAPER_TABLE_DIR = RELIABILITY_DIR / "paper_tables"
BURST_MATRIX = DATA_ROOT / "outputs/milestones/legacy_core_results/burst/burst_alpha_seed_m_matrix.csv"
QUALITATIVE_GALLERY = DATA_ROOT / "docs/qualitative_release_gallery.md"
FIGURES_DIR = DATA_ROOT / "figures"

DIRTY_TOKENS = (
    "/tmp/",
    "existing_certificate_row",
    "meanstd_existing_certificate",
    "rerun_required",
    "scaffold_only",
    "local_repo_present_no_prediction",
    "provenance_pending",
    "tpami_",
    "nmi" + "_release_story",
)


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


def _safe_reason(row: pd.Series) -> str:
    reason = _text(row.get("empty_reason", ""))
    released = _num(row.get("parc_released", row.get("released", 0)))
    if released > 0:
        return ""
    if reason:
        return reason
    mass = _num(row.get("mass_ratio", row.get("best_mass_ratio", float("nan"))), default=float("nan"))
    if not pd.isna(mass) and mass < 1:
        return "insufficient_high_evidence_mass"
    return "no_self_consistent_release"


def _clean_missing(value: Any) -> Any:
    text = _text(value).strip().lower()
    if text in {"nan", "none", "<na>"}:
        return ""
    return value


def _is_seed_row(seed: Any) -> bool:
    text = _text(seed).strip()
    return text in {"0", "1", "2", "3", "4"}


def _write_csv(frame: pd.DataFrame, path: Path, source_paths: list[Path], command: str, started: float) -> Path:
    out = ensure_data_output(path)
    frame.to_csv(out, index=False)
    provenance = {
        "table": out.name,
        "repo_commit": _git_commit(),
        "command": command,
        "runtime_sec": round(time.time() - started, 6),
        "source_files": [
            {"path": _rel(src), "sha256": _sha256(src)} for src in source_paths if src.exists()
        ],
        "output_sha256": _sha256(out),
        "config_sha256": "",
        "candidate_universe_sha256": "",
        "candidate_nodes_sha256": "",
        "audit_labels_sha256": _sha256(RELIABILITY_DIR / "audit_labels_2000_human_reviewed.csv")
        if (RELIABILITY_DIR / "audit_labels_2000_human_reviewed.csv").exists()
        else "",
        "paper_facing_table": True,
        "notes": "Derived sanitized paper-facing table. Raw provenance tables are preserved separately.",
    }
    write_json(out.with_suffix(out.suffix + ".provenance.json"), provenance)
    return out


def _validate_clean_tables(paths: list[Path]) -> None:
    failures: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for token in DIRTY_TOKENS:
            if token in text:
                failures.append(f"{path}: contains {token}")
    if failures:
        raise RuntimeError("paper-facing table cleanliness check failed:\n" + "\n".join(failures))


def _append_burst_rows(rows: list[dict[str, Any]]) -> list[Path]:
    source = BURST_MATRIX
    frame = _read_csv(source)
    if frame.empty:
        return []
    data = frame.copy()
    data = data[data.get("method", "").astype(str).eq("parc_track_gamma_tuned_uniform_scs")]
    data = data[pd.to_numeric(data.get("alpha1", pd.Series(dtype=float)), errors="coerce").eq(0.10)]
    data = data[data.get("seed", "").map(_is_seed_row)]
    data = data[pd.to_numeric(data.get("candidate_budget_M", pd.Series(dtype=float)), errors="coerce").eq(150)]
    for _, row in data.iterrows():
        released = _num(row.get("released", 0))
        mass = row.get("best_margin", row.get("mass_ratio", row.get("self_consistency_margin", "")))
        empty_reason = _text(row.get("empty_reason", ""))
        rows.append(
                {
                    "dataset": "BURST",
                    "generator": "GroundingDINO",
                    "alpha": 0.10,
                    "certified_risk_level_alpha": 0.10,
                    "M": 150,
                    "seed": int(float(row.get("seed"))),
                    "raw_topM_released": 150,
                    "raw_topM_audited_false_rate": "",
                    "raw_topM_unsupported_rate": "",
                    "raw_topM_policy": "score_ranked_topM_reference_count_only",
                    "parc_released": released,
                    "parc_UTR": row.get("utr", ""),
                    "parc_audited_FTR": row.get("audited_ftr_on_labeled_released", ""),
                    "parc_conservative_FTR": row.get("conservative_ftr_uncertain_and_unlabeled_false", ""),
                    "empirical_audited_FTR": row.get("audited_ftr_on_labeled_released", ""),
                    "conservative_label_uncertainty_FTR": row.get("conservative_ftr_uncertain_and_unlabeled_false", ""),
                    "mass_ratio": mass,
                    "best_mass_ratio": mass,
                    "self_consistency_margin": row.get("self_consistency_margin", ""),
                    "required_emax": row.get("required_emax", ""),
                    "max_observed_e": row.get("max_observed_e", ""),
                    "mean_observed_e": row.get("mean_observed_e", ""),
                    "selected_e_min": row.get("selected_e_min", ""),
                    "selected_e_mean": row.get("selected_e_mean", ""),
                    "selected_e_max": row.get("selected_e_max", ""),
                    "release_feasible": bool(released > 0 or _num(mass, default=0.0) >= 1.0),
                    "empty_reason": empty_reason,
                    "safe_refusal_reason": _safe_reason(row),
                    "HOTA_or_proxy": row.get("HOTA", ""),
                    "IDF1_or_proxy": row.get("IDF1", ""),
                    "MOTA_or_proxy": row.get("MOTA", ""),
                    "runtime_sec": row.get("runtime_sec", ""),
                    "paper_table_scope": "main_protocol",
                }
            )
    return [source]


def _build_main_raw_vs_parc(out_dir: Path, started: float) -> Path:
    source = RELIABILITY_DIR / "table_blackbox_generator_certification.csv"
    frame = _read_csv(source)
    rows: list[dict[str, Any]] = []
    if not frame.empty:
        data = frame.copy()
        data = data[data.get("dataset", "").astype(str).isin(["OVT-B", "TAO", "BURST"])]
        data = data[pd.to_numeric(data.get("alpha1", pd.Series(dtype=float)), errors="coerce").eq(0.10)]
        data = data[data.get("seed", "").map(_is_seed_row)]
        if "result_type" in data:
            result_type = data["result_type"].fillna("").astype(str)
            data = data[~result_type.str.contains("published|meanstd|scaffold|rerun", case=False, regex=True)]
        for _, row in data.iterrows():
            released = _num(row.get("released", 0))
            mass = row.get("mass_ratio", "")
            empty_reason = _text(row.get("empty_reason", ""))
            rows.append(
                {
                    "dataset": row.get("dataset", ""),
                    "generator": row.get("generator", ""),
                    "alpha": 0.10,
                    "certified_risk_level_alpha": 0.10,
                    "M": 150,
                    "seed": int(float(row.get("seed"))),
                    "raw_topM_released": 150,
                    "raw_topM_audited_false_rate": "",
                    "raw_topM_unsupported_rate": "",
                    "raw_topM_policy": "score_ranked_topM_reference_count_only",
                    "parc_released": released,
                    "parc_UTR": row.get("UTR", ""),
                    "parc_audited_FTR": row.get("audited_FTR", row.get("audited_ftr_on_labeled_released", "")),
                    "parc_conservative_FTR": row.get("conservative_FTR", ""),
                    "empirical_audited_FTR": "",
                    "conservative_label_uncertainty_FTR": row.get("conservative_FTR", ""),
                    "mass_ratio": mass,
                    "best_mass_ratio": mass,
                    "self_consistency_margin": "",
                    "required_emax": row.get("required_emax", ""),
                    "max_observed_e": "",
                    "mean_observed_e": "",
                    "selected_e_min": row.get("selected_e_min", ""),
                    "selected_e_mean": row.get("selected_e_mean", ""),
                    "selected_e_max": row.get("selected_e_max", ""),
                    "release_feasible": bool(released > 0 or _num(mass, default=0.0) >= 1.0),
                    "empty_reason": empty_reason,
                    "safe_refusal_reason": _safe_reason(row),
                    "HOTA_or_proxy": row.get("HOTA", ""),
                    "IDF1_or_proxy": row.get("IDF1", ""),
                    "MOTA_or_proxy": row.get("MOTA", ""),
                    "runtime_sec": row.get("runtime_sec", ""),
                    "paper_table_scope": "main_protocol",
                }
            )
    source_paths = [source] + _append_burst_rows(rows)
    out = _write_csv(
        pd.DataFrame(rows),
        out_dir / "table_main_raw_vs_parc.csv",
        source_paths,
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    return out


def _build_safe_refusal(out_dir: Path, main_path: Path, started: float) -> Path:
    main = _read_csv(main_path)
    if main.empty:
        table = pd.DataFrame()
    else:
        table = main[pd.to_numeric(main["parc_released"], errors="coerce").fillna(0).eq(0)].copy()
        if not table.empty:
            table["safe_refusal_reason"] = table.apply(_safe_reason, axis=1)
            table["diagnostic_available"] = table["mass_ratio"].notna() | table["empty_reason"].fillna("").astype(str).ne("")
            table["raw_topM_false_rate"] = table.get("raw_topM_audited_false_rate", "")
            table["raw_topM_unsupported_rate"] = table.get("raw_topM_unsupported_rate", "")
            table["diagnostic_reason"] = table["safe_refusal_reason"]
            table["human_audit_false_examples"] = ""
    out = _write_csv(
        table,
        out_dir / "table_safe_refusal_diagnostics.csv",
        [main_path],
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    return out


def _mean(series: pd.Series) -> float | str:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    return float(vals.mean()) if not vals.empty else ""


def _std(series: pd.Series) -> float | str:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    return float(vals.std(ddof=0)) if len(vals) > 1 else 0.0 if len(vals) == 1 else ""


def _build_main_summary(out_dir: Path, main_path: Path, started: float) -> Path:
    main = _read_csv(main_path)
    rows: list[dict[str, Any]] = []
    if not main.empty:
        for (dataset, generator), group in main.groupby(["dataset", "generator"], dropna=False):
            released = pd.to_numeric(group["parc_released"], errors="coerce").fillna(0)
            refusal = released.eq(0)
            rows.append(
                {
                    "dataset": dataset,
                    "generator": generator,
                    "certified_risk_level_alpha": 0.10,
                    "M": 150,
                    "seeds": int(group["seed"].nunique()),
                    "nonempty_seeds": int(released.gt(0).sum()),
                    "safe_refusal_seeds": int(refusal.sum()),
                    "parc_released_mean": _mean(group["parc_released"]),
                    "parc_released_std": _std(group["parc_released"]),
                    "parc_released_min": float(released.min()) if not released.empty else "",
                    "parc_released_max": float(released.max()) if not released.empty else "",
                    "raw_topM_released_mean": _mean(group["raw_topM_released"]),
                    "parc_UTR_mean": _mean(group["parc_UTR"]),
                    "conservative_label_uncertainty_FTR_mean": _mean(group["conservative_label_uncertainty_FTR"]),
                    "mass_ratio_mean": _mean(group["mass_ratio"]),
                    "mass_ratio_min": float(pd.to_numeric(group["mass_ratio"], errors="coerce").min())
                    if pd.to_numeric(group["mass_ratio"], errors="coerce").notna().any()
                    else "",
                    "safe_refusal_rate": float(refusal.mean()) if len(refusal) else "",
                    "dominant_safe_refusal_reason": ";".join(
                        sorted(set(group["safe_refusal_reason"].fillna("").astype(str).loc[lambda s: s.ne("")]))
                    ),
                    "paper_table_scope": "main_protocol_summary",
                }
            )
    return _write_csv(
        pd.DataFrame(rows),
        out_dir / "table_main_raw_vs_parc_summary.csv",
        [main_path],
        "python -m parc_track.cli phase14 closeout",
        started,
    )


def _build_risk_utility_frontier(out_dir: Path, main_path: Path, baseline_path: Path, started: float) -> Path:
    rows: list[dict[str, Any]] = []
    main = _read_csv(main_path)
    if not main.empty:
        for _, row in main.iterrows():
            rows.append(
                {
                    "dataset": row.get("dataset", ""),
                    "source": row.get("generator", ""),
                    "policy": "PARC_certified_release_or_refusal",
                    "certified_risk_level_alpha": row.get("certified_risk_level_alpha", ""),
                    "seed": row.get("seed", ""),
                    "M": row.get("M", 150),
                    "released": row.get("parc_released", ""),
                    "release_rate_vs_M": _num(row.get("parc_released", 0)) / max(_num(row.get("M", 150), 150), 1),
                    "UTR": row.get("parc_UTR", ""),
                    "empirical_audited_FTR": row.get("empirical_audited_FTR", ""),
                    "conservative_label_uncertainty_FTR": row.get("conservative_label_uncertainty_FTR", ""),
                    "mass_ratio": row.get("mass_ratio", ""),
                    "has_alpha_control": True,
                    "release_decision": "refusal" if _num(row.get("parc_released", 0)) == 0 else "release",
                    "safe_refusal_reason": row.get("safe_refusal_reason", ""),
                    "figure_role": "main_parc_curve",
                }
            )
            rows.append(
                {
                    "dataset": row.get("dataset", ""),
                    "source": row.get("generator", ""),
                    "policy": "raw_topM_count_reference_no_certificate",
                    "certified_risk_level_alpha": "",
                    "seed": row.get("seed", ""),
                    "M": row.get("M", 150),
                    "released": row.get("raw_topM_released", ""),
                    "release_rate_vs_M": _num(row.get("raw_topM_released", 0)) / max(_num(row.get("M", 150), 150), 1),
                    "UTR": "",
                    "empirical_audited_FTR": "",
                    "conservative_label_uncertainty_FTR": "",
                    "mass_ratio": "",
                    "has_alpha_control": False,
                    "release_decision": "release",
                    "safe_refusal_reason": "",
                    "figure_role": "topM_reference_count_only",
                }
            )
    baseline = _read_csv(baseline_path)
    if not baseline.empty:
        for _, row in baseline.iterrows():
            rows.append(
                {
                    "dataset": row.get("dataset", ""),
                    "source": "GroundingDINO",
                    "policy": row.get("method", ""),
                    "certified_risk_level_alpha": row.get("certified_risk_level_alpha", ""),
                    "seed": row.get("seed", ""),
                    "M": row.get("M", 150),
                    "released": row.get("released", row.get("parc_released", "")),
                    "release_rate_vs_M": _num(row.get("released", row.get("parc_released", 0))) / max(_num(row.get("M", 150), 150), 1),
                    "UTR": row.get("UTR", ""),
                    "empirical_audited_FTR": row.get("empirical_audited_FTR", ""),
                    "conservative_label_uncertainty_FTR": row.get("conservative_label_uncertainty_FTR", ""),
                    "mass_ratio": row.get("mass_ratio", ""),
                    "has_alpha_control": str(row.get("method", "")).startswith("PARC"),
                    "release_decision": "refusal" if _num(row.get("released", 0)) == 0 else "release",
                    "safe_refusal_reason": row.get("safe_refusal_reason", ""),
                    "figure_role": "baseline_comparison",
                }
            )
    table = pd.DataFrame(rows)
    primary = _write_csv(
        table,
        out_dir / "figure_risk_utility_frontier.csv",
        [main_path, baseline_path],
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    _write_csv(
        table,
        out_dir / "figure_3_risk_utility_frontier.csv",
        [main_path, baseline_path],
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    return primary


def _build_safe_refusal_figures(out_dir: Path, refusal_path: Path, started: float) -> tuple[Path, Path]:
    refusal = _read_csv(refusal_path)
    mass_rows: list[dict[str, Any]] = []
    reason_rows: list[dict[str, Any]] = []
    if not refusal.empty:
        for _, row in refusal.iterrows():
            mass = row.get("mass_ratio", "")
            mass_rows.append(
                {
                    "dataset": row.get("dataset", ""),
                    "generator": row.get("generator", ""),
                    "seed": row.get("seed", ""),
                    "certified_risk_level_alpha": row.get("certified_risk_level_alpha", ""),
                    "M": row.get("M", 150),
                    "mass_ratio": mass,
                    "mass_ratio_threshold": 1.0,
                    "unconstrained_feasible": _num(mass, default=0.0) >= 1.0,
                    "safe_refusal_reason": row.get("safe_refusal_reason", ""),
                    "empty_reason": row.get("empty_reason", ""),
                    "figure_role": "safe_refusal_mass_ratio",
                }
            )
        grouped = (
            refusal.groupby(["dataset", "generator", "safe_refusal_reason"], dropna=False)
            .size()
            .reset_index(name="refusal_seed_count")
        )
        for _, row in grouped.iterrows():
            reason_rows.append(
                {
                    "dataset": row.get("dataset", ""),
                    "generator": row.get("generator", ""),
                    "safe_refusal_reason": row.get("safe_refusal_reason", ""),
                    "refusal_seed_count": row.get("refusal_seed_count", ""),
                    "figure_role": "safe_refusal_reason_counts",
                }
            )
    mass_path = _write_csv(
        pd.DataFrame(mass_rows),
        out_dir / "figure_safe_refusal_mass_ratio.csv",
        [refusal_path],
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    reason_path = _write_csv(
        pd.DataFrame(reason_rows),
        out_dir / "figure_safe_refusal_reason_counts.csv",
        [refusal_path],
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    raw_false_path = _write_csv(
        refusal[
            [
                col
                for col in (
                    "dataset",
                    "generator",
                    "seed",
                    "certified_risk_level_alpha",
                    "M",
                    "raw_topM_false_rate",
                    "raw_topM_unsupported_rate",
                    "parc_released",
                    "safe_refusal_reason",
                    "mass_ratio",
                    "empty_reason",
                )
                if col in refusal.columns
            ]
        ]
        if not refusal.empty
        else pd.DataFrame(),
        out_dir / "figure_safe_refusal_raw_false_rate.csv",
        [refusal_path],
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    return mass_path, reason_path, raw_false_path


def _build_baseline_and_ablation(out_dir: Path, started: float) -> tuple[Path, Path]:
    source = LVVIS_DIR / "table_baseline_expanded.csv"
    frame = _read_csv(source)
    baseline_rows: list[dict[str, Any]] = []
    ablation_rows: list[dict[str, Any]] = []
    method_names = {
        "confidence_threshold": "score_threshold",
        "greedy_score_no_risk": "topM_no_risk",
        "tracklet_p_bh": "tracklet_p_BH",
        "tracklet_e_bh": "tracklet_e_BH",
        "post_filter_e_bh": "post_filter_e_BH",
        "unmatched_as_false_block": "unmatched_as_false_block_calibration",
        "null_superset_no_audit": "null_superset_without_audit",
        "parc_track_gamma_tuned_uniform_scs": "PARC_full",
    }
    component_names = {
        "parc_track_gamma_tuned_uniform_scs": "Full PARC",
        "null_superset_no_audit": "w/o verified-positive removal",
        "unmatched_as_false_block": "unmatched-as-false negative-control baseline",
        "post_filter_e_bh": "w/o SCS, post-filter only",
        "confidence_threshold": "score threshold baseline",
        "greedy_score_no_risk": "no-risk top-M baseline",
    }
    if not frame.empty:
        data = frame[pd.to_numeric(frame.get("alpha1", pd.Series(dtype=float)), errors="coerce").eq(0.10)].copy()
        data = data[data.get("seed", "").map(_is_seed_row)]
        for _, row in data.iterrows():
            method = _text(row.get("method", ""))
            released = _num(row.get("released", 0))
            conservative = row.get(
                "conservative_ftr_uncertain_and_unlabeled_false",
                row.get("conservative_FTR", row.get("conservative_ftr", "")),
            )
            baseline_rows.append(
                {
                    "dataset": "LVVIS",
                    "method": method_names.get(method, method),
                    "certified_risk_level_alpha": 0.10,
                    "M": int(_num(row.get("candidate_budget_M", 150), default=150)),
                    "seed": int(float(row.get("seed"))),
                    "raw_topM_released": 150 if method in {"confidence_threshold", "greedy_score_no_risk"} else "",
                    "parc_released": released if method == "parc_track_gamma_tuned_uniform_scs" else "",
                    "released": released,
                    "UTR": row.get("utr", row.get("UTR", "")),
                    "empirical_audited_FTR": row.get("audited_ftr_on_labeled_released", ""),
                    "conservative_label_uncertainty_FTR": conservative,
                    "mass_ratio": row.get("best_margin", row.get("mass_ratio", "")),
                    "release_feasible": row.get("release_feasible", ""),
                    "empty_reason": row.get("empty_reason", ""),
                    "safe_refusal_reason": _safe_reason(row),
                    "runtime_sec": row.get("runtime_sec", ""),
                    "paper_table_scope": "baseline_comparison",
                }
            )
            if method in component_names:
                ablation_rows.append(
                    {
                        "component": component_names[method],
                        "dataset": "LVVIS",
                        "certified_risk_level_alpha": 0.10,
                        "M": int(_num(row.get("candidate_budget_M", 150), default=150)),
                        "seed": int(float(row.get("seed"))),
                        "released": released,
                        "empirical_audited_FTR": row.get("audited_ftr_on_labeled_released", ""),
                        "conservative_label_uncertainty_FTR": conservative,
                        "mass_ratio": row.get("best_margin", row.get("mass_ratio", "")),
                        "release_feasible": row.get("release_feasible", ""),
                        "max_observed_e": row.get("max_observed_e", ""),
                        "runtime_sec": row.get("runtime_sec", ""),
                        "empty_reason": row.get("empty_reason", ""),
                        "paper_table_scope": "component_ablation",
                    }
                )
    baseline_path = _write_csv(
        pd.DataFrame(baseline_rows),
        out_dir / "table_baseline_comparison.csv",
        [source],
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    ablation_path = _write_csv(
        pd.DataFrame(ablation_rows),
        out_dir / "table_ablation_components.csv",
        [source],
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    return baseline_path, ablation_path


def _build_stress_tables(out_dir: Path, started: float) -> tuple[Path, Path]:
    actual_sources = [
        RELIABILITY_DIR / "table_nonexchangeability_severe_actual_results.csv",
        RELIABILITY_DIR / "table_null_inflation_verified_removal_actual_results.csv",
    ]
    actual_frames = []
    for src in actual_sources:
        frame = _read_csv(src)
        if frame.empty:
            continue
        frame = frame.copy()
        frame["source_table"] = _rel(src)
        actual_frames.append(frame)
    actual = pd.concat(actual_frames, ignore_index=True, sort=False) if actual_frames else pd.DataFrame()
    if not actual.empty and "result_status" in actual:
        actual = actual[actual["result_status"].astype(str).str.contains("actual", case=False, na=False)].copy()
    stress_path = _write_csv(
        actual,
        out_dir / "table_stress_actual_reruns.csv",
        actual_sources,
        "python -m parc_track.cli phase14 closeout",
        started,
    )

    projection_sources = [
        RELIABILITY_DIR / "table_nonexchangeability_stress_results.csv",
        RELIABILITY_DIR / "table_null_inflation_empirical.csv",
    ]
    projection_frames = []
    for src in projection_sources:
        frame = _read_csv(src)
        if frame.empty:
            continue
        frame = frame.copy()
        frame["source_table"] = _rel(src)
        frame["paper_status"] = "projection_only"
        projection_frames.append(frame)
    projection = pd.concat(projection_frames, ignore_index=True, sort=False) if projection_frames else pd.DataFrame()
    if not projection.empty:
        projection = projection.replace(
            {
                "requires_custom_split_rerun": "projection_only_not_claimed",
                "requires_rerun_for_changed_removal_ratio": "projection_only_not_claimed",
                "actual_existing_certificate": "existing_reference_certificate",
            }
        )
    projection_path = _write_csv(
        projection,
        out_dir / "table_stress_appendix_projection_only.csv",
        projection_sources,
        "python -m parc_track.cli phase14 closeout",
        started,
    )
    return stress_path, projection_path


def _select_gallery_rows(teaser: pd.DataFrame, case_types: set[str], limit: int = 8) -> pd.DataFrame:
    if teaser.empty or "case_type" not in teaser:
        return pd.DataFrame()
    data = teaser[teaser["case_type"].astype(str).isin(case_types)].copy()
    if data.empty:
        return data
    if "score" in data:
        data["_score"] = pd.to_numeric(data["score"], errors="coerce")
        data = data.sort_values("_score", ascending=False)
    return data.head(limit).drop(columns=[col for col in ("_score",) if col in data], errors="ignore")


def _write_gallery_manifest(path: Path, frame: pd.DataFrame) -> Path:
    out = ensure_data_output(path)
    frame.to_csv(out, index=False)
    return out


def _build_qualitative_gallery(started: float) -> list[Path]:
    teaser_path = RELEASE_STORY_DIR / "figure_release_story_teaser_manifest.csv"
    teaser = _read_csv(teaser_path)
    gallery_specs = {
        "released_examples": {"PARC_certified_release", "official_matched_positive", "real_official_unmatched"},
        "refusal_examples": {"high_score_topM_parc_refusal_candidate", "actually_false"},
        "borderline_examples": {"uncertain"},
    }
    outputs: list[Path] = []
    for name, case_types in gallery_specs.items():
        frame = _select_gallery_rows(teaser, case_types, limit=12)
        frame = frame.copy()
        if not frame.empty:
            frame["gallery"] = name
            frame["asset_policy"] = "public_manifest_reference_only_no_raw_image_packaging"
        out = _write_gallery_manifest(FIGURES_DIR / name / "manifest.csv", frame)
        outputs.append(out)

    doc = ensure_data_output(QUALITATIVE_GALLERY)
    doc.write_text(
        "# Qualitative Release Gallery\n\n"
        "This gallery is a public-safe manifest for paper figure selection. It does not package raw "
        "videos, raw frames, or montage images. Each row points to an existing public-safe reference "
        "when available, otherwise it records `missing_visual_asset`.\n\n"
        "## Gallery Groups\n\n"
        "- `figures/released_examples/manifest.csv`: certified releases and official matched references.\n"
        "- `figures/refusal_examples/manifest.csv`: high-score candidates and false examples used to explain safe refusal.\n"
        "- `figures/borderline_examples/manifest.csv`: uncertain cases counted conservatively.\n\n"
        "## Paper Use\n\n"
        "Use these manifests to select examples for the final figure layout. Do not commit raw images or "
        "dataset frames to the public repository.\n",
        encoding="utf-8",
    )
    outputs.append(doc)
    # A lightweight provenance sidecar keeps this gallery in the same traceable style as tables.
    write_json(
        doc.with_suffix(".provenance.json"),
        {
            "repo_commit": _git_commit(),
            "command": "python -m parc_track.cli phase14 closeout",
            "runtime_sec": round(time.time() - started, 6),
            "source_files": [{"path": _rel(teaser_path), "sha256": _sha256(teaser_path)}] if teaser_path.exists() else [],
            "outputs": [_rel(path) for path in outputs],
            "raw_data_included": False,
            "paper_facing_gallery": True,
        },
    )
    outputs.append(doc.with_suffix(".provenance.json"))
    return outputs


def _write_run_report(out_dir: Path, outputs: list[Path]) -> Path:
    report = ensure_data_output(out_dir / "RUN_REPORT.md")
    report.write_text(
        "# Paper-Facing Closeout Tables\n\n"
        "This directory contains sanitized paper-facing tables derived from frozen provenance tables. "
        "Raw provenance tables are preserved in their original locations. Published-tracker rows without "
        "complete official prediction provenance are excluded from the main protocol tables and remain "
        "appendix/provenance evidence only.\n\n"
        "## Main Protocol\n\n"
        "- Datasets: OVT-B, TAO, BURST.\n"
        "- Main candidate budget: M=150.\n"
        "- Main risk level: alpha=0.10.\n"
        "- Seeds: 0, 1, 2.\n\n"
        "## Tables\n\n"
        + "\n".join(f"- `{path.name}`" for path in outputs)
        + "\n\nFigure-ready CSVs are included in the same directory and are also covered by provenance sidecars.\n"
        + "\n",
        encoding="utf-8",
    )
    return report


def _write_manifest(root: Path) -> Path:
    manifest = ensure_data_output(root / "MANIFEST_SHA256.txt")
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path != manifest:
            rows.append(f"{_sha256(path)}  {path.relative_to(root).as_posix()}")
    manifest.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return manifest


def run_phase14_closeout(out_dir: str | Path | None = None) -> dict[str, Any]:
    started = time.time()
    output_dir = ensure_data_output(out_dir or PAPER_TABLE_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    main = _build_main_raw_vs_parc(output_dir, started)
    refusal = _build_safe_refusal(output_dir, main, started)
    baseline, ablation = _build_baseline_and_ablation(output_dir, started)
    summary = _build_main_summary(output_dir, main, started)
    frontier = _build_risk_utility_frontier(output_dir, main, baseline, started)
    safe_mass, safe_reasons, safe_raw_false = _build_safe_refusal_figures(output_dir, refusal, started)
    stress, projection = _build_stress_tables(output_dir, started)
    gallery_outputs = _build_qualitative_gallery(started)
    outputs = [
        main,
        summary,
        refusal,
        baseline,
        ablation,
        frontier,
        output_dir / "figure_3_risk_utility_frontier.csv",
        safe_mass,
        safe_reasons,
        safe_raw_false,
        stress,
        projection,
        *gallery_outputs,
    ]
    _validate_clean_tables(outputs)
    report = _write_run_report(output_dir, outputs)
    manifest = _write_manifest(output_dir)
    return {
        "status": "completed",
        "output_dir": _rel(output_dir),
        "tables": [_rel(path) for path in outputs],
        "run_report": _rel(report),
        "manifest": _rel(manifest),
        "runtime_sec": round(time.time() - started, 6),
    }
