from __future__ import annotations

from pathlib import Path

import pandas as pd

from parc_track import phase18
from parc_track.phase18 import run_phase18_statistical_scaleup


def _patch_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PARC_TRACK_EXTRA_OUTPUT_ROOTS", str(tmp_path))
    monkeypatch.setattr(phase18, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(phase18, "RELIABILITY_DIR", tmp_path / "outputs/milestones/reliability_fortress")
    monkeypatch.setattr(phase18, "GENERALITY_DIR", tmp_path / "outputs/milestones/generality_reliability")
    monkeypatch.setattr(phase18, "PAPER_TABLE_DIR", tmp_path / "outputs/milestones/reliability_fortress/paper_tables")
    monkeypatch.setattr(phase18, "SCALEUP_DIR", tmp_path / "outputs/milestones/reliability_fortress/statistical_scaleup")


def _write_inputs(tmp_path: Path) -> None:
    paper = tmp_path / "outputs/milestones/reliability_fortress/paper_tables"
    gen = tmp_path / "outputs/milestones/generality_reliability/paper_tables"
    paper.mkdir(parents=True, exist_ok=True)
    gen.mkdir(parents=True, exist_ok=True)
    rows = []
    for seed in range(3):
        rows.append(
            {
                "dataset": "OVT-B",
                "generator": "GroundingDINO",
                "certified_risk_level_alpha": 0.1,
                "M": 150,
                "seed": seed,
                "raw_topM_released": 150,
                "raw_topM_audited_false_rate": 0.12,
                "raw_topM_unsupported_rate": 0.2,
                "parc_released": 120 + seed,
                "empirical_audited_FTR": 0.0,
                "conservative_label_uncertainty_FTR": 0.01,
                "mass_ratio": 1.5,
                "HOTA_or_proxy": 0.1,
            }
        )
    pd.DataFrame(rows).to_csv(paper / "table_main_raw_vs_parc.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "OVT-B",
                "generator": "GroundingDINO",
                "baseline": "Split conformal p-value threshold",
                "certified_risk_level_alpha": 0.1,
                "M": 150,
                "seed": 0,
                "released": 100,
                "empirical_audited_FTR": 0.0,
                "conservative_FTR": 0.02,
                "mass_ratio": 1.0,
            }
        ]
    ).to_csv(paper / "table_baseline_comparison.csv", index=False)
    pd.DataFrame(
        [
            {
                "dataset": "LVIS",
                "detector": "GroundingDINO",
                "policy": "PARC certified release",
                "certified_risk_target_alpha": 0.1,
                "seed": seed,
                "M": 150,
                "released": 150,
                "empirical_audited_false_rate": "",
                "conservative_unknown_as_false_rate": 0.0,
                "mass_ratio": 1.2,
            }
            for seed in range(3)
        ]
    ).to_csv(gen / "table_lvis_detection_main.csv", index=False)


def test_phase18_statistical_scaleup_tables(tmp_path: Path, monkeypatch) -> None:
    _patch_roots(tmp_path, monkeypatch)
    _write_inputs(tmp_path)

    summary = run_phase18_statistical_scaleup()
    assert summary["status"] == "completed"

    out = tmp_path / "outputs/milestones/reliability_fortress/statistical_scaleup"
    protocol = pd.read_csv(out / "table_statistical_scaleup_protocol.csv")
    assert "30+ seeds" in " ".join(protocol["target"].astype(str))

    coverage = pd.read_csv(out / "table_seed_coverage.csv")
    assert coverage["target_seed_count"].max() >= 30
    assert "scientific_domain_dataset" in set(coverage["dataset"])
    assert "needs_30_seed_rerun" in set(coverage["status"])

    ci = pd.read_csv(out / "table_main_bootstrap_ci.csv")
    assert {"ci_low_95", "ci_high_95", "seed_count", "ci_status"}.issubset(ci.columns)
    assert "current_completed_ci_not_30seed_final" in set(ci["ci_status"])

    datasets = pd.read_csv(out / "table_dataset_scope_journal.csv")
    sci = datasets[datasets["dataset"].eq("scientific_domain_dataset")]
    assert not sci.empty
    assert sci["current_status"].iloc[0] == "missing"

    baselines = pd.read_csv(out / "table_baseline_family_mapping.csv")
    families = set(baselines["baseline_family"])
    assert "conformal_risk_control_crc" in families
    assert "e_bh_and_e_value_family" in families

