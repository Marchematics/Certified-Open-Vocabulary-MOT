from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE67C = ROOT / "outputs/milestones/ncs_phase67c_durability_risk_prediction"
FEATURE_SETS = {
    "candidate_margin_only",
    "candidate_t0_score_only",
    "chemical_system_exploration_only",
    "candidate_plus_system",
}


def test_phase67c_outputs_expected_feature_sets_without_t1_feature_leakage() -> None:
    summary = pd.read_csv(PHASE67C / "table_durability_risk_prediction_model_comparison.csv")
    metrics = pd.read_csv(PHASE67C / "table_durability_risk_cv_fold_metrics.csv")
    provenance = pd.read_csv(PHASE67C / "table_durability_risk_feature_provenance.csv")
    assert set(summary["feature_set"]) == FEATURE_SETS
    assert set(metrics["feature_set"]) == FEATURE_SETS
    forbidden = ["t1", "drift", "stable_to_unstable", "failure", "label"]
    feature_blob = ";".join(summary["feature_names"].astype(str).tolist()).lower()
    for token in forbidden:
        assert token not in feature_blob
    assert provenance["leakage_status"].str.contains("PASS_no_t1_or_post_update_information").all()
    assert not provenance["source_columns"].str.contains("t1|drift|stable_to_unstable", case=False, regex=True).any()
    assert summary["cv_scheme"].eq("GroupKFold_by_chemical_system").all()


def test_phase67c_population_and_predictions_are_scoped() -> None:
    population = pd.read_csv(PHASE67C / "table_durability_risk_population.csv")
    predictions = pd.read_csv(PHASE67C / "table_durability_risk_group_cv_predictions.csv")
    assert int(population.iloc[0]["n_rows"]) == len(predictions[predictions["feature_set"].eq("candidate_margin_only")])
    assert population.iloc[0]["population"] == "t0_stable_PARCrelease_K300_K500_rows"
    assert 0 < float(population.iloc[0]["positive_rate"]) < 1
    assert predictions["evidence_scope"].str.contains("not_release_certificate").all()
    assert predictions["evidence_scope"].str.contains("not_DFT_evidence").all()
    assert predictions["predicted_durability_failure_risk"].between(0, 1).all()


def test_phase67c_primary_signal_requires_system_model_to_beat_margin() -> None:
    summary = pd.read_csv(PHASE67C / "table_durability_risk_prediction_model_comparison.csv")
    margin = summary.loc[summary["feature_set"].eq("candidate_margin_only")].iloc[0]
    system = summary.loc[summary["feature_set"].eq("chemical_system_exploration_only")].iloc[0]
    positives = summary[summary["primary_prediction_signal"].astype(bool)]
    for _, row in positives.iterrows():
        assert row["feature_set"] == "chemical_system_exploration_only"
        assert row["mean_roc_auc"] >= 0.60
        assert row["delta_auc_vs_candidate_margin"] >= 0.03
        assert row["top20_enrichment_vs_base"] >= 1.25
    assert system["mean_roc_auc"] > margin["mean_roc_auc"]


def test_phase67c_ablation_and_by_k_robustness_tables_exist() -> None:
    ablation = pd.read_csv(PHASE67C / "table_durability_risk_ablation_model_comparison.csv")
    by_k = pd.read_csv(PHASE67C / "table_durability_risk_by_k_model_comparison.csv")
    assert {
        "system_size_activity_proxy",
        "system_near_hull_density",
        "system_margin_distribution",
        "system_raw_score_context",
    } == set(ablation["feature_set"])
    assert {300, 500} == set(by_k["K"])
    system_by_k = by_k[by_k["feature_set"].eq("chemical_system_exploration_only")]
    assert system_by_k["mean_roc_auc"].gt(0.60).all()
    margin_by_k = by_k[by_k["feature_set"].eq("candidate_margin_only")]
    assert (system_by_k["mean_roc_auc"].to_numpy() > margin_by_k["mean_roc_auc"].to_numpy()).all()


def test_phase67c_readme_forbids_overclaiming() -> None:
    text = (PHASE67C / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "no release certificate",
        "no prospective materials discovery",
        "no DFT evidence",
        "no t1 features used as predictors",
        "t0-public-label-dependent system features",
    ]:
        assert phrase in text


def test_phase67c_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase67c-durability-risk-prediction"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase67c_durability_risk_prediction" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase67c_durability_risk_prediction"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
