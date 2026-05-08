from __future__ import annotations

from collections import defaultdict
from math import isfinite
from statistics import mean

from .calibration import e_calibrator
from .selector import SelectionResult
from .types import CandidatePath, VideoBlock


def finite_resolution_diagnostics(
    n_cal: int,
    release_weights: tuple[float, ...],
    gamma: float,
    alpha1: float,
    candidate_budget_m: int,
    selected_k: int,
) -> dict[str, float | int | None]:
    if n_cal < 1:
        raise ValueError("n_cal must be positive")
    if not release_weights:
        raise ValueError("release_weights must be non-empty")
    max_weight = max(release_weights)
    if max_weight <= 0:
        raise ValueError("release_weights must contain a positive weight")

    p_block_min = 1.0 / (n_cal + 1.0)
    p_any_min = min(p_block_min / max_weight, 1.0)
    e_value_max = e_calibrator(p_any_min, gamma)
    tau = (
        candidate_budget_m / (alpha1 * selected_k)
        if selected_k > 0 and alpha1 > 0
        else None
    )
    return {
        "n_calibration_videos": n_cal,
        "release_grid_size": len(release_weights),
        "p_block_min": p_block_min,
        "p_any_min_theoretical": p_any_min,
        "e_value_max_theoretical": e_value_max,
        "tau_released_k": tau,
        "finite_resolution_feasibility_margin": (
            e_value_max - tau if tau is not None else None
        ),
    }


def selection_diagnostics(
    selection: SelectionResult,
    all_paths: list[CandidatePath] | None = None,
) -> dict[str, float | int | None]:
    selected = selection.selected
    selected_k = len(selected)
    tau_k = (
        selection.universe_size / (selection.alpha1 * selected_k)
        if selected_k > 0 and selection.alpha1 > 0
        else None
    )
    e_values = [path.evalue for path in selected if path.evalue is not None]
    thresholds = [
        selection.path_thresholds.get(path.path_id)
        for path in selected
        if selection.path_thresholds.get(path.path_id) is not None
    ]
    if e_values:
        selected_e_min = min(e_values)
        selected_e_mean = mean(e_values)
        selected_e_max = max(e_values)
    else:
        selected_e_min = selected_e_mean = selected_e_max = None

    if thresholds:
        selected_threshold_min = min(thresholds)
        selected_threshold_mean = mean(thresholds)
        selected_threshold_max = max(thresholds)
    else:
        selected_threshold_min = selected_threshold_mean = selected_threshold_max = tau_k

    if thresholds and e_values and len(thresholds) == len(e_values):
        self_consistency_margin = min(
            value - threshold for value, threshold in zip(e_values, thresholds)
        )
    elif tau_k is not None and e_values:
        self_consistency_margin = min(value - tau_k for value in e_values)
    else:
        self_consistency_margin = None

    dummy_paths = sum(1 for path in all_paths or [] if path.is_dummy)
    return {
        "released_k": selected_k,
        "tau_k": selected_threshold_max,
        "threshold": selection.threshold,
        "selected_threshold_min": selected_threshold_min,
        "selected_threshold_mean": selected_threshold_mean,
        "selected_threshold_max": selected_threshold_max,
        "effective_threshold_min": selected_threshold_min,
        "selected_e_min": selected_e_min,
        "selected_e_mean": selected_e_mean,
        "selected_e_max": selected_e_max,
        "self_consistency_margin_min": self_consistency_margin,
        "dummy_paths": dummy_paths,
        "weight_scheme": selection.weight_scheme,
        "weight_param": selection.weight_param,
    }


def calibration_diagnostics(cal_videos: list[VideoBlock]) -> dict[str, object]:
    null_superset_size = 0
    verified_positive_removed = 0
    false_path_count = 0
    dummy_paths = 0
    per_cell: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "null_superset_size": 0,
            "verified_positive_removed": 0,
            "false_path_count": 0,
        }
    )

    for video in cal_videos:
        for path in video.paths:
            if path.is_dummy:
                dummy_paths += 1
                continue
            cell_key = "/".join(path.cell)
            if path.A:
                verified_positive_removed += 1
                per_cell[cell_key]["verified_positive_removed"] += 1
            else:
                null_superset_size += 1
                per_cell[cell_key]["null_superset_size"] += 1
            if not path.Y:
                false_path_count += 1
                per_cell[cell_key]["false_path_count"] += 1

    return {
        "n_calibration_videos": len(cal_videos),
        "null_superset_size": null_superset_size,
        "verified_positive_removed": verified_positive_removed,
        "false_path_count": false_path_count,
        "dummy_paths": dummy_paths,
        "per_cell": dict(sorted(per_cell.items())),
    }


def aggregate_diagnostic_rows(
    rows: list[dict[str, object]],
    cal_diag: dict[str, object],
) -> dict[str, object]:
    if not rows:
        return {
            "released_k": 0,
            "tau_k": None,
            "selected_e_min": None,
            "selected_e_mean": None,
            "selected_e_max": None,
            "self_consistency_margin_min": None,
        }

    released = sum(int(row.get("released_k", 0) or 0) for row in rows)
    selected_weighted = [
        (
            float(row["selected_e_mean"]),
            int(row.get("released_k", 0) or 0),
        )
        for row in rows
        if row.get("selected_e_mean") is not None and int(row.get("released_k", 0) or 0) > 0
    ]
    selected_e_mean = (
        sum(value * count for value, count in selected_weighted)
        / sum(count for _, count in selected_weighted)
        if selected_weighted
        else None
    )
    tau_values = [float(row["tau_k"]) for row in rows if row.get("tau_k") is not None]
    margin_values = [
        float(row["self_consistency_margin_min"])
        for row in rows
        if row.get("self_consistency_margin_min") is not None
        and isfinite(float(row["self_consistency_margin_min"]))
    ]
    e_min_values = [
        float(row["selected_e_min"])
        for row in rows
        if row.get("selected_e_min") is not None
    ]
    e_max_values = [
        float(row["selected_e_max"])
        for row in rows
        if row.get("selected_e_max") is not None
    ]
    out = {
        "n_calibration_videos": rows[0].get("n_calibration_videos"),
        "release_grid_size": rows[0].get("release_grid_size"),
        "candidate_budget_M": rows[0].get("candidate_budget_M"),
        "released_k": released,
        "tau_k": max(tau_values) if tau_values else None,
        "effective_threshold_min": min(
            float(row["effective_threshold_min"])
            for row in rows
            if row.get("effective_threshold_min") is not None
        )
        if any(row.get("effective_threshold_min") is not None for row in rows)
        else None,
        "selected_e_min": min(e_min_values) if e_min_values else None,
        "selected_e_mean": selected_e_mean,
        "selected_e_max": max(e_max_values) if e_max_values else None,
        "self_consistency_margin_min": min(margin_values) if margin_values else None,
        "p_any_min_theoretical": rows[0].get("p_any_min_theoretical"),
        "e_value_max_theoretical": rows[0].get("e_value_max_theoretical"),
        "p_block_min": rows[0].get("p_block_min"),
        "finite_resolution_feasibility_margin": None,
        "dummy_paths": sum(int(row.get("dummy_paths", 0) or 0) for row in rows),
        "null_superset_size": cal_diag["null_superset_size"],
        "verified_positive_removed": cal_diag["verified_positive_removed"],
        "false_path_count": cal_diag["false_path_count"],
        "weight_scheme": rows[0].get("weight_scheme"),
        "weight_param": rows[0].get("weight_param"),
    }
    if out["tau_k"] is not None and out["e_value_max_theoretical"] is not None:
        out["finite_resolution_feasibility_margin"] = (
            float(out["e_value_max_theoretical"]) - float(out["tau_k"])
        )
    return out
