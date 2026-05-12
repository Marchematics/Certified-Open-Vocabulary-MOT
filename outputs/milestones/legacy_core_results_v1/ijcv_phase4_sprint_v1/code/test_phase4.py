from __future__ import annotations

import pandas as pd

from parc_track.phase2 import _best_mass_summary
from parc_track.phase4 import _iou_matrix, _score_variant


def test_prop5_mass_ratio_marks_feasible_and_infeasible_rows() -> None:
    feasible = _best_mass_summary([10.0] * 10, alpha1=0.1, candidate_budget_m=10)
    assert feasible["released_unconstrained"] is True
    assert feasible["best_mass_ratio"] >= 1.0

    infeasible = _best_mass_summary([9.0] * 10, alpha1=0.1, candidate_budget_m=10)
    assert infeasible["released_unconstrained"] is False
    assert infeasible["best_mass_ratio"] < 1.0


def test_score_variants_change_scores_without_changing_candidate_identity() -> None:
    frame = pd.DataFrame(
        {
            "path_id": ["a", "b"],
            "score": [0.8, 0.7],
            "objectness": [0.8, 0.7],
            "semantic_margin": [0.6, 0.9],
            "temporal_stability": [8, 4],
            "association_score": [0.2, 0.9],
            "path_length": [8, 4],
        }
    )
    identities = frame["path_id"].tolist()
    detector_only = _score_variant(frame, "detector_only")
    weighted = _score_variant(frame, "weighted_components")

    assert frame["path_id"].tolist() == identities
    assert detector_only.tolist() == [0.8, 0.7]
    assert len(weighted) == len(frame)
    assert weighted.iloc[0] != detector_only.iloc[0]


def test_iou_matrix_uses_nan_free_distances_for_basic_boxes() -> None:
    gt = pd.DataFrame({"x": [0.0], "y": [0.0], "w": [10.0], "h": [10.0]})
    pred = pd.DataFrame(
        {
            "x": [0.0, 20.0],
            "y": [0.0, 20.0],
            "w": [10.0, 5.0],
            "h": [10.0, 5.0],
        }
    )
    ious = _iou_matrix(gt, pred)
    assert ious.shape == (1, 2)
    assert ious[0, 0] == 1.0
    assert ious[0, 1] == 0.0
