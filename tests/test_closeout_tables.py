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


def _write_sources(root: Path) -> None:
    reliability = root / "outputs/milestones/reliability_fortress"
    lvvis = root / "outputs/milestones/lvvis_certification"
    reliability.mkdir(parents=True, exist_ok=True)
    lvvis.mkdir(parents=True, exist_ok=True)
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
    refusal = pd.read_csv(out_dir / "table_safe_refusal_diagnostics.csv")
    assert not refusal.empty
    assert refusal["safe_refusal_reason"].fillna("").astype(str).str.len().gt(0).all()
    assert (
        refusal["mass_ratio"].notna()
        | refusal["empty_reason"].fillna("").astype(str).str.len().gt(0)
    ).all()
    provenance = json.loads((out_dir / "table_main_raw_vs_parc.csv.provenance.json").read_text())
    assert provenance["paper_facing_table"] is True
    assert provenance["source_files"]
