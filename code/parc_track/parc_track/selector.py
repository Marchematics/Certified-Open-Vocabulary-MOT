from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, inf
from time import perf_counter

from .types import CandidatePath


@dataclass
class SelectionResult:
    selected: list[CandidatePath]
    alpha1: float
    universe_size: int
    threshold: float | None
    runtime_sec: float
    reason: str
    path_thresholds: dict[str, float] = field(default_factory=dict)
    slot_weights: dict[str, float] = field(default_factory=dict)
    weight_scheme: str = "uniform"
    weight_param: float | None = None

    @property
    def selected_ids(self) -> set[str]:
        return {path.path_id for path in self.selected}


def _compatible(
    path: CandidatePath,
    selected: list[CandidatePath],
    used_nodes: set[str],
    component_owner: dict[str, str],
    lambda_plus: float,
) -> bool:
    if not path.has_only_safe_edges(lambda_plus):
        return False
    if any(node in used_nodes for node in path.nodes):
        return False
    for other in selected:
        if path.path_id in other.conflicts or other.path_id in path.conflicts:
            return False
    for component in path.protected_components:
        owner = component_owner.get(component)
        if owner is not None and owner != path.path_id:
            return False
    return True


def _add_path(
    path: CandidatePath,
    selected: list[CandidatePath],
    used_nodes: set[str],
    component_owner: dict[str, str],
) -> None:
    selected.append(path)
    used_nodes.update(path.nodes)
    for component in path.protected_components:
        component_owner[component] = path.path_id


def scs_greedy_select(
    paths: list[CandidatePath],
    alpha1: float,
    universe_size: int,
    lambda_plus: float,
) -> SelectionResult:
    return weighted_scs_greedy_select(
        paths=paths,
        alpha1=alpha1,
        universe_size=universe_size,
        lambda_plus=lambda_plus,
        weight_scheme="uniform",
        weight_param=None,
    )


def slot_weights(
    paths: list[CandidatePath],
    universe_size: int,
    weight_scheme: str = "uniform",
    weight_param: float | None = None,
) -> dict[str, float]:
    if universe_size <= 0:
        raise ValueError("universe_size must be positive")
    ranks = range(1, universe_size + 1)
    if weight_scheme == "uniform":
        raw = [1.0 for _ in ranks]
    elif weight_scheme == "power":
        q = 0.5 if weight_param is None else float(weight_param)
        if q < 0:
            raise ValueError("power weight_param must be nonnegative")
        raw = [rank ** (-q) for rank in ranks]
    elif weight_scheme == "exponential":
        tau = 16.0 if weight_param is None else float(weight_param)
        if tau <= 0:
            raise ValueError("exponential weight_param must be positive")
        raw = [exp(-(rank - 1) / tau) for rank in ranks]
    else:
        raise ValueError(f"unknown weight scheme: {weight_scheme}")

    total = sum(raw)
    weights_by_rank = [value / total for value in raw]
    weights: dict[str, float] = {}
    for idx, path in enumerate(paths[:universe_size]):
        weights[path.path_id] = weights_by_rank[idx]
    return weights


def weighted_scs_greedy_select(
    paths: list[CandidatePath],
    alpha1: float,
    universe_size: int,
    lambda_plus: float,
    weight_scheme: str = "uniform",
    weight_param: float | None = None,
) -> SelectionResult:
    start = perf_counter()
    candidates = [p for p in paths if not p.is_dummy]
    max_k = min(universe_size, len(candidates))
    sorted_candidates = sorted(candidates, key=lambda p: p.utility, reverse=True)
    weights = slot_weights(paths, universe_size, weight_scheme, weight_param)

    for k in range(max_k, 0, -1):
        thresholds = {
            p.path_id: (
                1.0 / (alpha1 * k * weights[p.path_id])
                if weights.get(p.path_id, 0.0) > 0
                else inf
            )
            for p in candidates
        }
        eligible = [
            p for p in sorted_candidates if (p.evalue or 0.0) >= thresholds[p.path_id]
        ]
        if len(eligible) < k:
            continue
        selected: list[CandidatePath] = []
        used_nodes: set[str] = set()
        component_owner: dict[str, str] = {}
        for path in eligible:
            if _compatible(path, selected, used_nodes, component_owner, lambda_plus):
                _add_path(path, selected, used_nodes, component_owner)
            if len(selected) == k:
                selected_thresholds = {
                    path.path_id: thresholds[path.path_id] for path in selected
                }
                return SelectionResult(
                    selected=selected,
                    alpha1=alpha1,
                    universe_size=universe_size,
                    threshold=max(selected_thresholds.values()),
                    runtime_sec=perf_counter() - start,
                    reason="self_consistent",
                    path_thresholds=selected_thresholds,
                    slot_weights={path.path_id: weights[path.path_id] for path in selected},
                    weight_scheme=weight_scheme,
                    weight_param=weight_param,
                )

    return SelectionResult(
        selected=[],
        alpha1=alpha1,
        universe_size=universe_size,
        threshold=None,
        runtime_sec=perf_counter() - start,
        reason="no_self_consistent_set",
        path_thresholds={},
        slot_weights={},
        weight_scheme=weight_scheme,
        weight_param=weight_param,
    )


def post_filter_select(
    paths: list[CandidatePath],
    alpha1: float,
    universe_size: int,
) -> SelectionResult:
    start = perf_counter()
    threshold = 1.0 / alpha1
    selected = [
        path
        for path in paths
        if not path.is_dummy and (path.evalue or 0.0) >= threshold
    ]
    return SelectionResult(
        selected=selected,
        alpha1=alpha1,
        universe_size=universe_size,
        threshold=threshold,
        runtime_sec=perf_counter() - start,
        reason="post_filter_threshold",
        path_thresholds={path.path_id: threshold for path in selected},
    )


def oracle_utility_upper_bound(paths: list[CandidatePath], count: int) -> SelectionResult:
    start = perf_counter()
    selected = sorted(
        [path for path in paths if not path.is_dummy and path.Y],
        key=lambda p: p.utility,
        reverse=True,
    )[:count]
    return SelectionResult(
        selected=selected,
        alpha1=0.0,
        universe_size=len([p for p in paths if not p.is_dummy]),
        threshold=None,
        runtime_sec=perf_counter() - start,
        reason="oracle_true_utility_upper_bound",
        path_thresholds={},
    )
