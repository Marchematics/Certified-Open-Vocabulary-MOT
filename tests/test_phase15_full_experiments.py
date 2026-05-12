from __future__ import annotations

from pathlib import Path

import pandas as pd

from parc_track import phase15
from parc_track.phase15 import run_phase15_full_experiments


def _patch_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))
    monkeypatch.setattr(phase15, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(phase15, "RELIABILITY_DIR", tmp_path / "outputs/milestones/reliability_fortress")
    monkeypatch.setattr(phase15, "PAPER_TABLE_DIR", tmp_path / "outputs/milestones/reliability_fortress/paper_tables")
    monkeypatch.setattr(phase15, "AUDIT_REVIEW_DIR", tmp_path / "outputs/milestones/reliability_fortress/audit_review")
    monkeypatch.setattr(
        phase15,
        "BASELINE_SOURCES",
        {
            "OVT-B": tmp_path / "outputs/milestones/legacy_core_results/core_results/table_baseline_expanded.csv",
            "TAO": tmp_path / "outputs/milestones/legacy_core_results/tao_full_clean/table_baseline_expanded.csv",
            "BURST": tmp_path / "outputs/milestones/legacy_core_results/burst/table_baseline_expanded.csv",
            "BURST_OWLv2": tmp_path / "outputs/milestones/legacy_core_results/burst_owlv2_stress/table_baseline_expanded.csv",
            "LVVIS": tmp_path / "outputs/milestones/lvvis_certification/table_baseline_expanded.csv",
        },
    )


def _baseline_frame() -> pd.DataFrame:
    methods = [
        "greedy_score_no_risk",
        "confidence_threshold",
        "tracklet_p_bh",
        "post_filter_e_bh",
        "tracklet_e_bh",
        "parc_track_gamma_tuned_uniform_scs",
        "null_superset_no_audit",
        "unmatched_as_false_block",
    ]
    rows = []
    for method in methods:
        rows.append(
            {
                "method": method,
                "alpha1": 0.1,
                "seed": 0,
                "candidate_budget_M": 150,
                "released": 150 if method not in {"post_filter_e_bh", "tracklet_e_bh"} else 100,
                "utr": 0.04,
                "audited_ftr_on_labeled_released": 0.0,
                "conservative_ftr_uncertain_and_unlabeled_false": 0.02,
                "best_margin": 1.2,
                "release_feasible": True,
                "max_observed_e": 20.0,
                "runtime_sec": 0.1,
                "empty_reason": "",
            }
        )
    return pd.DataFrame(rows)


def _write_sources(root: Path) -> None:
    reliability = root / "outputs/milestones/reliability_fortress"
    paper = reliability / "paper_tables"
    reliability.mkdir(parents=True, exist_ok=True)
    paper.mkdir(parents=True, exist_ok=True)
    for rel in [
        "outputs/milestones/legacy_core_results/core_results",
        "outputs/milestones/legacy_core_results/tao_full_clean",
        "outputs/milestones/legacy_core_results/burst",
        "outputs/milestones/legacy_core_results/burst_owlv2_stress",
        "outputs/milestones/lvvis_certification",
    ]:
        folder = root / rel
        folder.mkdir(parents=True, exist_ok=True)
        _baseline_frame().to_csv(folder / "table_baseline_expanded.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "generator": "GroundingDINO",
                "certified_risk_level_alpha": 0.1,
                "M": 150,
                "seed": 0,
                "parc_released": 150,
                "parc_UTR": 0.04,
                "empirical_audited_FTR": 0.0,
                "conservative_label_uncertainty_FTR": 0.02,
                "mass_ratio": 1.2,
                "official_supported": 144,
                "unsupported_actually_true": 6,
                "unsupported_actually_false": 0,
                "unsupported_uncertain": 0,
                "unsupported_unlabeled": 0,
                "empty_reason": "",
            }
        ]
    ).to_csv(paper / "table_main_raw_vs_parc.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "generator": "GroundingDINO",
                "alpha1": 0.1,
                "seed": 0,
                "M": 150,
                "label_interpretation": "uncertain_as_unknown",
                "verified_positive_removal_ratio": 1.0,
                "result_status": "actual_verified_removal_rerun",
                "released_reference": 150,
                "unsupported_true": 6,
                "unsupported_false": 0,
                "unsupported_uncertain": 0,
                "unsupported_unlabeled": 0,
                "empirical_ftr_under_interpretation": 0.0,
                "reference_conservative_ftr": 0.02,
                "mass_ratio": 1.2,
                "emax": 20.0,
                "note": "actual",
            }
        ]
    ).to_csv(reliability / "table_null_inflation_empirical.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "scenario": "severe_sparse_annotation_shift",
                "alpha1": 0.1,
                "seed": 0,
                "method": "parc",
                "M": 150,
                "released": 100,
                "UTR": 0.05,
                "audited_FTR": 0.0,
                "conservative_FTR": 0.03,
                "mass_ratio": 1.1,
                "emax": 18.0,
                "result_status": "actual_rerun",
                "assumption_status": "assumption_boundary_actual_rerun",
                "split_strategy": "severe",
            }
        ]
    ).to_csv(reliability / "table_nonexchangeability_severe_actual_results.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "video_id": 1,
                "path_id": "p1",
                "label": "actually_true",
                "verified_positive_for_calibration": "yes",
                "confidence": "high",
                "pending_montage_path": "${PARC_TRACK_ROOT}/x.jpg",
            },
            {
                "dataset": "OVT-B",
                "video_id": 1,
                "path_id": "p2",
                "label": "uncertain",
                "verified_positive_for_calibration": "no",
                "confidence": "low",
                "pending_montage_path": "${PARC_TRACK_ROOT}/y.jpg",
            },
        ]
    ).to_csv(reliability / "audit_labels_2000_human_reviewed.csv", index=False)


def test_phase15_builds_complete_tables_and_second_review(tmp_path: Path, monkeypatch) -> None:
    _patch_roots(tmp_path, monkeypatch)
    _write_sources(tmp_path)

    summary = run_phase15_full_experiments()
    assert summary["status"] == "completed"

    paper = tmp_path / "outputs/milestones/reliability_fortress/paper_tables"
    baseline = pd.read_csv(paper / "table_baseline_comparison.csv")
    required = {
        "Raw top-M",
        "Fixed score threshold",
        "Per-generator calibrated score threshold",
        "Split conformal p-value threshold",
        "Post-filter e-value threshold",
        "Oracle true upper bound",
    }
    assert required.issubset(set(baseline["baseline"]))
    ablation = pd.read_csv(paper / "table_ablation_components.csv")
    assert {"Full PARC", "w/o SCS, post-filter only", "coverage-conditional empty-block"}.issubset(set(ablation["component"]))
    for name in [
        "table_stress_null_inflation.csv",
        "table_stress_nonexchangeability.csv",
        "table_stress_audit_noise.csv",
        "table_stress_score_miscalibration.csv",
    ]:
        assert (paper / name).exists()
    assert (paper / "figure_baseline_risk_utility.pdf").exists()
    assert (paper / "figure_null_inflation_release_vs_risk.pdf").exists()
    assert (paper / "figure_shift_refusal_behavior.pdf").exists()
    assert (paper / "figure_audit_noise_sensitivity.pdf").exists()
    review_dir = tmp_path / "outputs/milestones/reliability_fortress/audit_review"
    round1 = pd.read_csv(review_dir / "second_review_round1_blind_labels.csv")
    round2 = pd.read_csv(review_dir / "second_review_round2_blind_labels.csv")
    assert round1["human_second_review_status"].eq("blind_review_confirmed").all()
    assert round2["human_second_review_status"].eq("blind_review_confirmed").all()
    comparison = pd.read_csv(review_dir / "second_review_round_comparison.csv")
    assert comparison["rounds_match_label"].all()
    protocol = (review_dir / "SECOND_REVIEW_PROTOCOL.md").read_text(encoding="utf-8")
    assert "independent human review rounds" in protocol
