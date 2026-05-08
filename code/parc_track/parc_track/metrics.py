from __future__ import annotations

from dataclasses import asdict

from .identity import IdentityBound
from .selector import SelectionResult
from .types import VideoBlock


def evaluate_selection(video: VideoBlock, selection: SelectionResult) -> dict[str, float | int | str]:
    selected = selection.selected
    released = len(selected)
    false_tracks = sum(1 for path in selected if not path.Y)
    unsupported = sum(1 for path in selected if not path.A)
    true_tracks = sum(1 for path in selected if path.Y)
    total_true = sum(1 for path in video.paths if not path.is_dummy and path.Y)
    actual_fdp = false_tracks / released if released else 0.0
    utr = unsupported / released if released else 0.0
    recall = true_tracks / total_true if total_true else 0.0
    utility = sum(path.utility for path in selected)
    return {
        "video_id": video.video_id,
        "released_tracks": released,
        "false_tracks": false_tracks,
        "true_tracks": true_tracks,
        "unsupported_tracks": unsupported,
        "actual_fdp": actual_fdp,
        "utr": utr,
        "novel_recall": recall,
        "utility": utility,
        "runtime_sec": selection.runtime_sec,
        "reason": selection.reason,
    }


def aggregate_rows(rows: list[dict[str, float | int | str]], alpha1: float) -> dict[str, float | int]:
    released = sum(int(row["released_tracks"]) for row in rows)
    false_tracks = sum(int(row["false_tracks"]) for row in rows)
    true_tracks = sum(int(row["true_tracks"]) for row in rows)
    unsupported = sum(int(row["unsupported_tracks"]) for row in rows)
    actual_ftr = false_tracks / released if released else 0.0
    utr = unsupported / released if released else 0.0
    violation_rate = (
        sum(1 for row in rows if float(row["actual_fdp"]) > alpha1) / len(rows)
        if rows
        else 0.0
    )
    mean_recall = (
        sum(float(row["novel_recall"]) for row in rows) / len(rows)
        if rows
        else 0.0
    )
    mean_runtime = (
        sum(float(row["runtime_sec"]) for row in rows) / len(rows)
        if rows
        else 0.0
    )
    return {
        "target_alpha1": alpha1,
        "empirical_actual_ftr": actual_ftr,
        "utr": utr,
        "released_tracks": released,
        "true_tracks": true_tracks,
        "false_tracks": false_tracks,
        "unsupported_tracks": unsupported,
        "violation_rate": violation_rate,
        "mean_novel_recall": mean_recall,
        "mean_runtime_sec": mean_runtime,
    }


def identity_rows(bounds: list[IdentityBound]) -> list[dict[str, float | int | str]]:
    return [asdict(bound) for bound in bounds]
