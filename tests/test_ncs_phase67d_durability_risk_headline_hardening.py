from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase67d_durability_risk_headline_hardening"


def test_phase67d_outputs_and_guardrails_exist() -> None:
    required = [
        "README_evidence_scope.md",
        "HEADLINE_DISPLAY_GUIDANCE.md",
        "table_headline_pruned_model_summary.csv",
        "table_headline_pruned_bootstrap_ci.csv",
        "table_headline_pruned_calibration.csv",
        "table_base_rate_baseline_by_fold.csv",
        "table_base_rate_and_memorization_controls.csv",
        "table_extended_data_ablation_role.csv",
        "figure_durability_risk_headline_inputs.csv",
        "MANIFEST_SHA256.txt",
    ]
    for name in required:
        assert (OUT / name).exists(), name

    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "headline pruned model",
        "chemical-system bootstrap confidence intervals",
        "calibration table",
        "train-fold base-rate baseline",
        "not a release certificate",
        "not DFT evidence",
        "not prospective materials discovery",
        "not a label-free deployment predictor",
    ]:
        assert phrase in readme


def test_phase67d_headline_model_is_pruned_and_strong() -> None:
    summary = pd.read_csv(OUT / "table_headline_pruned_model_summary.csv").iloc[0]
    assert summary["feature_set"] == "headline_pruned_margin_distribution_plus_size_activity"
    assert summary["roc_auc"] >= 0.80
    assert summary["top30_retained_flip_rate"] < summary["base_flip_rate"]
    assert summary["top30_fraction_flips_flagged"] >= 0.50
    assert "not_release_certificate" in summary["evidence_scope"]


def test_phase67d_bootstrap_ci_and_calibration_are_reported() -> None:
    ci = pd.read_csv(OUT / "table_headline_pruned_bootstrap_ci.csv")
    assert {"roc_auc", "top30_retained_flip_rate", "top30_fraction_flips_flagged"} <= set(ci["metric"])
    auc = ci[ci["metric"].eq("roc_auc")].iloc[0]
    assert auc["bootstrap_unit"] == "chemical_system"
    assert int(auc["n_bootstrap"]) >= 1000
    assert auc["ci_low_95"] < auc["estimate"] < auc["ci_high_95"]

    cal = pd.read_csv(OUT / "table_headline_pruned_calibration.csv")
    assert len(cal) >= 5
    assert cal["predicted_mean"].between(0, 1).all()
    assert cal["observed_flip_rate"].between(0, 1).all()
    assert cal["weighted_absolute_calibration_error"].ge(0).all()


def test_phase67d_base_rate_and_memorization_controls() -> None:
    controls = pd.read_csv(OUT / "table_base_rate_and_memorization_controls.csv").iloc[0]
    assert controls["comparison"] == "headline_pruned_vs_train_fold_base_rate"
    assert controls["passes"] in [True, "True"]
    assert controls["delta_roc_auc"] >= 0.10
    assert int(controls["baseline_system_overlap"]) == 0

    base = pd.read_csv(OUT / "table_base_rate_baseline_by_fold.csv")
    assert base["train_test_system_overlap"].eq(0).all()
    assert base["test_system_lookup_coverage"].eq(0.0).all()
    assert base["interpretation"].str.contains("cannot memorize held-out chemical systems").all()


def test_phase67d_near_hull_density_is_extended_data_negative_ablation() -> None:
    role = pd.read_csv(OUT / "table_extended_data_ablation_role.csv")
    near = role[role["feature_set"].eq("system_near_hull_density")].iloc[0]
    assert near["main_display_role"] == "extended_data_negative_ablation"
    assert near["mean_roc_auc"] < 0.60
    margin = role[role["feature_set"].eq("system_margin_distribution")].iloc[0]
    assert margin["main_display_role"] == "component_of_headline_or_mechanism_support"


def test_phase67d_ledger_and_reproduce_target() -> None:
    ledger = pd.read_csv(
        ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    )
    row = ledger[ledger["claim_id"].eq("DUR-RISK-HARDEN-001")]
    assert len(row) == 1
    assert "not_release_certificate" in row.iloc[0]["scope"]

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "reproduce-ncs-phase67d-durability-risk-headline-hardening" in makefile


def test_phase67d_public_bundle_validation() -> None:
    subprocess.run(
        [
            "python",
            "scripts/validate_public_bundle.py",
            "outputs/milestones/ncs_phase67d_durability_risk_headline_hardening",
        ],
        cwd=ROOT,
        check=True,
    )
