from __future__ import annotations

from parc_track.calibration import calibrate_null_superset, compute_release_grid_evalues
from parc_track.diagnostics import (
    calibration_diagnostics,
    finite_resolution_diagnostics,
    selection_diagnostics,
)
from parc_track.identity import evaluate_clear_mot_bounds
from parc_track.selector import scs_greedy_select, slot_weights, weighted_scs_greedy_select
from parc_track.synthetic import generate_synthetic_split
from parc_track.sweeps import build_sweep_config
from parc_track.types import ExperimentConfig


def _cfg() -> dict:
    return {
        "seed": 20260507,
        "M": 48,
        "alpha1": 0.2,
        "alpha2": 1.0,
        "gamma": 0.5,
        "release_grid": [0.5, 1, 2],
        "release_weights": [1 / 3, 1 / 3, 1 / 3],
        "min_cal_blocks": 5,
        "selector": {"lambda_plus": 0.85, "lambda_minus": 0.85},
        "synthetic": {
            "split": {"tune": 2, "cal": 200, "test": 20},
            "true_rate": 0.94,
            "verified_positive_rate": 0.98,
            "false_quota_per_cell": 1,
            "conflict_rate": 0.0,
            "bad_safe_edge_rate": 0.0,
            "sensor_gap_rate": 0.0,
            "minutes_per_video": 0.5,
        },
    }


def test_null_superset_contains_all_false_paths() -> None:
    split = generate_synthetic_split(_cfg())
    for video in split.cal:
        for path in video.paths:
            if not path.Y:
                assert not path.A


def test_false_pvalues_are_conservative_enough() -> None:
    cfg_map = _cfg()
    cfg = ExperimentConfig.from_mapping(cfg_map)
    split = generate_synthetic_split(cfg_map)
    table = calibrate_null_superset(split.cal, cfg)
    p_values = []
    for video in split.test:
        compute_release_grid_evalues(video.paths, table)
        for path in video.paths:
            if not path.Y and path.p_any is not None:
                p_values.append(path.p_any)
    assert p_values
    for threshold in (0.05, 0.1, 0.2):
        frac = sum(p <= threshold for p in p_values) / len(p_values)
        assert frac <= threshold + 0.12


def test_false_evalues_have_mean_at_most_one_with_tolerance() -> None:
    cfg_map = _cfg()
    cfg = ExperimentConfig.from_mapping(cfg_map)
    split = generate_synthetic_split(cfg_map)
    table = calibrate_null_superset(split.cal, cfg)
    evalues = []
    for video in split.test:
        compute_release_grid_evalues(video.paths, table)
        for path in video.paths:
            if not path.Y and path.evalue is not None:
                evalues.append(path.evalue)
    assert sum(evalues) / len(evalues) <= 1.15


def test_scs_greedy_self_consistency_and_node_disjointness() -> None:
    cfg_map = _cfg()
    cfg = ExperimentConfig.from_mapping(cfg_map)
    split = generate_synthetic_split(cfg_map)
    table = calibrate_null_superset(split.cal, cfg)
    video = split.test[0]
    compute_release_grid_evalues(video.paths, table)
    result = scs_greedy_select(video.paths, cfg.alpha1, cfg.candidate_budget, cfg.lambda_plus)
    if result.selected:
        threshold = cfg.candidate_budget / (cfg.alpha1 * len(result.selected))
        assert all((path.evalue or 0.0) >= threshold for path in result.selected)
    seen = set()
    for path in result.selected:
        assert not (seen & set(path.nodes))
        seen.update(path.nodes)


def test_protected_components_not_split_across_selected_ids() -> None:
    cfg_map = _cfg()
    cfg = ExperimentConfig.from_mapping(cfg_map)
    split = generate_synthetic_split(cfg_map)
    table = calibrate_null_superset(split.cal, cfg)
    video = split.test[0]
    compute_release_grid_evalues(video.paths, table)
    result = scs_greedy_select(video.paths, cfg.alpha1, cfg.candidate_budget, cfg.lambda_plus)
    owner = {}
    for path in result.selected:
        for component in path.protected_components:
            assert owner.setdefault(component, path.path_id) == path.path_id


def test_finite_resolution_matches_current_smoke_formula() -> None:
    diag = finite_resolution_diagnostics(
        n_cal=2400,
        release_weights=(0.2, 0.2, 0.2, 0.2, 0.2),
        gamma=0.5,
        alpha1=0.10,
        candidate_budget_m=128,
        selected_k=128,
    )
    assert abs(float(diag["p_any_min_theoretical"]) - (5 / 2401)) < 1e-12
    assert abs(float(diag["e_value_max_theoretical"]) - 10.956733089748969) < 1e-9
    assert abs(float(diag["tau_released_k"]) - 10.0) < 1e-12


def test_selection_diagnostics_matches_scs_threshold() -> None:
    cfg_map = _cfg()
    cfg = ExperimentConfig.from_mapping(cfg_map)
    split = generate_synthetic_split(cfg_map)
    table = calibrate_null_superset(split.cal, cfg)
    video = split.test[0]
    compute_release_grid_evalues(video.paths, table)
    result = scs_greedy_select(video.paths, cfg.alpha1, cfg.candidate_budget, cfg.lambda_plus)
    diag = selection_diagnostics(result, video.paths)
    if result.selected:
        assert diag["threshold"] == result.threshold
        assert diag["tau_k"] == result.threshold
        assert float(diag["self_consistency_margin_min"]) >= -1e-12


def test_calibration_diagnostics_counts_removed_and_null_superset() -> None:
    split = generate_synthetic_split(_cfg())
    diag = calibration_diagnostics(split.cal)
    total_non_dummy = sum(1 for video in split.cal for path in video.paths if not path.is_dummy)
    assert int(diag["null_superset_size"]) + int(diag["verified_positive_removed"]) == total_non_dummy
    assert int(diag["false_path_count"]) <= int(diag["null_superset_size"])


def test_sweep_config_overrides_do_not_mutate_base_config() -> None:
    base = _cfg()
    cfg = build_sweep_config(
        base,
        seed=123,
        preset="quick",
        overrides=[(("synthetic", "split", "cal"), 100)],
    )
    assert cfg["seed"] == 123
    assert cfg["synthetic"]["split"]["cal"] == 100
    assert base["seed"] == 20260507
    assert base["synthetic"]["split"]["cal"] == 200


def test_identity_rows_have_decomposed_fields_and_finite_tightness() -> None:
    cfg_map = _cfg()
    cfg = ExperimentConfig.from_mapping(cfg_map)
    split = generate_synthetic_split(cfg_map)
    table = calibrate_null_superset(split.cal, cfg)
    video = split.test[0]
    compute_release_grid_evalues(video.paths, table)
    result = scs_greedy_select(video.paths, cfg.alpha1, cfg.candidate_budget, cfg.lambda_plus)
    bound = evaluate_clear_mot_bounds(video, result, cfg.lambda_plus, cfg.lambda_minus)
    assert bound.certified_ub == bound.badlink_ub + bound.misscont_ub + bound.gap_sensor
    assert bound.actual_idsw >= 0
    assert bound.tightness >= 0


def test_slot_weights_sum_to_one_and_power_weights_prioritize_early_slots() -> None:
    split = generate_synthetic_split(_cfg())
    paths = split.test[0].paths
    weights = slot_weights(paths, universe_size=48, weight_scheme="power", weight_param=1.0)
    assert abs(sum(weights.values()) - 1.0) < 1e-12
    assert weights[paths[0].path_id] > weights[paths[-1].path_id]


def test_weighted_scs_greedy_uses_path_specific_thresholds() -> None:
    cfg_map = _cfg()
    cfg = ExperimentConfig.from_mapping(cfg_map)
    split = generate_synthetic_split(cfg_map)
    table = calibrate_null_superset(split.cal, cfg)
    video = split.test[0]
    compute_release_grid_evalues(video.paths, table)
    result = weighted_scs_greedy_select(
        video.paths,
        cfg.alpha1,
        cfg.candidate_budget,
        cfg.lambda_plus,
        weight_scheme="power",
        weight_param=0.5,
    )
    assert result.weight_scheme == "power"
    for path in result.selected:
        assert (path.evalue or 0.0) >= result.path_thresholds[path.path_id]
