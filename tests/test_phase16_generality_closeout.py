from __future__ import annotations

from pathlib import Path

import pandas as pd

from parc_track.phase16 import run_phase16_generality_closeout


def _patch_roots(tmp_path: Path, monkeypatch) -> None:
    import parc_track.phase16 as phase16

    root = tmp_path
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))
    monkeypatch.setattr(phase16, "DATA_ROOT", root)
    monkeypatch.setattr(phase16, "RELIABILITY_DIR", root / "outputs/milestones/reliability_fortress")
    monkeypatch.setattr(phase16, "GENERALITY_DIR", root / "outputs/milestones/generality_reliability")
    monkeypatch.setattr(phase16, "PAPER_DIR", root / "outputs/milestones/reliability_fortress/paper_tables")
    monkeypatch.setattr(phase16, "FIGURE_DIR", root / "outputs/milestones/reliability_fortress/figures_publication")
    monkeypatch.setattr(phase16, "GENERALITY_TABLE_DIR", root / "outputs/milestones/generality_reliability/paper_tables")


def _write_inputs(tmp_path: Path) -> None:
    gen = tmp_path / "outputs/milestones/generality_reliability"
    paper = tmp_path / "outputs/milestones/reliability_fortress/paper_tables"
    gen.mkdir(parents=True, exist_ok=True)
    paper.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"dataset": "LVIS", "detector": "GroundingDINO", "method": "parc", "alpha1": 0.1, "seed": 0, "M": 150, "released": 10, "UTR": 0.0, "conservative_FTR": 0.0, "mass_ratio": 1.2, "empty_reason": ""},
            {"dataset": "LVIS", "detector": "OWLv2", "method": "parc", "alpha1": 0.1, "seed": 0, "M": 150, "released": 0, "UTR": 0.0, "conservative_FTR": 0.0, "mass_ratio": 0.4, "empty_reason": "no_k"},
        ]
    ).to_csv(gen / "table_lvis_detection_certification.csv", index=False)
    pd.DataFrame(
        [
            {"detector": "GroundingDINO", "score": 0.9, "is_matched_to_gt": True},
            {"detector": "OWLv2", "score": 0.8, "is_matched_to_gt": False},
        ]
    ).to_csv(gen / "candidate_universe.csv", index=False)
    pd.DataFrame(
        [
            {"dataset": "BURST", "task": "mask", "alpha1": 0.1, "seed": 0, "M": 150, "released": 10, "UTR": 0.1, "conservative_FTR": 0.1, "mass_ratio": 1.1, "mask_iou_threshold": 0.5}
        ]
    ).to_csv(gen / "table_ovvis_mask_certification.csv", index=False)
    pd.DataFrame(
        [
            {"dataset": "OVT-B", "generator": "GroundingDINO", "baseline": "Raw top-M", "released": 150, "conservative_label_uncertainty_FTR": 0.2},
            {"dataset": "OVT-B", "generator": "GroundingDINO", "baseline": "Full PARC", "released": 100, "conservative_label_uncertainty_FTR": 0.01},
            {"dataset": "OVT-B", "generator": "GroundingDINO", "baseline": "Post-filter e-value threshold", "released": 80, "conservative_label_uncertainty_FTR": 0.02},
            {"dataset": "OVT-B", "generator": "GroundingDINO", "baseline": "Oracle true upper bound", "released": 150, "conservative_label_uncertainty_FTR": 0.0},
        ]
    ).to_csv(paper / "table_baseline_comparison.csv", index=False)
    pd.DataFrame(
        [
            {"best_mass_ratio": 0.5, "max_observed_e": 5, "safe_refusal_reason": "insufficient_high_e_mass"}
        ]
    ).to_csv(paper / "table_safe_refusal_diagnostics.csv", index=False)
    pd.DataFrame([{"label_keep_rate": 1.0, "released": 10}]).to_csv(paper / "table_stress_null_inflation.csv", index=False)
    pd.DataFrame([{"noise_rate": 0.0, "conservative_FTR": 0.1}]).to_csv(paper / "table_stress_audit_noise.csv", index=False)
    pd.DataFrame([{"shift_scenario": "tail", "released": 0}]).to_csv(paper / "table_stress_nonexchangeability.csv", index=False)
    pd.DataFrame(
        [
            {"dimension": "size", "level": "small", "official_support_rate": 0.2, "human_valid_rate": 0.8}
        ]
    ).to_csv(gen / "figure_stratified_reliability.csv", index=False)


def test_phase16_generality_closeout(tmp_path: Path, monkeypatch) -> None:
    _patch_roots(tmp_path, monkeypatch)
    _write_inputs(tmp_path)

    summary = run_phase16_generality_closeout()
    assert summary["status"] == "completed"

    out = tmp_path / "outputs/milestones/generality_reliability/paper_tables"
    lvis = pd.read_csv(out / "table_lvis_detection_main.csv")
    assert {"certified_risk_target_alpha", "empirical_audited_false_rate", "conservative_unknown_as_false_rate"}.issubset(lvis.columns)
    assert "appendix_stress" in set(lvis["paper_placement"])
    raw = pd.read_csv(out / "table_lvis_raw_detector_vs_parc.csv")
    assert {"raw detector top-M", "PARC certified release"}.issubset(set(raw["policy"]))
    mask = pd.read_csv(out / "table_mask_path_proof_of_principle.csv")
    assert mask["paper_placement"].eq("appendix_proof_of_principle").all()

    figs = tmp_path / "outputs/milestones/reliability_fortress/figures_publication"
    for name in [
        "figure_lvis_raw_detector_vs_parc.pdf",
        "figure_3_risk_utility_frontier.pdf",
        "figure_4_safe_refusal_diagnostics.pdf",
        "figure_5_stress_tests.pdf",
        "figure_6_stratified_reliability.pdf",
    ]:
        assert (figs / name).exists()

    assert (tmp_path / "environment.yml").exists()
    assert (tmp_path / "requirements.lock.txt").exists()
    assert (tmp_path / "Dockerfile").exists()
