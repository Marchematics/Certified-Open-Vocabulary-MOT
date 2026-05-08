from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

import pandas as pd
import yaml

from .adapters.baselines import DEFAULT_BASELINES
from .adapters.datasets import inspect_bdd100k_zip
from .calibration import calibrate_null_superset, compute_release_grid_evalues
from .diagnostics import (
    aggregate_diagnostic_rows,
    calibration_diagnostics,
    finite_resolution_diagnostics,
    selection_diagnostics,
)
from .identity import evaluate_clear_mot_bounds
from .metrics import aggregate_rows, evaluate_selection, identity_rows
from .selector import oracle_utility_upper_bound, post_filter_select, weighted_scs_greedy_select
from .synthetic import SyntheticSplit, generate_synthetic_split
from .types import ExperimentConfig, VideoBlock


DATA_DISK_ROOT = Path("/home/waas/paper_experiments")


def load_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def ensure_data_disk_output_dir(path: str | Path) -> Path:
    output_dir = Path(path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if output_dir != DATA_DISK_ROOT and DATA_DISK_ROOT not in output_dir.parents:
        raise ValueError(f"Refusing to write outside data disk workspace: {output_dir}")
    return output_dir


def _row_with_diagnostics(
    video: VideoBlock,
    selection,
    cfg: ExperimentConfig,
    alpha: float,
    n_cal: int,
    cal_diag: dict[str, object],
) -> dict[str, object]:
    row = evaluate_selection(video, selection)
    sel_diag = selection_diagnostics(selection, video.paths)
    finite_diag = finite_resolution_diagnostics(
        n_cal=n_cal,
        release_weights=cfg.release_weights,
        gamma=cfg.gamma,
        alpha1=alpha,
        candidate_budget_m=cfg.candidate_budget,
        selected_k=int(sel_diag["released_k"]),
    )
    row.update(sel_diag)
    row.update(finite_diag)
    row["tau_k"] = sel_diag["tau_k"]
    row["tau_released_k"] = finite_diag["tau_released_k"]
    row["candidate_budget_M"] = cfg.candidate_budget
    row["null_superset_size"] = cal_diag["null_superset_size"]
    row["verified_positive_removed"] = cal_diag["verified_positive_removed"]
    row["false_path_count"] = cal_diag["false_path_count"]
    return row


def _aggregate_with_diagnostics(
    rows: list[dict[str, object]],
    alpha: float,
    cal_diag: dict[str, object],
) -> dict[str, object]:
    out = aggregate_rows(rows, alpha)
    out.update(aggregate_diagnostic_rows(rows, cal_diag))
    return out


def _summarize_id_rows(id_rows: list[dict[str, object]]) -> dict[str, object]:
    minutes = sum(float(row["minutes"]) for row in id_rows)
    actual_idsw = sum(int(row["actual_idsw"]) for row in id_rows)
    certified_ub = sum(int(row["certified_ub"]) for row in id_rows)
    out = {
        "actual_idsw": actual_idsw,
        "actual_idsw_per_min": actual_idsw / minutes if minutes else 0.0,
        "badlink_ub": sum(int(row["badlink_ub"]) for row in id_rows),
        "misscont_ub": sum(int(row["misscont_ub"]) for row in id_rows),
        "gap_sensor": sum(int(row["gap_sensor"]) for row in id_rows),
        "certified_ub": certified_ub,
        "certified_ub_per_min": certified_ub / minutes if minutes else 0.0,
        "minutes": minutes,
        "tightness": certified_ub / max(actual_idsw, 1),
        "actual_idsw_source": (
            id_rows[0]["actual_idsw_source"] if id_rows else "synthetic_proxy"
        ),
    }
    return out


def _id_tightness_distribution(id_rows: list[dict[str, object]]) -> dict[str, object]:
    if not id_rows:
        return {
            "n_videos": 0,
            "tightness_mean": 0.0,
            "tightness_median": 0.0,
            "tightness_p25": 0.0,
            "tightness_p75": 0.0,
            "tightness_max": 0.0,
            "actual_idsw_positive_videos": 0,
        }
    df = pd.DataFrame(id_rows)
    tightness = df["tightness"].astype(float)
    return {
        "n_videos": int(len(df)),
        "tightness_mean": float(tightness.mean()),
        "tightness_median": float(tightness.median()),
        "tightness_p25": float(tightness.quantile(0.25)),
        "tightness_p75": float(tightness.quantile(0.75)),
        "tightness_max": float(tightness.max()),
        "actual_idsw_positive_videos": int((df["actual_idsw"].astype(int) > 0).sum()),
    }


def run_synthetic_experiment(cfg_map: dict) -> dict[str, object]:
    cfg = ExperimentConfig.from_mapping(cfg_map)
    start = perf_counter()
    split = generate_synthetic_split(cfg_map)
    return evaluate_synthetic_split(cfg_map, split, perf_counter() - start)


def evaluate_synthetic_split(
    cfg_map: dict,
    split: SyntheticSplit,
    generation_runtime_sec: float = 0.0,
) -> dict[str, object]:
    cfg = ExperimentConfig.from_mapping(cfg_map)
    start = perf_counter()
    cal_table = calibrate_null_superset(split.cal, cfg)
    cal_diag = calibration_diagnostics(split.cal)

    alpha_grid = [float(x) for x in cfg_map.get("alpha1_grid", [cfg.alpha1])]
    risk_rows: list[dict[str, object]] = []
    selector_rows: list[dict[str, object]] = []
    id_bound_objects = []

    for alpha in alpha_grid:
        scs_rows = []
        post_rows = []
        oracle_rows = []
        selector_cfg = cfg_map.get("selector", {})
        weight_scheme = selector_cfg.get("weight_scheme", "uniform")
        weight_param = selector_cfg.get("weight_param")
        for video in split.test:
            paths = compute_release_grid_evalues(video.paths, cal_table)
            scs = weighted_scs_greedy_select(
                paths=paths,
                alpha1=alpha,
                universe_size=cfg.candidate_budget,
                lambda_plus=cfg.lambda_plus,
                weight_scheme=weight_scheme,
                weight_param=weight_param,
            )
            post = post_filter_select(paths, alpha1=alpha, universe_size=cfg.candidate_budget)
            oracle = oracle_utility_upper_bound(paths, count=max(len(scs.selected), 1))

            scs_rows.append(_row_with_diagnostics(video, scs, cfg, alpha, len(split.cal), cal_diag))
            post_rows.append(_row_with_diagnostics(video, post, cfg, alpha, len(split.cal), cal_diag))
            oracle_rows.append(_row_with_diagnostics(video, oracle, cfg, alpha, len(split.cal), cal_diag))

            if alpha == cfg.alpha1:
                id_bound_objects.append(
                    evaluate_clear_mot_bounds(
                        video=video,
                        selection=scs,
                        lambda_plus=cfg.lambda_plus,
                        lambda_minus=cfg.lambda_minus,
                    )
                )

        scs_agg = _aggregate_with_diagnostics(scs_rows, alpha, cal_diag)
        post_agg = _aggregate_with_diagnostics(post_rows, alpha, cal_diag)
        oracle_agg = _aggregate_with_diagnostics(oracle_rows, alpha, cal_diag)
        scs_agg["method"] = (
            "PARC-Track SCS-Greedy"
            if weight_scheme == "uniform"
            else f"PARC-Track weighted SCS-Greedy ({weight_scheme})"
        )
        post_agg["method"] = "post-filter e-value"
        oracle_agg["method"] = "oracle true utility upper bound"
        risk_rows.append(scs_agg)
        selector_rows.extend([post_agg, scs_agg, oracle_agg])

    id_rows = identity_rows(id_bound_objects)
    id_summary = _summarize_id_rows(id_rows)
    id_tightness_distribution = _id_tightness_distribution(id_rows)
    primary = next(row for row in risk_rows if float(row["target_alpha1"]) == cfg.alpha1)
    return {
        "cfg": cfg,
        "split": split,
        "risk_rows": risk_rows,
        "selector_rows": selector_rows,
        "id_rows": id_rows,
        "id_summary": id_summary,
        "id_tightness_distribution": id_tightness_distribution,
        "primary": primary,
        "calibration_diagnostics": cal_diag,
        "fallback_records": len(cal_table.fallback_records),
        "generation_runtime_sec": generation_runtime_sec,
        "evaluation_runtime_sec": perf_counter() - start,
    }


def run_smoke(config_path: str | Path) -> dict[str, object]:
    cfg_map = load_config(config_path)
    cfg = ExperimentConfig.from_mapping(cfg_map)
    output_dir = ensure_data_disk_output_dir(cfg_map["output_dir"])
    start = perf_counter()
    result = run_synthetic_experiment(cfg_map)

    bdd_catalog = inspect_bdd100k_zip(cfg_map.get("bdd100k_zip", ""))
    baseline_catalog = [baseline.to_dict() for baseline in DEFAULT_BASELINES]

    risk_df = pd.DataFrame(result["risk_rows"])
    selector_df = pd.DataFrame(result["selector_rows"])
    id_df = pd.DataFrame(result["id_rows"])
    id_tightness_df = pd.DataFrame([result["id_tightness_distribution"]])
    risk_df.to_csv(output_dir / "risk_table.csv", index=False)
    selector_df.to_csv(output_dir / "selector_table.csv", index=False)
    id_df.to_csv(output_dir / "id_bounds.csv", index=False)
    id_tightness_df.to_csv(output_dir / "id_tightness_summary.csv", index=False)

    primary = result["primary"]
    theorem_bridge = {
        key: primary.get(key)
        for key in (
            "n_calibration_videos",
            "release_grid_size",
            "candidate_budget_M",
            "released_k",
            "tau_k",
            "effective_threshold_min",
            "selected_e_min",
            "selected_e_mean",
            "selected_e_max",
            "self_consistency_margin_min",
            "p_any_min_theoretical",
            "e_value_max_theoretical",
            "finite_resolution_feasibility_margin",
            "weight_scheme",
            "weight_param",
        )
    }
    summary = {
        "config_path": str(Path(config_path).resolve()),
        "seed": cfg.seed,
        "candidate_budget": cfg.candidate_budget,
        "target_alpha1": cfg.alpha1,
        "target_alpha2": cfg.alpha2,
        "gamma": cfg.gamma,
        "release_grid": list(cfg.release_grid),
        "split": cfg_map["synthetic"]["split"],
        "primary": primary,
        "theorem_bridge_diagnostics": theorem_bridge,
        "calibration_diagnostics": result["calibration_diagnostics"],
        "id_summary": result["id_summary"],
        "id_tightness_distribution": result["id_tightness_distribution"],
        "identity_protocol": {
            "guarantee_metric": "CLEAR-MOT IDSW/min",
            "smoke_actual_idsw": "synthetic proxy, not real CLEAR-MOT evaluator output",
        },
        "fallback_records": result["fallback_records"],
        "bdd100k_catalog": bdd_catalog.to_dict(),
        "baseline_catalog": baseline_catalog,
        "runtime_sec": perf_counter() - start,
        "outputs": {
            "summary_json": str(output_dir / "summary.json"),
            "risk_table_csv": str(output_dir / "risk_table.csv"),
            "selector_table_csv": str(output_dir / "selector_table.csv"),
            "id_bounds_csv": str(output_dir / "id_bounds.csv"),
            "id_tightness_summary_csv": str(output_dir / "id_tightness_summary.csv"),
        },
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)
    return summary
