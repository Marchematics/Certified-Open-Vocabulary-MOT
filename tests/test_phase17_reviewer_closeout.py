from pathlib import Path

import pandas as pd

from parc_track import phase17
from parc_track.phase17 import run_phase17_reviewer_closeout


def _patch_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))
    monkeypatch.setattr(phase17, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(phase17, "RELIABILITY_DIR", tmp_path / "outputs/milestones/reliability_fortress")
    monkeypatch.setattr(phase17, "PAPER_DIR", tmp_path / "outputs/milestones/reliability_fortress/paper_tables")
    monkeypatch.setattr(phase17, "REVIEW_DIR", tmp_path / "outputs/milestones/reliability_fortress/reviewer_closeout")
    monkeypatch.setattr(phase17, "AUDIT_REVIEW_DIR", tmp_path / "outputs/milestones/reliability_fortress/audit_review")
    monkeypatch.setattr(phase17, "LEGACY_DIR", tmp_path / "outputs/milestones/legacy_core_results")


def _write_sources(tmp_path: Path) -> None:
    legacy = tmp_path / "outputs/milestones/legacy_core_results"
    reliability = tmp_path / "outputs/milestones/reliability_fortress"
    paper = reliability / "paper_tables"
    benchmark_audit = tmp_path / "outputs/benchmarks/parc_certification_benchmark/audit"
    (legacy / "phase2h_first_real_nonempty").mkdir(parents=True, exist_ok=True)
    (legacy / "core_results").mkdir(parents=True, exist_ok=True)
    (legacy / "tao_full_clean").mkdir(parents=True, exist_ok=True)
    paper.mkdir(parents=True, exist_ok=True)
    benchmark_audit.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "alpha1": 0.1,
                "candidate_budget_M": 150,
                "released": 126,
                "unsupported_false": 0,
                "unsupported_uncertain": 1,
            }
        ]
    ).to_csv(legacy / "phase2h_first_real_nonempty/table_real_first_nonempty.csv", index=False)
    pd.DataFrame(
        [
            {
                "candidate_budget_M": 75,
                "released": 75,
                "unsupported_actually_false": 0,
                "unsupported_uncertain": 0,
            }
        ]
    ).to_csv(legacy / "core_results/table_m_sweep_parc_full_with_audit.csv", index=False)
    rows = []
    for alpha in (0.1, 0.2):
        for m in (75, 100, 125, 150, 175, 200, 250):
            for seed in range(3):
                released = 150 if alpha == 0.2 and m == 150 else (75 if alpha == 0.1 and m == 75 else 0)
                rows.append(
                    {
                        "method": "parc_track_gamma_tuned_uniform_scs",
                        "alpha1": alpha,
                        "candidate_budget_M": m,
                        "seed": seed,
                        "released": released,
                        "conservative_ftr_uncertain_and_unlabeled_false": 0.0 if released else "",
                        "best_margin": 1.0 if released else -1.0,
                    }
                )
    pd.DataFrame(rows).to_csv(legacy / "tao_full_clean/table_baseline_expanded.csv", index=False)
    pd.DataFrame([{"placeholder": 1}]).to_csv(paper / "table_main_raw_vs_parc.csv", index=False)
    pd.DataFrame(
        [
            {"metric": "rows_total", "value": 300},
            {"metric": "label_agreement_rate", "value": 0.9967},
            {"metric": "cohens_kappa", "value": 0.9917},
            {"metric": "verified_positive_agreement_rate", "value": 1.0},
        ]
    ).to_csv(benchmark_audit / "second_rater_agreement_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "video_id": 1,
                "path_id": "p_true",
                "label": "actually_true",
                "verified_positive_for_calibration": "yes",
                "pending_montage_path": "${PARC_TRACK_ROOT}/x.jpg",
            },
            {
                "dataset": "OVT-B",
                "video_id": 1,
                "path_id": "p_false",
                "label": "actually_false",
                "verified_positive_for_calibration": "no",
                "pending_montage_path": "${PARC_TRACK_ROOT}/y.jpg",
            },
            {
                "dataset": "OVT-B",
                "video_id": 2,
                "path_id": "p_uncertain",
                "label": "uncertain",
                "verified_positive_for_calibration": "no",
                "pending_montage_path": "${PARC_TRACK_ROOT}/z.jpg",
            },
        ]
    ).to_csv(reliability / "audit_labels_2000_human_reviewed.csv", index=False)


def test_phase17_reviewer_closeout_outputs(tmp_path: Path, monkeypatch) -> None:
    _patch_roots(tmp_path, monkeypatch)
    _write_sources(tmp_path)

    summary = run_phase17_reviewer_closeout()
    artifacts = {Path(p).name for p in summary["artifacts"]}
    assert "table_actual_ftr_validation.csv" in artifacts
    assert "table_tao_sensitivity_framing.csv" in artifacts
    assert "THEOREM1_MAIN_TEXT.md" in artifacts
    actual = pd.read_csv(tmp_path / "outputs/milestones/reliability_fortress/paper_tables/table_actual_ftr_validation.csv")
    assert {"controlled_simulation_known_ground_truth", "adversarial_score_overlap_known_ground_truth", "real_data_release_set_audit_anchor"}.issubset(
        set(actual["validation_block"])
    )
    sim = actual[actual["validation_block"].eq("controlled_simulation_known_ground_truth")]
    assert sim.groupby("certified_risk_level_alpha")["seed"].nunique().min() == 100
    assert (sim["actual_FTR"] <= sim["certified_risk_level_alpha"] + 1e-12).all()
    hard_summary = pd.read_csv(
        tmp_path / "outputs/milestones/reliability_fortress/paper_tables/table_actual_ftr_hard_regime_summary.csv"
    )
    assert hard_summary["mean_actual_FTR"].max() > 0.05
    assert (hard_summary["mean_actual_FTR"] <= hard_summary["certified_risk_level_alpha"]).all()
    tao = pd.read_csv(tmp_path / "outputs/milestones/reliability_fortress/paper_tables/table_tao_sensitivity_framing.csv")
    positive = tao[(tao["certified_risk_level_alpha"].eq(0.2)) & (tao["M"].eq(150))]
    assert not positive.empty
    assert int(positive["nonempty_seeds"].iloc[0]) == 3
    challenge = pd.read_csv(tmp_path / "outputs/milestones/reliability_fortress/audit_review/second_review_challenge_template_500.csv")
    leaked = {"label", "verified_positive_for_calibration", "review_label_v2"}.intersection(challenge.columns)
    assert not leaked
    review_status = pd.read_csv(tmp_path / "outputs/milestones/reliability_fortress/paper_tables/table_second_review_status.csv")
    challenge_status = review_status[review_status["review_block"].eq("stricter_blind_challenge")]
    assert challenge_status["status"].iloc[0] == "template_only_not_completed"
