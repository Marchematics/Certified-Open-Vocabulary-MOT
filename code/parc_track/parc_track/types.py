from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Cell = tuple[str, ...]


@dataclass(frozen=True)
class AssociationEdge:
    edge_id: str
    source: str
    target: str
    r_plus: float
    r_minus: float
    bad_link: bool = False
    continuation_id: str | None = None


@dataclass
class CandidatePath:
    path_id: str
    video_id: str
    nodes: tuple[str, ...]
    edges: tuple[AssociationEdge, ...]
    cell: Cell
    checkpoint_scores: dict[float, float]
    utility: float
    A: bool
    Y: bool
    conflicts: frozenset[str] = field(default_factory=frozenset)
    protected_components: frozenset[str] = field(default_factory=frozenset)
    evalue: float | None = None
    p_any: float | None = None
    p_values: dict[float, float] = field(default_factory=dict)
    is_dummy: bool = False

    @property
    def length(self) -> float:
        return max(self.checkpoint_scores) if self.checkpoint_scores else 0.0

    def score_at(self, checkpoint: float) -> float | None:
        if checkpoint in self.checkpoint_scores:
            return self.checkpoint_scores[checkpoint]
        earlier = [k for k in self.checkpoint_scores if k <= checkpoint]
        if not earlier:
            return None
        return self.checkpoint_scores[max(earlier)]

    def has_only_safe_edges(self, lambda_plus: float) -> bool:
        return all(edge.r_plus >= lambda_plus for edge in self.edges)


@dataclass
class VideoBlock:
    video_id: str
    paths: list[CandidatePath]
    minutes: float
    protected_continuations: frozenset[str] = field(default_factory=frozenset)
    sensor_gaps: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int
    candidate_budget: int
    alpha1: float
    alpha2: float
    gamma: float
    release_grid: tuple[float, ...]
    release_weights: tuple[float, ...]
    lambda_plus: float
    lambda_minus: float
    min_cal_blocks: int = 10

    @classmethod
    def from_mapping(cls, cfg: dict[str, Any]) -> "ExperimentConfig":
        release_grid = tuple(float(x) for x in cfg["release_grid"])
        weights = cfg.get("release_weights")
        if weights is None:
            weights_tuple = tuple(1.0 / len(release_grid) for _ in release_grid)
        else:
            weights_tuple = tuple(float(x) for x in weights)
        if len(weights_tuple) != len(release_grid):
            raise ValueError("release_weights must match release_grid length")
        if sum(weights_tuple) > 1.0 + 1e-12:
            raise ValueError("release_weights must sum to <= 1")
        selector = cfg.get("selector", {})
        return cls(
            seed=int(cfg["seed"]),
            candidate_budget=int(cfg["M"]),
            alpha1=float(cfg["alpha1"]),
            alpha2=float(cfg["alpha2"]),
            gamma=float(cfg["gamma"]),
            release_grid=release_grid,
            release_weights=weights_tuple,
            lambda_plus=float(selector.get("lambda_plus", 0.85)),
            lambda_minus=float(selector.get("lambda_minus", 0.85)),
            min_cal_blocks=int(cfg.get("min_cal_blocks", 10)),
        )
