from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from statistics import mean
from typing import Iterable

import pandas as pd

from .smoke import ensure_data_disk_output_dir, load_config, run_synthetic_experiment


CALIBRATION_SIZES = [100, 200, 400, 800, 1200, 1600, 2400, 4000]
VERIFIED_POSITIVE_RATES = [0.0, 0.25, 0.5, 0.75, 1.0]
FALSE_SCORE_SHIFTS = [0.0, 0.25, 0.5, 0.75, 1.0]
GAMMA_VALUES = [0.15, 0.2, 0.25, 0.35, 0.5, 0.65, 0.8]
GAMMA_CALIBRATION_SIZES = [200, 400, 800, 1200, 1600, 2400]
WEIGHTING_CALIBRATION_SIZES = [400, 800, 1200, 1600, 2400]
WEIGHTING_SCHEMES = [
    ("uniform", None),
    ("power", 0.5),
    ("power", 1.0),
    ("exponential", 16.0),
]


def _set_path(cfg: dict, path: tuple[str, ...], value: object) -> None:
    cursor = cfg
    for key in path[:-1]:
        cursor = cursor.setdefault(key, {})
    cursor[path[-1]] = value


def build_sweep_config(
    base_cfg: dict,
    seed: int,
    preset: str,
    overrides: Iterable[tuple[tuple[str, ...], object]],
) -> dict:
    cfg = deepcopy(base_cfg)
    cfg["seed"] = seed
    cfg["alpha1_grid"] = [float(cfg["alpha1"])]
    synthetic = cfg.setdefault("synthetic", {})
    split = synthetic.setdefault("split", {})
    sweeps = cfg.get("sweeps", {})
    if preset == "quick":
        split["tune"] = int(sweeps.get("quick_tune_videos", 0))
        split["test"] = min(
            int(split.get("test", 40)),
            int(sweeps.get("quick_test_videos", 8)),
        )
    elif preset == "paper":
        split["tune"] = int(split.get("tune", 20))
    else:
        raise ValueError(f"Unknown sweep preset: {preset}")
    for path, value in overrides:
        _set_path(cfg, path, value)
    return cfg


def _seed_values(base_cfg: dict, preset: str) -> list[int]:
    sweeps = base_cfg.get("sweeps", {})
    count = int(sweeps.get("quick_seed_count" if preset == "quick" else "paper_seed_count", 5 if preset == "quick" else 50))
    base_seed = int(base_cfg["seed"])
    return [base_seed + offset for offset in range(count)]


def _mean(rows: list[dict[str, object]], key: str) -> float:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return mean(values) if values else 0.0


def _min_non_null(rows: list[dict[str, object]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return min(values) if values else None


def _mean_non_null(rows: list[dict[str, object]], key: str) -> float | None:
    values = [float(row[key]) for row in rows if row.get(key) is not None]
    return mean(values) if values else None


def _run_replicates(
    base_cfg: dict,
    preset: str,
    overrides: Iterable[tuple[tuple[str, ...], object]],
) -> list[dict[str, object]]:
    rows = []
    for seed in _seed_values(base_cfg, preset):
        cfg = build_sweep_config(base_cfg, seed, preset, overrides)
        result = run_synthetic_experiment(cfg)
        primary = dict(result["primary"])
        primary["seed"] = seed
        primary["id_certified_ub_per_min"] = result["id_summary"]["certified_ub_per_min"]
        primary["id_tightness"] = result["id_summary"]["tightness"]
        rows.append(primary)
    return rows


def _summarize_common(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "seeds": len(rows),
        "released": _mean(rows, "released_tracks"),
        "actual_ftr": _mean(rows, "empirical_actual_ftr"),
        "utr": _mean(rows, "utr"),
        "recall": _mean(rows, "mean_novel_recall"),
        "empty_rate": mean(1.0 if float(row["released_tracks"]) == 0 else 0.0 for row in rows),
        "violation_rate": _mean(rows, "violation_rate"),
        "tau_k": _mean_non_null(rows, "tau_k"),
        "effective_threshold_min": _mean_non_null(rows, "effective_threshold_min"),
        "self_consistency_margin_min": _min_non_null(rows, "self_consistency_margin_min"),
        "margin": _min_non_null(rows, "self_consistency_margin_min"),
        "selected_e_min": _min_non_null(rows, "selected_e_min"),
    }


def run_calibration_size_sweep(base_cfg: dict, preset: str) -> pd.DataFrame:
    out_rows = []
    for n_cal in CALIBRATION_SIZES:
        rows = _run_replicates(
            base_cfg,
            preset,
            [(
                ("synthetic", "split", "cal"),
                n_cal,
            )],
        )
        first = rows[0]
        row = {
            "n_cal": n_cal,
            "gamma": first["gamma"] if "gamma" in first else base_cfg["gamma"],
            "grid_size": first["release_grid_size"],
            "e_max": first["e_value_max_theoretical"],
            "alpha1": base_cfg["alpha1"],
            "large_release_tau": 1.0 / float(base_cfg["alpha1"]),
            "margin_vs_large_release_tau": first["e_value_max_theoretical"] - (1.0 / float(base_cfg["alpha1"])),
        }
        row.update(_summarize_common(rows))
        out_rows.append(row)
    return pd.DataFrame(out_rows)


def run_gamma_calibration_sweep(base_cfg: dict, preset: str) -> pd.DataFrame:
    out_rows = []
    for gamma in GAMMA_VALUES:
        for n_cal in GAMMA_CALIBRATION_SIZES:
            rows = _run_replicates(
                base_cfg,
                preset,
                [
                    (("gamma",), gamma),
                    (("synthetic", "split", "cal"), n_cal),
                ],
            )
            first = rows[0]
            row = {
                "gamma": gamma,
                "n_cal": n_cal,
                "grid_size": first["release_grid_size"],
                "e_max": first["e_value_max_theoretical"],
                "alpha1": base_cfg["alpha1"],
                "large_release_tau": 1.0 / float(base_cfg["alpha1"]),
                "margin_vs_large_release_tau": first["e_value_max_theoretical"] - (1.0 / float(base_cfg["alpha1"])),
            }
            row.update(_summarize_common(rows))
            out_rows.append(row)
    return pd.DataFrame(out_rows)


def run_selector_weighting_sweep(base_cfg: dict, preset: str) -> pd.DataFrame:
    out_rows = []
    for n_cal in WEIGHTING_CALIBRATION_SIZES:
        for scheme, param in WEIGHTING_SCHEMES:
            overrides = [
                (("synthetic", "split", "cal"), n_cal),
                (("synthetic", "rank_candidates_by_utility"), True),
                (("selector", "weight_scheme"), scheme),
            ]
            if param is not None:
                overrides.append((("selector", "weight_param"), param))
            rows = _run_replicates(base_cfg, preset, overrides)
            row = {
                "weight_scheme": scheme,
                "weight_param": param,
                "n_cal": n_cal,
                "gamma": base_cfg["gamma"],
                "effective_threshold_min": _mean_non_null(rows, "effective_threshold_min"),
                "runtime": _mean(rows, "mean_runtime_sec"),
            }
            row.update(_summarize_common(rows))
            out_rows.append(row)
    return pd.DataFrame(out_rows)


def plot_calibration_cliff(df: pd.DataFrame, output_dir: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax1 = plt.subplots(figsize=(8, 4.8))
    ax1.plot(df["n_cal"], df["e_max"], marker="o", label="Emax", color="#1f77b4")
    ax1.plot(
        df["n_cal"],
        df["large_release_tau"],
        linestyle="--",
        label="large-release tau=1/alpha",
        color="#d62728",
    )
    if "tau_k" in df and df["tau_k"].notna().any():
        ax1.scatter(
            df.loc[df["tau_k"].notna(), "n_cal"],
            df.loc[df["tau_k"].notna(), "tau_k"],
            label="observed tau_k",
            color="#9467bd",
            zorder=3,
        )
    ax1.set_xlabel("Calibration videos")
    ax1.set_ylabel("E-value / threshold")
    ax1.grid(True, alpha=0.25)
    ax2 = ax1.twinx()
    ax2.bar(df["n_cal"], df["released"], width=80, alpha=0.25, label="released", color="#2ca02c")
    ax2.set_ylabel("Released tracks")
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc="upper left")
    fig.tight_layout()
    path = output_dir / "calibration_size_cliff.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def run_verified_positive_sweep(base_cfg: dict, preset: str) -> pd.DataFrame:
    out_rows = []
    for rate in VERIFIED_POSITIVE_RATES:
        rows = _run_replicates(
            base_cfg,
            preset,
            [(("synthetic", "cal_verified_positive_rate"), rate)],
        )
        row = {
            "verified_positive_rate": rate,
            "null_superset_size": _mean(rows, "null_superset_size"),
            "removed_verified_positive": _mean(rows, "verified_positive_removed"),
        }
        row.update(_summarize_common(rows))
        out_rows.append(row)
    return pd.DataFrame(out_rows)


def run_score_overlap_sweep(base_cfg: dict, preset: str) -> pd.DataFrame:
    out_rows = []
    for shift in FALSE_SCORE_SHIFTS:
        rows = _run_replicates(
            base_cfg,
            preset,
            [(("synthetic", "false_score_shift"), shift)],
        )
        row = {
            "score_overlap": f"false_shift_{shift:.2f}",
            "false_score_shift": shift,
            "delay": min(float(x) for x in base_cfg["release_grid"]),
        }
        row.update(_summarize_common(rows))
        out_rows.append(row)
    return pd.DataFrame(out_rows)


def run_sweep(
    sweep_name: str,
    config_path: str | Path,
    preset: str = "quick",
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    base_cfg = load_config(config_path)
    out_dir = ensure_data_disk_output_dir(
        output_dir or "/home/waas/paper_experiments/outputs/sweeps"
    )
    if sweep_name == "calibration-size":
        df = run_calibration_size_sweep(base_cfg, preset)
        filename = "calibration_size_sweep.csv"
        plot_path = None
    elif sweep_name == "verified-positive":
        df = run_verified_positive_sweep(base_cfg, preset)
        filename = "verified_positive_rate_sweep.csv"
        plot_path = None
    elif sweep_name == "score-overlap":
        df = run_score_overlap_sweep(base_cfg, preset)
        filename = "score_overlap_sweep.csv"
        plot_path = None
    elif sweep_name == "gamma-calibration":
        df = run_gamma_calibration_sweep(base_cfg, preset)
        filename = "gamma_calibration_sweep.csv"
        plot_path = None
    elif sweep_name == "selector-weighting":
        df = run_selector_weighting_sweep(base_cfg, preset)
        filename = "selector_weighting_sweep.csv"
        plot_path = None
    else:
        raise ValueError(f"Unknown sweep: {sweep_name}")

    path = out_dir / filename
    df.to_csv(path, index=False)
    if sweep_name == "calibration-size":
        plot_path = plot_calibration_cliff(df, out_dir)
    return {
        "sweep": sweep_name,
        "preset": preset,
        "rows": len(df),
        "output_csv": str(path),
        "plot_png": str(plot_path) if plot_path is not None else None,
        "columns": list(df.columns),
    }
