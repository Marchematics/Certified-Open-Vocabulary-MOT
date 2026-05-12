from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .adapters.datasets import ensure_data_output


DATA_ROOT = Path(os.environ.get("PARC_TRACK_ROOT", ".")).resolve()
RELIABILITY_DIR = DATA_ROOT / "outputs/milestones/reliability_fortress"
GENERALITY_DIR = DATA_ROOT / "outputs/milestones/generality_reliability"
PAPER_DIR = RELIABILITY_DIR / "paper_tables"
FIGURE_DIR = RELIABILITY_DIR / "figures_publication"
GENERALITY_TABLE_DIR = GENERALITY_DIR / "paper_tables"

PALETTE = {
    "blue": "#0072B2",
    "orange": "#E69F00",
    "green": "#009E73",
    "red": "#D55E00",
    "purple": "#CC79A7",
    "sky": "#56B4E9",
    "gray": "#4D4D4D",
}


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
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=DATA_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def _rel(path: str | Path) -> str:
    try:
        return Path(path).resolve().relative_to(DATA_ROOT).as_posix()
    except Exception:
        return Path(path).as_posix()


def _num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _write_csv(df: pd.DataFrame, path: Path, sources: list[Path], started: float, notes: str = "") -> Path:
    path = ensure_data_output(path)
    df.to_csv(path, index=False)
    _write_provenance(path, sources, started, notes)
    return path


def _write_provenance(path: Path, sources: list[Path], started: float, notes: str = "") -> None:
    sidecar = ensure_data_output(path.with_suffix(path.suffix + ".provenance.json"))
    existing_sources = [source for source in sources if source.exists()]
    payload = {
        "table": path.name,
        "repo_commit": _git_commit(),
        "command": "python -m parc_track.cli phase16 generality-closeout",
        "runtime_sec": round(time.time() - started, 6),
        "environment": "python",
        "random_seed": "not_applicable",
        "sources": [{"path": _rel(source), "sha256": _sha256(source)} for source in existing_sources],
        "output_sha256": _sha256(path),
        "notes": notes,
    }
    sidecar.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _set_style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 300,
            "font.size": 8,
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "legend.fontsize": 7,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def _save_figure(fig: plt.Figure, path: Path, sources: list[Path], started: float, notes: str = "") -> Path:
    path = ensure_data_output(path)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    _write_provenance(path, sources, started, notes)
    return path


def _build_lvis_tables(started: float) -> list[Path]:
    outputs: list[Path] = []
    cert_path = GENERALITY_DIR / "table_lvis_detection_certification.csv"
    universe_path = GENERALITY_DIR / "candidate_universe.csv"
    cert = _read_csv(cert_path)
    universe = _read_csv(universe_path)
    if cert.empty:
        return outputs

    main_rows: list[dict[str, Any]] = []
    for _, row in cert.iterrows():
        detector = row.get("detector", "")
        alpha = _num(row.get("alpha1"))
        utr = _num(row.get("UTR"))
        released = _num(row.get("released"))
        empty_reason = str(row.get("empty_reason", "") or "")
        if detector == "GroundingDINO" and released > 0 and utr <= alpha:
            placement = "main_generality_positive"
            interpretation = "positive_certified_release"
        elif released == 0:
            placement = "appendix_stress"
            interpretation = "certified_refusal"
        elif utr > alpha:
            placement = "appendix_stress"
            interpretation = "unsafe_under_official_support_proxy_do_not_use_as_main_claim"
        else:
            placement = "appendix_stress"
            interpretation = "secondary_release"
        main_rows.append(
            {
                "dataset": "LVIS",
                "task": "single_frame_open_vocabulary_detection",
                "detector": detector,
                "policy": "PARC certified release",
                "certified_risk_target_alpha": alpha,
                "seed": row.get("seed", ""),
                "M": row.get("M", 150),
                "released": released,
                "official_unsupported_rate": utr,
                "empirical_audited_false_rate": "",
                "conservative_unknown_as_false_rate": _num(row.get("conservative_FTR")),
                "mass_ratio": _num(row.get("mass_ratio")),
                "empty_reason": empty_reason,
                "paper_placement": placement,
                "interpretation": interpretation,
                "audit_status": "LVIS high-score unmatched audit labels pending; conservative rate uses official-unsupported proxy.",
            }
        )
    main = pd.DataFrame(main_rows)
    outputs.append(
        _write_csv(
            main,
            GENERALITY_TABLE_DIR / "table_lvis_detection_main.csv",
            [cert_path],
            started,
            notes="Paper-facing LVIS detection table with explicit risk metric names and placement.",
        )
    )

    raw_rows: list[dict[str, Any]] = []
    if not universe.empty and "detector" in universe.columns:
        for detector, group in universe.groupby("detector"):
            score_col = "score" if "score" in group.columns else "candidate_rank"
            top = group.sort_values(score_col, ascending=False).head(150)
            support = top.get("is_matched_to_gt", pd.Series([False] * len(top))).astype(bool)
            unsupported = 1.0 - float(support.mean()) if len(top) else 0.0
            raw_rows.append(
                {
                    "dataset": "LVIS",
                    "detector": detector,
                    "policy": "raw detector top-M",
                    "certified_risk_target_alpha": "",
                    "seed": "pooled",
                    "M": len(top),
                    "released": len(top),
                    "official_unsupported_rate": unsupported,
                    "empirical_audited_false_rate": "",
                    "conservative_unknown_as_false_rate": unsupported,
                    "mass_ratio": "",
                    "empty_reason": "",
                    "has_alpha_control": False,
                    "paper_placement": "main_comparison" if detector == "GroundingDINO" else "appendix_stress",
                }
            )
    parc_rows = main.rename(
        columns={
            "paper_placement": "paper_placement",
        }
    ).copy()
    parc_rows["has_alpha_control"] = True
    raw_vs_parc = pd.concat([pd.DataFrame(raw_rows), parc_rows], ignore_index=True, sort=False)
    outputs.append(
        _write_csv(
            raw_vs_parc,
            GENERALITY_TABLE_DIR / "table_lvis_raw_detector_vs_parc.csv",
            [cert_path, universe_path],
            started,
            notes="LVIS raw detector top-M vs PARC certified release comparison.",
        )
    )
    stress = main[main["paper_placement"].eq("appendix_stress")].copy()
    outputs.append(
        _write_csv(
            stress,
            GENERALITY_TABLE_DIR / "table_lvis_detection_appendix_stress.csv",
            [cert_path],
            started,
            notes="LVIS rows that are diagnostic/stress evidence rather than main positive claims.",
        )
    )
    return outputs


def _build_mask_scope_table(started: float) -> list[Path]:
    outputs: list[Path] = []
    sources = [
        GENERALITY_DIR / "table_ovvis_mask_certification.csv",
        DATA_ROOT / "outputs/milestones/lvvis_mask_certification/table_lvvis_mask_certification.csv",
        DATA_ROOT / "outputs/milestones/ovis_certification/table_ovis_certification_summary.csv",
    ]
    rows: list[dict[str, Any]] = []
    for source in sources:
        df = _read_csv(source)
        if df.empty:
            continue
        for _, row in df.iterrows():
            dataset = str(row.get("dataset", source.parent.name.upper()))
            task = str(row.get("task", "mask_path_certification"))
            alpha = row.get("alpha1", row.get("certified_risk_target_alpha", ""))
            released = _num(row.get("released"))
            utr = _num(row.get("UTR", row.get("utr", 0.0)))
            rows.append(
                {
                    "dataset": dataset,
                    "task": task,
                    "certified_risk_target_alpha": alpha,
                    "seed": row.get("seed", ""),
                    "M": row.get("M", row.get("candidate_budget_M", 150)),
                    "released": released,
                    "official_unsupported_rate": utr,
                    "conservative_unknown_as_false_rate": _num(row.get("conservative_FTR", row.get("conservative_ftr", 0.0))),
                    "mass_ratio": _num(row.get("mass_ratio", row.get("best_mass_ratio", 0.0))),
                    "empty_reason": row.get("empty_reason", ""),
                    "mask_iou_threshold": row.get("mask_iou_threshold", ""),
                    "paper_scope": row.get("paper_scope", "box_to_mask_or_mask_path_proof_of_principle"),
                    "paper_placement": "appendix_proof_of_principle",
                }
            )
    table = pd.DataFrame(rows)
    outputs.append(
        _write_csv(
            table,
            GENERALITY_TABLE_DIR / "table_mask_path_proof_of_principle.csv",
            sources,
            started,
            notes="Mask-path evidence is proof-of-principle unless full official mask benchmark provenance is available.",
        )
    )
    return outputs


def _plot_lvis_raw_vs_parc(started: float) -> Path | None:
    source = GENERALITY_TABLE_DIR / "table_lvis_raw_detector_vs_parc.csv"
    df = _read_csv(source)
    if df.empty:
        return None
    plot = df[df["detector"].isin(["GroundingDINO", "OWLv2"])].copy()
    plot["policy_label"] = plot["policy"].astype(str) + " " + plot["certified_risk_target_alpha"].astype(str).replace({"": ""})
    fig, ax = plt.subplots(figsize=(3.5, 2.2))
    colors = {"GroundingDINO": PALETTE["blue"], "OWLv2": PALETTE["orange"]}
    for detector, group in plot.groupby("detector"):
        ax.scatter(
            group["released"],
            group["official_unsupported_rate"],
            label=detector,
            s=36,
            color=colors.get(detector, PALETTE["gray"]),
            edgecolor="white",
            linewidth=0.5,
        )
    ax.set_xlabel("Released boxes")
    ax.set_ylabel("Official unsupported rate")
    ax.set_title("LVIS raw detector vs PARC")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False)
    return _save_figure(fig, FIGURE_DIR / "figure_lvis_raw_detector_vs_parc.pdf", [source], started)


def _plot_risk_utility(started: float) -> Path | None:
    source = PAPER_DIR / "table_baseline_comparison.csv"
    df = _read_csv(source)
    if df.empty:
        return None
    risk_col = "conservative_label_uncertainty_FTR" if "conservative_label_uncertainty_FTR" in df.columns else "conservative_FTR"
    if risk_col not in df.columns:
        return None
    main = df[df["baseline"].isin(["Raw top-M", "Post-filter e-value threshold", "Full PARC", "Oracle true upper bound"])].copy()
    fig, ax = plt.subplots(figsize=(4.8, 2.8))
    markers = {"Raw top-M": "o", "Post-filter e-value threshold": "s", "Full PARC": "^", "Oracle true upper bound": "D"}
    colors = {"Raw top-M": PALETTE["gray"], "Post-filter e-value threshold": PALETTE["orange"], "Full PARC": PALETTE["blue"], "Oracle true upper bound": PALETTE["green"]}
    for baseline, group in main.groupby("baseline"):
        ax.scatter(
            group["released"],
            group[risk_col],
            label=baseline,
            marker=markers.get(baseline, "o"),
            color=colors.get(baseline, PALETTE["gray"]),
            s=26,
            alpha=0.85,
            edgecolor="white",
            linewidth=0.4,
        )
    ax.set_xlabel("Released paths")
    ax.set_ylabel("Conservative FTR")
    ax.set_title("Risk-utility frontier")
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, ncol=2)
    return _save_figure(fig, FIGURE_DIR / "figure_3_risk_utility_frontier.pdf", [source], started)


def _plot_safe_refusal(started: float) -> Path | None:
    source = PAPER_DIR / "table_safe_refusal_diagnostics.csv"
    df = _read_csv(source)
    if df.empty:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(6.2, 2.6))
    ax = axes[0]
    ax.scatter(df["best_mass_ratio"], df["max_observed_e"], color=PALETTE["red"], s=24, alpha=0.8)
    ax.axvline(1.0, color=PALETTE["gray"], linewidth=1, linestyle="--")
    ax.set_xlabel("Best mass ratio")
    ax.set_ylabel("Max observed e")
    ax.set_title("Refusal evidence")
    ax = axes[1]
    counts = df["safe_refusal_reason"].fillna("unknown").value_counts().head(6)
    ax.barh(np.arange(len(counts)), counts.values, color=PALETTE["sky"])
    ax.set_yticks(np.arange(len(counts)), counts.index)
    ax.invert_yaxis()
    ax.set_xlabel("Rows")
    ax.set_title("Refusal reasons")
    return _save_figure(fig, FIGURE_DIR / "figure_4_safe_refusal_diagnostics.pdf", [source], started)


def _plot_stress(started: float) -> Path | None:
    null_source = PAPER_DIR / "table_stress_null_inflation.csv"
    audit_source = PAPER_DIR / "table_stress_audit_noise.csv"
    shift_source = PAPER_DIR / "table_stress_nonexchangeability.csv"
    null_df = _read_csv(null_source)
    audit_df = _read_csv(audit_source)
    shift_df = _read_csv(shift_source)
    if null_df.empty and audit_df.empty and shift_df.empty:
        return None
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.4))
    if not null_df.empty:
        g = null_df.groupby("label_keep_rate", as_index=False)["released"].mean()
        axes[0].plot(g["label_keep_rate"], g["released"], color=PALETTE["blue"], marker="o")
        axes[0].set_xlabel("Label keep rate")
        axes[0].set_ylabel("Mean release")
        axes[0].set_title("Annotation sparsity")
    if not audit_df.empty:
        g = audit_df.groupby("noise_rate", as_index=False)["conservative_FTR"].mean()
        axes[1].plot(g["noise_rate"], g["conservative_FTR"], color=PALETTE["orange"], marker="o")
        axes[1].set_xlabel("Audit noise rate")
        axes[1].set_ylabel("Conservative FTR")
        axes[1].set_title("Audit noise")
    if not shift_df.empty:
        g = shift_df.groupby("shift_scenario", as_index=False)["released"].mean().sort_values("released")
        axes[2].barh(np.arange(len(g)), g["released"], color=PALETTE["green"])
        axes[2].set_yticks(np.arange(len(g)), g["shift_scenario"])
        axes[2].set_xlabel("Mean release")
        axes[2].set_title("Shift stress")
    return _save_figure(fig, FIGURE_DIR / "figure_5_stress_tests.pdf", [null_source, audit_source, shift_source], started)


def _plot_stratified(started: float) -> Path | None:
    source = GENERALITY_DIR / "figure_stratified_reliability.csv"
    df = _read_csv(source)
    if df.empty:
        source = GENERALITY_DIR / "table_stratified_reliability.csv"
        df = _read_csv(source)
    if df.empty:
        return None
    dim_col = "dimension" if "dimension" in df.columns else ("stratification_dimension" if "stratification_dimension" in df.columns else "stratum_type")
    level_col = "level" if "level" in df.columns else "stratum"
    official_col = "official_support_rate" if "official_support_rate" in df.columns else "official_matched_rate"
    human_col = "human_valid_rate" if "human_valid_rate" in df.columns else "actually_true_rate"
    subset = df[[dim_col, level_col, official_col, human_col]].dropna().head(24)
    if subset.empty:
        return None
    labels = subset[dim_col].astype(str) + ": " + subset[level_col].astype(str)
    x = np.arange(len(subset))
    width = 0.38
    fig, ax = plt.subplots(figsize=(7.2, 2.8))
    ax.bar(x - width / 2, subset[official_col], width, label="Official support", color=PALETTE["gray"])
    ax.bar(x + width / 2, subset[human_col], width, label="Human-valid", color=PALETTE["blue"])
    ax.set_ylabel("Rate")
    ax.set_title("Stratified reliability under incomplete annotations")
    ax.set_xticks(x, labels, rotation=45, ha="right")
    ax.set_ylim(0, 1.05)
    ax.legend(frameon=False)
    return _save_figure(fig, FIGURE_DIR / "figure_6_stratified_reliability.pdf", [Path(source)], started)


def _write_environment_files() -> list[Path]:
    outputs: list[Path] = []
    env = ensure_data_output(DATA_ROOT / "environment.yml")
    env.write_text(
        "name: parc-track\n"
        "channels:\n"
        "  - conda-forge\n"
        "dependencies:\n"
        "  - python=3.11\n"
        "  - pip\n"
        "  - pip:\n"
        "      - -r requirements.lock.txt\n",
        encoding="utf-8",
    )
    outputs.append(env)
    req = ensure_data_output(DATA_ROOT / "requirements.lock.txt")
    req.write_text(
        "numpy==2.4.4\n"
        "pandas==3.0.2\n"
        "matplotlib==3.10.9\n"
        "PyYAML==6.0.3\n"
        "Pillow==12.2.0\n"
        "pytest==9.0.3\n",
        encoding="utf-8",
    )
    outputs.append(req)
    docker = ensure_data_output(DATA_ROOT / "Dockerfile")
    docker.write_text(
        "FROM python:3.11-slim\n"
        "WORKDIR /workspace\n"
        "COPY requirements.lock.txt ./requirements.lock.txt\n"
        "RUN pip install --no-cache-dir -r requirements.lock.txt\n"
        "COPY . .\n"
        "ENV PYTHONPATH=/workspace/code/parc_track\n"
        "CMD [\"make\", \"tiny-fixture\"]\n",
        encoding="utf-8",
    )
    outputs.append(docker)
    return outputs


def run_phase16_generality_closeout(output_dir: str | Path | None = None) -> dict[str, Any]:
    started = time.time()
    if output_dir is not None:
        global GENERALITY_TABLE_DIR
        GENERALITY_TABLE_DIR = ensure_data_output(Path(output_dir))
    _set_style()
    GENERALITY_TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    outputs.extend(_build_lvis_tables(started))
    outputs.extend(_build_mask_scope_table(started))
    for maybe_path in [
        _plot_lvis_raw_vs_parc(started),
        _plot_risk_utility(started),
        _plot_safe_refusal(started),
        _plot_stress(started),
        _plot_stratified(started),
    ]:
        if maybe_path is not None:
            outputs.append(maybe_path)
    outputs.extend(_write_environment_files())
    report = ensure_data_output(GENERALITY_TABLE_DIR / "GENERALITY_CLOSEOUT_REPORT.md")
    report.write_text(
        "# Generality and Reproducibility Closeout\n\n"
        "LVIS detection rows are split into main positive evidence and appendix stress rows. "
        "OWLv2 rows with high official-unsupported rates are diagnostic stress evidence, not main positive claims. "
        "Mask-path rows are proof-of-principle unless full official mask benchmark provenance is available. "
        "Publication figures use a consistent vector PDF style and colorblind-safe palette.\n",
        encoding="utf-8",
    )
    outputs.append(report)
    return {
        "status": "completed",
        "generality_table_dir": _rel(GENERALITY_TABLE_DIR),
        "figure_dir": _rel(FIGURE_DIR),
        "outputs": [_rel(path) for path in outputs],
        "runtime_sec": round(time.time() - started, 6),
    }
