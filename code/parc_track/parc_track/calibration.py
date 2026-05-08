from __future__ import annotations

from dataclasses import dataclass, field
from math import inf

from .types import CandidatePath, Cell, ExperimentConfig, VideoBlock


GLOBAL_CELL: Cell = ("global",)


@dataclass
class CalibrationTable:
    block_maxima: dict[tuple[Cell, float], list[float]]
    release_grid: tuple[float, ...]
    release_weights: tuple[float, ...]
    gamma: float
    min_cal_blocks: int
    fallback_records: list[dict[str, object]] = field(default_factory=list)

    def candidates_for(self, cell: Cell) -> list[Cell]:
        cells: list[Cell] = [cell]
        for keep in range(len(cell) - 1, 0, -1):
            cells.append(cell[:keep])
        cells.append(GLOBAL_CELL)
        return cells

    def resolve_cell(self, cell: Cell, checkpoint: float) -> Cell:
        for candidate in self.candidates_for(cell):
            values = self.block_maxima.get((candidate, checkpoint), [])
            finite_count = sum(1 for value in values if value < inf)
            if finite_count >= self.min_cal_blocks:
                if candidate != cell:
                    self.fallback_records.append(
                        {
                            "requested": cell,
                            "resolved": candidate,
                            "checkpoint": checkpoint,
                            "finite_blocks": finite_count,
                        }
                    )
                return candidate
        return GLOBAL_CELL


def _cell_prefixes(cell: Cell) -> list[Cell]:
    prefixes = [cell[:keep] for keep in range(len(cell), 0, -1)]
    prefixes.append(GLOBAL_CELL)
    return prefixes


def calibrate_null_superset(
    cal_videos: list[VideoBlock],
    cfg: ExperimentConfig,
) -> CalibrationTable:
    """Compute per-video null-superset block maxima.

    Verified positives (A=True) are removed. Unknown paths remain and therefore
    conservatively contain every actual false path because false paths never have
    one-sided positive labels.
    """

    block_maxima: dict[tuple[Cell, float], list[float]] = {}
    all_cells: set[Cell] = set()
    for video in cal_videos:
        for path in video.paths:
            if path.is_dummy:
                continue
            for prefix in _cell_prefixes(path.cell):
                all_cells.add(prefix)
    all_cells.add(GLOBAL_CELL)

    for checkpoint in cfg.release_grid:
        for cell in all_cells:
            block_maxima[(cell, checkpoint)] = []

    for video in cal_videos:
        for checkpoint in cfg.release_grid:
            per_cell: dict[Cell, list[float]] = {cell: [] for cell in all_cells}
            for path in video.paths:
                if path.is_dummy or path.A or path.length < checkpoint:
                    continue
                score = path.score_at(checkpoint)
                if score is None:
                    continue
                for prefix in _cell_prefixes(path.cell):
                    per_cell[prefix].append(score)
            for cell in all_cells:
                values = per_cell[cell]
                block_maxima[(cell, checkpoint)].append(max(values) if values else inf)

    return CalibrationTable(
        block_maxima=block_maxima,
        release_grid=cfg.release_grid,
        release_weights=cfg.release_weights,
        gamma=cfg.gamma,
        min_cal_blocks=cfg.min_cal_blocks,
    )


def block_p_value(score: float, cell: Cell, checkpoint: float, table: CalibrationTable) -> float:
    resolved = table.resolve_cell(cell, checkpoint)
    maxima = table.block_maxima[(resolved, checkpoint)]
    ge_count = sum(1 for value in maxima if value >= score)
    return (1.0 + ge_count) / (len(maxima) + 1.0)


def e_calibrator(p_value: float, gamma: float) -> float:
    p = min(max(p_value, 1e-300), 1.0)
    return gamma * (p ** (gamma - 1.0))


def compute_release_grid_evalues(
    paths: list[CandidatePath],
    table: CalibrationTable,
) -> list[CandidatePath]:
    for path in paths:
        if path.is_dummy:
            path.p_values = {}
            path.p_any = 1.0
            path.evalue = 0.0
            continue
        p_values: dict[float, float] = {}
        adjusted: list[float] = []
        for checkpoint, weight in zip(table.release_grid, table.release_weights):
            if checkpoint > path.length:
                continue
            score = path.score_at(checkpoint)
            if score is None:
                continue
            p_l = block_p_value(score, path.cell, checkpoint, table)
            p_values[checkpoint] = p_l
            adjusted.append(min(p_l / weight, 1.0))
        p_any = min(adjusted) if adjusted else 1.0
        path.p_values = p_values
        path.p_any = p_any
        path.evalue = e_calibrator(p_any, table.gamma)
    return paths
