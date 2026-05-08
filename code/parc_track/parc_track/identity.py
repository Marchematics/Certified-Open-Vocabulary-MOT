from __future__ import annotations

from dataclasses import dataclass

from .selector import SelectionResult
from .types import VideoBlock


@dataclass
class IdentityBound:
    video_id: str
    actual_idsw: int
    actual_idsw_per_min: float
    badlink_ub: int
    misscont_ub: int
    gap_sensor: int
    certified_ub: int
    certified_ub_per_min: float
    minutes: float
    tightness: float
    actual_idsw_source: str


def evaluate_clear_mot_bounds(
    video: VideoBlock,
    selection: SelectionResult,
    lambda_plus: float,
    lambda_minus: float,
) -> IdentityBound:
    selected = selection.selected
    selected_continuations: set[str] = set()
    selected_protected_components: set[str] = set()
    badlink_ub = 0

    for path in selected:
        selected_protected_components.update(path.protected_components)
        for edge in path.edges:
            if edge.r_plus >= lambda_plus and edge.bad_link:
                badlink_ub += 1
            if (
                edge.continuation_id is not None
                and edge.r_plus >= lambda_plus
                and edge.r_minus >= lambda_minus
            ):
                selected_continuations.add(edge.continuation_id)

    misscont_ub = len(video.protected_continuations - selected_continuations)
    gap_sensor = video.sensor_gaps
    certified_ub = badlink_ub + misscont_ub + gap_sensor
    minutes = max(video.minutes, 1e-12)

    uncovered_selected_continuations = len(
        selected_protected_components - selected_continuations
    )
    actual_idsw = badlink_ub + uncovered_selected_continuations
    actual_idsw_per_min = actual_idsw / minutes
    certified_ub_per_min = certified_ub / minutes
    tightness = certified_ub / max(actual_idsw, 1)
    return IdentityBound(
        video_id=video.video_id,
        actual_idsw=actual_idsw,
        actual_idsw_per_min=actual_idsw_per_min,
        badlink_ub=badlink_ub,
        misscont_ub=misscont_ub,
        gap_sensor=gap_sensor,
        certified_ub=certified_ub,
        certified_ub_per_min=certified_ub_per_min,
        minutes=video.minutes,
        tightness=tightness,
        actual_idsw_source="synthetic_proxy_selected_badlinks_plus_uncovered_selected_continuations",
    )
