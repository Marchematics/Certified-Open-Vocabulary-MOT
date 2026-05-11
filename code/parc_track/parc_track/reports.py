from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

from .adapters.datasets import inspect_bdd100k_zip
from .smoke import ensure_data_disk_output_dir, load_config

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Required report input missing: {path}")
    return pd.read_csv(path)


def _gamma_star(n_cal: np.ndarray, grid_size: int) -> np.ndarray:
    r = grid_size / (n_cal + 1.0)
    return -1.0 / np.log(r)


def plot_calibration_cliff(calibration_df: pd.DataFrame, figures_dir: Path) -> Path:
    path = figures_dir / "fig_calibration_cliff.pdf"
    fig, ax1 = plt.subplots(figsize=(7.5, 4.6))
    ax1.plot(
        calibration_df["n_cal"],
        calibration_df["e_max"],
        marker="o",
        linewidth=2,
        color="#1f77b4",
        label=r"$E_{\max}$",
    )
    ax1.plot(
        calibration_df["n_cal"],
        calibration_df["large_release_tau"],
        linestyle="--",
        linewidth=1.8,
        color="#d62728",
        label=r"$1/\alpha_1$ large-release threshold",
    )
    nonempty = calibration_df[calibration_df["released"] > 0]
    if not nonempty.empty:
        crossing = int(nonempty.iloc[0]["n_cal"])
        ax1.axvline(crossing, color="#444444", linestyle=":", linewidth=1.5)
        ax1.text(crossing, ax1.get_ylim()[1] * 0.9, f" first release\n n={crossing}", ha="left", va="top")
    ax1.set_xlabel("Calibration videos")
    ax1.set_ylabel("E-value / threshold")
    ax1.grid(True, alpha=0.25)

    ax2 = ax1.twinx()
    ax2.bar(
        calibration_df["n_cal"],
        calibration_df["released"],
        width=85,
        alpha=0.25,
        color="#2ca02c",
        label="released tracks",
    )
    ax2.set_ylabel("Released tracks")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_gamma_heatmap(gamma_df: pd.DataFrame, figures_dir: Path) -> Path:
    path = figures_dir / "fig_gamma_heatmap.pdf"
    pivot = gamma_df.pivot(index="gamma", columns="n_cal", values="recall").sort_index()
    gammas = pivot.index.to_numpy(dtype=float)
    n_vals = pivot.columns.to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    im = ax.imshow(
        pivot.to_numpy(),
        origin="lower",
        aspect="auto",
        cmap="viridis",
        extent=[n_vals.min(), n_vals.max(), gammas.min(), gammas.max()],
        vmin=0.0,
        vmax=max(float(gamma_df["recall"].max()), 1e-6),
    )
    fig.colorbar(im, ax=ax, label="Recall")

    n_line = np.linspace(n_vals.min(), n_vals.max(), 300)
    grid_size = int(gamma_df["grid_size"].iloc[0])
    ax.plot(
        n_line,
        _gamma_star(n_line, grid_size),
        color="white",
        linewidth=2,
        linestyle="--",
        label=r"$\gamma^\star=-1/\log(G/(n+1))$",
    )
    ax.set_xlabel("Calibration videos")
    ax.set_ylabel(r"$\gamma$")
    ax.set_title("Gamma-calibration recall heatmap")
    ax.legend(loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_selector_weighting(selector_df: pd.DataFrame, figures_dir: Path) -> Path:
    path = figures_dir / "fig_selector_weighting.pdf"
    df = selector_df.copy()
    df["scheme"] = df.apply(
        lambda row: row["weight_scheme"]
        if pd.isna(row.get("weight_param"))
        else f"{row['weight_scheme']}({row['weight_param']})",
        axis=1,
    )
    schemes = list(dict.fromkeys(df["scheme"].tolist()))
    n_vals = sorted(df["n_cal"].unique())
    x = np.arange(len(n_vals))
    width = 0.8 / max(len(schemes), 1)

    fig, axes = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
    metrics = [("recall", "Recall"), ("empty_rate", "Empty rate"), ("margin", "Margin")]
    for ax, (metric, label) in zip(axes, metrics):
        for idx, scheme in enumerate(schemes):
            sub = df[df["scheme"] == scheme].set_index("n_cal").reindex(n_vals)
            ax.bar(x + idx * width, sub[metric].fillna(0.0), width=width, label=scheme)
        ax.set_ylabel(label)
        ax.grid(True, axis="y", alpha=0.2)
    axes[-1].set_xticks(x + width * (len(schemes) - 1) / 2)
    axes[-1].set_xticklabels([str(int(v)) for v in n_vals])
    axes[-1].set_xlabel("Calibration videos")
    axes[0].legend(loc="upper left", ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def plot_id_tightness(id_df: pd.DataFrame, figures_dir: Path) -> Path:
    path = figures_dir / "fig_id_tightness.pdf"
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    axes[0].hist(id_df["tightness"].astype(float), bins=20, color="#1f77b4", alpha=0.75)
    axes[0].set_xlabel("Tightness")
    axes[0].set_ylabel("Videos")
    axes[0].set_title("IDSW tightness proxy")
    slack = id_df["certified_ub_per_min"].astype(float) - id_df["actual_idsw_per_min"].astype(float)
    axes[1].hist(slack, bins=20, color="#ff7f0e", alpha=0.75)
    axes[1].set_xlabel("Additive slack per min")
    axes[1].set_ylabel("Videos")
    axes[1].set_title("Certified UB - proxy IDSW")
    for ax in axes:
        ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def build_phase1b_summary(
    calibration_df: pd.DataFrame,
    gamma_df: pd.DataFrame,
    selector_df: pd.DataFrame,
    id_summary_df: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    nonempty_cal = calibration_df[calibration_df["released"] > 0]
    if not nonempty_cal.empty:
        first = nonempty_cal.iloc[0]
        rows.append(
            {
                "section": "calibration_cliff",
                "finding": "first_nonempty_uniform_gamma_0.5",
                "n_cal": int(first["n_cal"]),
                "gamma": float(first["gamma"]),
                "released": float(first["released"]),
                "recall": float(first["recall"]),
                "actual_ftr": float(first["actual_ftr"]),
                "margin": float(first["margin"]),
            }
        )

    best_by_recall = gamma_df.loc[gamma_df["recall"].idxmax()]
    rows.append(
        {
            "section": "gamma_calibration",
            "finding": "best_quick_recall",
            "n_cal": int(best_by_recall["n_cal"]),
            "gamma": float(best_by_recall["gamma"]),
            "released": float(best_by_recall["released"]),
            "recall": float(best_by_recall["recall"]),
            "actual_ftr": float(best_by_recall["actual_ftr"]),
            "margin": float(best_by_recall["margin"]),
        }
    )

    n800 = gamma_df[(gamma_df["n_cal"] == 800) & (gamma_df["gamma"] == 0.20)]
    if not n800.empty:
        row = n800.iloc[0]
        rows.append(
            {
                "section": "gamma_calibration",
                "finding": "theory_predicted_gamma_near_0.20_at_n800",
                "n_cal": 800,
                "gamma": 0.20,
                "gamma_star": float(_gamma_star(np.array([800.0]), int(row["grid_size"]))[0]),
                "released": float(row["released"]),
                "recall": float(row["recall"]),
                "actual_ftr": float(row["actual_ftr"]),
                "margin": float(row["margin"]),
            }
        )

    selector_nonempty = selector_df[selector_df["released"] > 0]
    rows.append(
        {
            "section": "selector_weighting",
            "finding": "weighted_scs_not_promoted_in_current_synthetic",
            "nonempty_rows": int(len(selector_nonempty)),
            "best_recall": float(selector_df["recall"].max()),
            "note": "Top-heavy weights did not beat gamma tuning in current synthetic setup.",
        }
    )

    if not id_summary_df.empty:
        s = id_summary_df.iloc[0]
        rows.append(
            {
                "section": "idsw_tightness",
                "finding": "synthetic_proxy_distribution",
                "tightness_median": float(s["tightness_median"]),
                "tightness_p75": float(s["tightness_p75"]),
                "tightness_mean": float(s["tightness_mean"]),
                "tightness_max": float(s["tightness_max"]),
                "note": "Typical proxy tightness is promising; tail remains loose.",
            }
        )
    return pd.DataFrame(rows)


def build_dataset_adapter_report(cfg: dict, output_dir: Path) -> Path:
    bdd = inspect_bdd100k_zip(cfg.get("bdd100k_zip", ""))
    contract = {
        "dataset_name": "bdd100k_zip",
        "path": bdd.path,
        "adapter_status": "not_mot_tracking_layout"
        if not bdd.usable_for_mot_benchmark
        else "needs_manual_tracking_layout_verification",
        "has_video_frames": False,
        "has_tracking_annotations": bdd.tracking_like_entries > 0,
        "has_track_ids": False,
        "has_category_labels": bdd.json_entries > 0,
        "has_frame_indices": False,
        "num_videos": None,
        "num_tracks": None,
        "num_categories": None,
        "annotation_mode": "single_frame_or_unknown",
        "raw_catalog": bdd.to_dict(),
        "decision": "Do not use this archive as a real MOT benchmark unless a future adapter verifies track IDs and video sequences.",
    }
    path = output_dir / "dataset_adapter_report.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(contract, handle, indent=2, ensure_ascii=False)
    return path


def build_phase1b_report(
    config_path: str | Path,
    output_root: str | Path | None = None,
) -> dict[str, object]:
    cfg = load_config(config_path)
    root = ensure_data_disk_output_dir(output_root or "./outputs")
    sweeps_dir = root / "sweeps"
    smoke_dir = root / "smoke"
    figures_dir = ensure_data_disk_output_dir(root / "figures")
    tables_dir = ensure_data_disk_output_dir(root / "tables")
    datasets_dir = ensure_data_disk_output_dir(root / "datasets")

    calibration_df = _read_csv(sweeps_dir / "calibration_size_sweep.csv")
    gamma_df = _read_csv(sweeps_dir / "gamma_calibration_sweep.csv")
    selector_df = _read_csv(sweeps_dir / "selector_weighting_sweep.csv")
    id_df = _read_csv(smoke_dir / "id_bounds.csv")
    id_summary_df = _read_csv(smoke_dir / "id_tightness_summary.csv")

    figure_paths = [
        plot_calibration_cliff(calibration_df, figures_dir),
        plot_gamma_heatmap(gamma_df, figures_dir),
        plot_selector_weighting(selector_df, figures_dir),
        plot_id_tightness(id_df, figures_dir),
    ]
    summary_df = build_phase1b_summary(
        calibration_df=calibration_df,
        gamma_df=gamma_df,
        selector_df=selector_df,
        id_summary_df=id_summary_df,
    )
    summary_path = tables_dir / "table_phase1b_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    dataset_report = build_dataset_adapter_report(cfg, datasets_dir)
    return {
        "figures": [str(path) for path in figure_paths],
        "summary_table": str(summary_path),
        "dataset_adapter_report": str(dataset_report),
    }
