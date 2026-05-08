from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .types import AssociationEdge, CandidatePath, VideoBlock


@dataclass(frozen=True)
class SyntheticSplit:
    tune: list[VideoBlock]
    cal: list[VideoBlock]
    test: list[VideoBlock]


DEFAULT_CELLS = (
    ("novel_high", "vehicle_like", "low_occ", "day"),
    ("novel_high", "vehicle_like", "high_occ", "night"),
)


def _clamp_prob(value: float) -> float:
    return float(min(max(value, 0.001), 0.999))


def generate_synthetic_split(cfg: dict) -> SyntheticSplit:
    synthetic = cfg.get("synthetic", {})
    split = synthetic.get("split", {"tune": 20, "cal": 2400, "test": 40})
    seed = int(cfg["seed"])
    rng = np.random.default_rng(seed)
    release_grid = tuple(float(x) for x in cfg["release_grid"])
    m = int(cfg["M"])

    tune = [
        _make_video(rng, "tune", idx, m, release_grid, synthetic)
        for idx in range(int(split["tune"]))
    ]
    cal = [
        _make_video(rng, "cal", idx, m, release_grid, synthetic)
        for idx in range(int(split["cal"]))
    ]
    test = [
        _make_video(rng, "test", idx, m, release_grid, synthetic)
        for idx in range(int(split["test"]))
    ]
    return SyntheticSplit(tune=tune, cal=cal, test=test)


def _make_video(
    rng: np.random.Generator,
    split_name: str,
    index: int,
    candidate_budget: int,
    release_grid: tuple[float, ...],
    synthetic: dict,
) -> VideoBlock:
    video_id = f"{split_name}_{index:05d}"
    true_rate = float(synthetic.get("true_rate", 0.96))
    verified_positive_rate = float(
        synthetic.get(
            f"{split_name}_verified_positive_rate",
            synthetic.get("verified_positive_rate", 0.985),
        )
    )
    false_quota_per_cell = int(synthetic.get("false_quota_per_cell", 1))
    conflict_rate = float(synthetic.get("conflict_rate", 0.01))
    bad_safe_edge_rate = float(synthetic.get("bad_safe_edge_rate", 0.01))
    minutes = float(synthetic.get("minutes_per_video", 0.5))
    video_cluster_noise = float(synthetic.get("video_cluster_noise", 0.15))
    false_track_correlation = float(synthetic.get("false_track_correlation", 0.0))
    false_score_shift = float(synthetic.get("false_score_shift", 0.0))
    video_difficulty = rng.normal(0.0, video_cluster_noise)
    false_video_factor = rng.normal(0.0, false_track_correlation)
    paths: list[CandidatePath] = []
    protected_continuations: set[str] = set()

    forced_false = false_quota_per_cell * len(DEFAULT_CELLS)
    for path_idx in range(candidate_budget):
        cell = DEFAULT_CELLS[path_idx % len(DEFAULT_CELLS)]
        is_forced_false = path_idx < forced_false
        is_true = (not is_forced_false) and (rng.random() < true_rate)
        is_positive = bool(is_true and rng.random() < verified_positive_rate)
        path_id = f"{video_id}_p{path_idx:04d}"

        component = f"{video_id}_k{path_idx:04d}" if is_true and rng.random() < 0.85 else None
        if component is not None:
            protected_continuations.add(component)

        node_base = path_idx
        if paths and rng.random() < conflict_rate:
            conflict_with = rng.choice(paths)
            nodes = (conflict_with.nodes[0], f"{video_id}_n{node_base}_1", f"{video_id}_n{node_base}_2")
            conflicts = frozenset({conflict_with.path_id})
        else:
            nodes = (
                f"{video_id}_n{node_base}_0",
                f"{video_id}_n{node_base}_1",
                f"{video_id}_n{node_base}_2",
            )
            conflicts = frozenset()

        edge_good = is_true or rng.random() > 0.55
        r_plus = float(rng.uniform(0.93, 0.995) if edge_good else rng.uniform(0.1, 0.75))
        if is_true and rng.random() < bad_safe_edge_rate:
            r_plus = float(rng.uniform(0.2, 0.7))
        r_minus = float(rng.uniform(0.90, 0.995) if component else rng.uniform(0.35, 0.85))
        edge = AssociationEdge(
            edge_id=f"{path_id}_e0",
            source=nodes[0],
            target=nodes[1],
            r_plus=r_plus,
            r_minus=r_minus,
            bad_link=bool((not is_true) and r_plus >= 0.85),
            continuation_id=component,
        )

        checkpoint_scores = _scores_for_path(
            rng,
            release_grid,
            is_true,
            video_difficulty,
            false_score_shift,
            false_video_factor,
        )
        final_score = checkpoint_scores[max(release_grid)]
        utility = float(final_score + (0.35 if is_true else -0.15) + rng.normal(0.0, 0.05))
        protected_components = frozenset({component}) if component is not None else frozenset()
        paths.append(
            CandidatePath(
                path_id=path_id,
                video_id=video_id,
                nodes=nodes,
                edges=(edge,),
                cell=cell,
                checkpoint_scores=checkpoint_scores,
                utility=utility,
                A=is_positive,
                Y=bool(is_true),
                conflicts=conflicts,
                protected_components=protected_components,
            )
        )

    if bool(synthetic.get("rank_candidates_by_utility", False)):
        paths = sorted(paths, key=lambda path: path.utility, reverse=True)

    sensor_gaps = int(rng.poisson(float(synthetic.get("sensor_gap_rate", 0.2))))
    return VideoBlock(
        video_id=video_id,
        paths=paths,
        minutes=minutes,
        protected_continuations=frozenset(protected_continuations),
        sensor_gaps=sensor_gaps,
        metadata={
            "split": split_name,
            "video_difficulty": video_difficulty,
            "false_track_correlation": false_track_correlation,
            "false_score_shift": false_score_shift,
        },
    )


def _scores_for_path(
    rng: np.random.Generator,
    release_grid: tuple[float, ...],
    is_true: bool,
    video_difficulty: float,
    false_score_shift: float,
    false_video_factor: float,
) -> dict[float, float]:
    false_score_shift = float(min(max(false_score_shift, 0.0), 1.0))
    if is_true:
        base = rng.normal(7.5, 0.28) - 0.05 * video_difficulty
        slope = rng.normal(0.12, 0.03)
    else:
        easy_false_base = 0.25 + video_difficulty + false_video_factor
        hard_false_base = 7.15 + 0.20 * video_difficulty + false_video_factor
        base_mean = (1.0 - false_score_shift) * easy_false_base + false_score_shift * hard_false_base
        base = rng.normal(base_mean, 0.30 + 0.08 * false_score_shift)
        slope = rng.normal(0.03 + 0.08 * false_score_shift, 0.03)
    scores: dict[float, float] = {}
    for checkpoint in release_grid:
        maturity = np.log1p(checkpoint)
        noise = rng.normal(0.0, 0.05 if is_true else 0.12)
        scores[float(checkpoint)] = float(base + slope * maturity + noise)
    return scores
