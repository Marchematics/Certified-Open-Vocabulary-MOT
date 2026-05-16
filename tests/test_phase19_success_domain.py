from __future__ import annotations

from pathlib import Path

import pandas as pd

from parc_track import phase19
from parc_track.phase19 import run_phase19_success_domain


def _patch_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))
    monkeypatch.setattr(phase19, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(phase19, "SUCCESS_DIR", tmp_path / "outputs/milestones/scientific_release_success_map")
    monkeypatch.setattr(phase19, "CTC_LEARNED_DIR", tmp_path / "outputs/milestones/scientific_domain_ctc_learned")
    monkeypatch.setattr(phase19, "MATERIALS_DIR", tmp_path / "outputs/milestones/scientific_domain_materials")
    monkeypatch.setattr(phase19, "IWILDCAM_DIR", tmp_path / "outputs/milestones/scientific_domain_iwildcam_human_audit")
    monkeypatch.setattr(phase19, "SPACENET_REAL_DIR", tmp_path / "outputs/spacenet7_real_audit")
    monkeypatch.setattr(phase19, "RELEASE_DIAG_DIR", tmp_path / "outputs/milestones/release_story/paper_diagnostics")


def _write_inputs(tmp_path: Path) -> None:
    ctc = tmp_path / "outputs/milestones/scientific_domain_ctc_learned"
    mat = tmp_path / "outputs/milestones/scientific_domain_materials"
    iw = tmp_path / "outputs/milestones/scientific_domain_iwildcam_human_audit"
    sp = tmp_path / "outputs/spacenet7_real_audit"
    diag = tmp_path / "outputs/milestones/release_story/paper_diagnostics"
    for path in (ctc, mat, iw, sp, diag):
        path.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {
                "domain": "biomedical_cell_tracking",
                "rho": 0.1,
                "alpha": 0.1,
                "M": 100,
                "seeds": 20,
                "nonempty_seeds": 20,
                "released_mean": 100,
                "actual_FTR_mean": 0,
                "actual_FTR_max": 0,
                "raw_topM_actual_FTR_mean": 0,
                "max_observed_e_mean": 13.4,
                "required_e": 10,
                "best_mass_ratio_mean": 1.34,
            }
        ]
    ).to_csv(ctc / "table_ctc_learned_strict_alpha010_smallK.csv", index=False)
    pd.DataFrame(
        [
            {
                "domain": "biomedical_cell_tracking",
                "alpha": 0.1,
                "M": 100,
                "seeds": 20,
                "nonempty_seeds": 0,
                "released_mean": 0,
                "actual_FTR_mean": 0,
                "raw_topM_actual_FTR_mean": 0.8,
                "max_observed_e_mean": 8,
                "required_e": 10,
                "best_mass_ratio_mean": 0.2,
            }
        ]
    ).to_csv(ctc / "table_ctc_learned_negative_control.csv", index=False)
    pd.DataFrame(
        [
            {
                "proposal_source": "cgcnn",
                "rho": 0.1,
                "alpha": 0.1,
                "K": 100,
                "seeds": 20,
                "non_empty_seeds": 20,
                "mean_release": 95,
                "actual_FTR_mean": 0.03,
                "raw_topK_actual_FTR_mean": 0.0,
                "best_mass_ratio_mean": 2.0,
                "max_observed_e_mean": 50,
                "required_e": 10,
                "block_coverage_mean": 0.9,
            }
        ]
    ).to_csv(mat / "table_materials_primary_results.csv", index=False)
    pd.DataFrame([{"proposal_source": "cgcnn", "K": 100, "raw_topK_actual_FTR": 0.0}]).to_csv(
        mat / "table_materials_raw_topK_baseline.csv", index=False
    )
    pd.DataFrame().to_csv(mat / "table_materials_modern_model_sensitivity.csv", index=False)
    pd.DataFrame().to_csv(mat / "table_materials_high_volume_refusal.csv", index=False)
    pd.DataFrame(
        [
            {
                "alpha": 0.2,
                "K": 50,
                "non_empty_seeds": 20,
                "mean_release": 50,
                "mean_best_mass_ratio": 1.1,
                "max_observed_e": 6,
                "required_e": 5,
                "source_name": "animal detector",
            }
        ]
    ).to_csv(iw / "table_iwildcam_human_audit_primary_results.csv", index=False)
    pd.DataFrame(
        [{"endpoint_alpha": 0.2, "endpoint_K": 50, "human_FTR": 0.0, "conservative_human_FTR": 0.0}]
    ).to_csv(iw / "table_iwildcam_release_audit_summary.csv", index=False)
    pd.DataFrame([{"human_FTR": 0.0}]).to_csv(iw / "table_iwildcam_raw_topk_audit_summary.csv", index=False)
    pd.DataFrame([{"cohen_kappa": 0.8}]).to_csv(iw / "table_iwildcam_second_review_agreement_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "K": 50,
                "alpha": 0.2,
                "non_empty_seeds": 18,
                "total_seeds": 20,
                "mean_release_across_seeds": 44,
                "audited_FTR_uncertain_as_false": 0,
                "mean_mass_ratio": 1.1,
            }
        ]
    ).to_csv(sp / "table_spacenet7_real_audit_k50_completed_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "K": 100,
                "alpha": 0.2,
                "non_empty_seeds": 0,
                "total_seeds": 20,
                "mean_best_mass_ratio": 0.6,
                "mean_max_observed_e": 6,
                "required_e": 5,
            }
        ]
    ).to_csv(sp / "table_spacenet7_real_audit_primary_refusal_diagnostics.csv", index=False)
    pd.DataFrame([{"domain": "x", "row": "y"}]).to_csv(diag / "table_assumption_diagnostic_panel.csv", index=False)


def test_phase19_success_domain_tables(tmp_path: Path, monkeypatch) -> None:
    _patch_roots(tmp_path, monkeypatch)
    _write_inputs(tmp_path)

    summary = run_phase19_success_domain()
    assert summary["status"] == "completed"
    assert summary["n_evidence_rows"] >= 4
    assert summary["n_protocol_only_rows"] >= 1

    out = tmp_path / "outputs/milestones/scientific_release_success_map"
    evidence = pd.read_csv(out / "table_cross_domain_evidence_matrix.csv")
    assert {"domain", "PARC_FTR", "raw_topK_FTR", "false_releases_prevented_est"}.issubset(evidence.columns)
    assert "main_flagship" in set(evidence["paper_status"])
    assert "protocol_only_not_evidence" in set(pd.read_csv(out / "table_strict_real_audit_protocols.csv")["paper_use_before_completion"])

    features = pd.read_csv(out / "table_success_domain_features.csv")
    assert {"phi_ge_1", "release_success_binary", "risk_success_binary"}.issubset(features.columns)

    checklist = pd.read_csv(out / "table_practitioner_success_checklist.csv")
    assert "sufficient_evidence_mass" in set(checklist["condition"])

