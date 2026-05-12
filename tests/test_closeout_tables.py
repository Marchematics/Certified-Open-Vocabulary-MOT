from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from parc_track import phase14
from parc_track.phase14 import run_phase14_closeout


def _patch_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))
    monkeypatch.setattr(phase14, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(phase14, "RELIABILITY_DIR", tmp_path / "outputs/milestones/reliability_fortress")
    monkeypatch.setattr(phase14, "RELEASE_STORY_DIR", tmp_path / "outputs/milestones/release_story")
    monkeypatch.setattr(phase14, "LVVIS_DIR", tmp_path / "outputs/milestones/lvvis_certification")
    monkeypatch.setattr(phase14, "PAPER_TABLE_DIR", tmp_path / "outputs/milestones/reliability_fortress/paper_tables")
    monkeypatch.setattr(phase14, "QUALITATIVE_GALLERY", tmp_path / "docs/qualitative_release_gallery.md")
    monkeypatch.setattr(phase14, "FIGURES_DIR", tmp_path / "figures")
    monkeypatch.setattr(
        phase14,
        "BURST_MATRIX",
        tmp_path / "outputs/milestones/legacy_core_results/burst/burst_alpha_seed_m_matrix.csv",
    )
    monkeypatch.setattr(
        phase14,
        "BURST_OWLV2_MATRIX",
        tmp_path / "outputs/milestones/legacy_core_results/burst_owlv2_stress/burst_alpha_seed_m_matrix.csv",
    )
    monkeypatch.setattr(
        phase14,
        "CROSS_DATASET_CERT",
        tmp_path / "outputs/milestones/legacy_core_results/cross_dataset/table_cross_dataset_certification.csv",
    )


def _write_sources(root: Path) -> None:
    reliability = root / "outputs/milestones/reliability_fortress"
    lvvis = root / "outputs/milestones/lvvis_certification"
    legacy = root / "outputs/milestones/legacy_core_results"
    reliability.mkdir(parents=True, exist_ok=True)
    lvvis.mkdir(parents=True, exist_ok=True)
    (legacy / "cross_dataset").mkdir(parents=True, exist_ok=True)
    (legacy / "burst").mkdir(parents=True, exist_ok=True)
    (legacy / "burst_owlv2_stress").mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "generator": "GroundingDINO",
                "dataset": "OVT-B",
                "alpha1": 0.1,
                "seed": 0,
                "released": 126,
                "UTR": 0.079,
                "conservative_FTR": 0.008,
                "mass_ratio": 1.2,
                "empty_reason": "",
                "result_type": "seed_result",
            },
            {
                "generator": "OWLv2",
                "dataset": "TAO",
                "alpha1": 0.1,
                "seed": 1,
                "released": 0,
                "UTR": 0.0,
                "conservative_FTR": 0.0,
                "mass_ratio": 0.42,
                "empty_reason": "no_k_satisfies_uniform_self_consistency",
                "result_type": "seed_result",
            },
            {
                "generator": "OVTR",
                "dataset": "TAO",
                "alpha1": 0.1,
                "seed": 0,
                "released": 0,
                "UTR": 0.0,
                "conservative_FTR": 0.0,
                "mass_ratio": 0.2,
                "empty_reason": "local_repo_present_no_prediction",
                "result_type": "published_tracker_provenance_pending",
            },
            {
                "generator": "GroundingDINO",
                "dataset": "OVT-B",
                "alpha1": 0.1,
                "seed": "meanstd",
                "released": 100,
                "UTR": 0.1,
                "conservative_FTR": 0.1,
                "mass_ratio": 1.0,
                "empty_reason": "",
                "result_type": "meanstd_existing_certificate",
            },
        ]
    ).to_csv(reliability / "table_blackbox_generator_certification.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "label": "actually_true",
                "verified_positive_for_calibration": "yes",
            }
        ]
    ).to_csv(reliability / "audit_labels_2000_human_reviewed.csv", index=False)
    pd.DataFrame(
        [
            {
                "method": "parc_track_gamma_tuned_uniform_scs",
                "alpha1": 0.1,
                "seed": 0,
                "candidate_budget_M": 150,
                "released": 150,
                "utr": 0.02,
                "audited_ftr_on_labeled_released": 0.0,
                "conservative_ftr_uncertain_and_unlabeled_false": 0.02,
                "best_margin": 2.0,
                "release_feasible": True,
                "empty_reason": "",
            },
            {
                "method": "post_filter_e_bh",
                "alpha1": 0.1,
                "seed": 0,
                "candidate_budget_M": 150,
                "released": 100,
                "utr": 0.05,
                "audited_ftr_on_labeled_released": 0.01,
                "conservative_ftr_uncertain_and_unlabeled_false": 0.03,
                "best_margin": 1.1,
                "release_feasible": True,
                "empty_reason": "",
            },
        ]
    ).to_csv(lvvis / "table_baseline_expanded.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "method": "parc_track_gamma_tuned_uniform_scs",
                "alpha1": 0.1,
                "seed": 0,
                "candidate_budget_M": 150,
                "released": 105,
                "utr": 0.02,
                "audited_ftr_supported_plus_labeled": 0.0,
                "conservative_ftr_uncertain_and_unlabeled_false": 0.01,
                "self_consistency_margin": 0.9,
                "tau_k": 14.2,
                "selected_e_min": 15.1,
                "selected_e_mean": 22.3,
                "selected_e_max": 38.5,
                "max_observed_e": 38.5,
                "empty_reason": "",
            }
        ]
    ).to_csv(legacy / "cross_dataset/table_cross_dataset_certification.csv", index=False)
    burst_rows = [
        {
            "method": "parc_track_gamma_tuned_uniform_scs",
            "alpha1": 0.1,
            "seed": 0,
            "candidate_budget_M": 150,
            "released": 150,
            "utr": 0.04,
            "audited_ftr_on_labeled_released": 0.0,
            "conservative_ftr_uncertain_and_unlabeled_false": 0.04,
            "best_margin": 9.6,
            "best_margin_tau": 15.3,
            "release_feasible": True,
            "max_observed_e": 24.9,
            "mean_observed_e": 21.1,
            "empty_reason": "",
        }
    ]
    pd.DataFrame(burst_rows).to_csv(legacy / "burst/burst_alpha_seed_m_matrix.csv", index=False)
    burst_rows[0] = dict(burst_rows[0], released=0, utr=0.0, conservative_ftr_uncertain_and_unlabeled_false=0.0, best_margin=-9.1, empty_reason="no_k_satisfies_uniform_self_consistency")
    pd.DataFrame(burst_rows).to_csv(legacy / "burst_owlv2_stress/burst_alpha_seed_m_matrix.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "scenario": "severe_sparse_annotation_shift",
                "alpha1": 0.1,
                "seed": 0,
                "method": "parc",
                "M": 150,
                "released": 150,
                "UTR": 0.05,
                "audited_FTR": 0.0,
                "conservative_FTR": 0.02,
                "mass_ratio": 1.7,
                "emax": 30.0,
                "empty_reason": "",
                "result_status": "actual_rerun",
                "assumption_status": "assumption_boundary_actual_rerun",
            }
        ]
    ).to_csv(reliability / "table_nonexchangeability_severe_actual_results.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "scenario": "verified_positive_removal_ratio",
                "alpha1": 0.1,
                "seed": 0,
                "method": "parc",
                "M": 150,
                "released": 105,
                "UTR": 0.02,
                "audited_FTR": 0.0,
                "conservative_FTR": 0.01,
                "mass_ratio": 1.1,
                "emax": 38.0,
                "empty_reason": "",
                "result_status": "actual_rerun",
            }
        ]
    ).to_csv(reliability / "table_null_inflation_verified_removal_actual_results.csv", index=False)


def test_closeout_tables_are_clean_and_have_refusal_diagnostics(tmp_path: Path, monkeypatch) -> None:
    _patch_roots(tmp_path, monkeypatch)
    _write_sources(tmp_path)

    summary = run_phase14_closeout()

    out_dir = tmp_path / "outputs/milestones/reliability_fortress/paper_tables"
    assert summary["status"] == "completed"
    dirty_tokens = [
        "/tmp/",
        "existing_certificate_row",
        "meanstd_existing_certificate",
        "rerun_required",
        "scaffold_only",
        "local_repo_present_no_prediction",
        "tpami_",
        "nmi" + "_release_story",
    ]
    for table_path in out_dir.glob("table_*.csv"):
        text = table_path.read_text(encoding="utf-8")
        assert not any(token in text for token in dirty_tokens), table_path
        assert table_path.with_suffix(table_path.suffix + ".provenance.json").exists()

    main = pd.read_csv(out_dir / "table_main_raw_vs_parc.csv")
    assert "OVTR" not in set(main["generator"])
    assert "GroundingDINO + tracker" in set(main["generator"])
    assert ((main["dataset"] == "BURST") & (main["generator"] == "OWLv2")).any()
    required_schema = {
        "dataset",
        "generator",
        "alpha",
        "certified_risk_level_alpha",
        "M",
        "seed",
        "raw_topM_released",
        "raw_topM_audited_false_rate",
        "raw_topM_unsupported_rate",
        "parc_released",
        "parc_UTR",
        "parc_audited_FTR",
        "parc_conservative_FTR",
        "empirical_audited_FTR",
        "conservative_label_uncertainty_FTR",
        "mass_ratio",
        "best_mass_ratio",
        "self_consistency_margin",
        "required_emax",
        "max_observed_e",
        "mean_observed_e",
        "selected_e_min",
        "selected_e_mean",
        "selected_e_max",
        "official_supported",
        "unsupported_actually_true",
        "unsupported_actually_false",
        "unsupported_uncertain",
        "unsupported_unlabeled",
        "release_feasible",
        "empty_reason",
        "safe_refusal_reason",
        "HOTA_or_proxy",
        "IDF1_or_proxy",
        "MOTA_or_proxy",
        "runtime_sec",
    }
    assert required_schema.issubset(main.columns)
    coverage = pd.read_csv(out_dir / "table_main_protocol_coverage.csv")
    assert {"included_main_table", "appendix_only_official_prediction_metadata_incomplete"}.issubset(
        set(coverage["main_protocol_status"])
    )
    baseline_coverage = pd.read_csv(out_dir / "table_baseline_protocol_coverage.csv")
    assert baseline_coverage["main_protocol_all_generator_dataset_grid"].eq(False).all()
    oracle = pd.read_csv(out_dir / "table_oracle_true_upper_bound_appendix.csv")
    assert {"oracle_status", "oracle_upper_bound_release_if_unknown_true"}.issubset(oracle.columns)
    summary = pd.read_csv(out_dir / "table_main_raw_vs_parc_summary.csv")
    assert {"nonempty_seeds", "safe_refusal_rate"}.issubset(summary.columns)
    refusal = pd.read_csv(out_dir / "table_safe_refusal_diagnostics.csv")
    assert not refusal.empty
    assert refusal["safe_refusal_reason"].fillna("").astype(str).str.len().gt(0).all()
    assert (
        refusal["mass_ratio"].notna()
        | refusal["empty_reason"].fillna("").astype(str).str.len().gt(0)
    ).all()
    frontier = pd.read_csv(out_dir / "figure_risk_utility_frontier.csv")
    assert {"PARC_certified_release_or_refusal", "raw_topM_count_reference_no_certificate"}.issubset(
        set(frontier["policy"])
    )
    assert (out_dir / "figure_3_risk_utility_frontier.csv").exists()
    assert (out_dir / "figure_3_risk_utility_frontier.pdf").exists()
    safe_mass = pd.read_csv(out_dir / "figure_safe_refusal_mass_ratio.csv")
    assert {"mass_ratio", "mass_ratio_threshold", "unconstrained_feasible"}.issubset(safe_mass.columns)
    safe_evidence = pd.read_csv(out_dir / "figure_safe_refusal_mass_evidence.csv")
    assert {"mass_ratio", "max_observed_e", "raw_topM_risk_available"}.issubset(safe_evidence.columns)
    assert (out_dir / "figure_safe_refusal_mass_ratio.pdf").exists()
    assert (out_dir / "figure_safe_refusal_mass_evidence.pdf").exists()
    assert not (out_dir / "figure_safe_refusal_raw_false_rate.csv").exists()
    assert (tmp_path / "docs/qualitative_release_gallery.md").exists()
    for folder in ("released_examples", "refusal_examples", "borderline_examples"):
        assert (tmp_path / "figures" / folder / "manifest.csv").exists()
    provenance = json.loads((out_dir / "table_main_raw_vs_parc.csv.provenance.json").read_text())
    assert provenance["paper_facing_table"] is True
    assert provenance["source_files"]
