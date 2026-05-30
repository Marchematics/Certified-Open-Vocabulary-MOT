from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase79_controlled_evolving_reference_simulation"


def test_phase79_outputs_exist_and_scope_guardrails() -> None:
    expected = {
        "CONTROLLED_EVOLVING_REFERENCE_PREREGISTRATION.md",
        "table_controlled_simulation_synthetic_row_sample.csv",
        "table_controlled_simulation_fold_metrics.csv",
        "table_controlled_simulation_prediction_sample.csv",
        "table_controlled_simulation_model_comparison.csv",
        "table_controlled_simulation_regime_summary.csv",
        "table_controlled_simulation_toprisk_enrichment.csv",
        "table_controlled_simulation_go_no_go.csv",
        "table_controlled_simulation_feature_provenance.csv",
        "table_controlled_simulation_materials_mapping.csv",
        "figure_controlled_simulation_auc_inputs.csv",
        "figure_controlled_simulation_toprisk_inputs.csv",
        "README_evidence_scope.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "controlled evolving-reference simulation",
        "not a new empirical domain",
        "not a release certificate",
        "not DFT evidence",
        "not prospective materials",
        "do not claim all evolving-reference systems are neighborhood-driven",
    ]:
        assert phrase in readme


def test_phase79_feature_provenance_has_no_post_update_leakage() -> None:
    provenance = pd.read_csv(OUT / "table_controlled_simulation_feature_provenance.csv")
    assert not provenance["uses_post_update_label"].astype(bool).any()
    assert provenance["leakage_status"].eq("PASS_pre_update_only").all()
    forbidden = "post_update|flip|label|future|t1"
    assert not provenance["feature"].str.contains(forbidden, case=False, regex=True).any()


def test_phase79_recovers_both_mechanism_signatures() -> None:
    summary = pd.read_csv(OUT / "table_controlled_simulation_model_comparison.csv")
    pivot = summary.pivot(index="regime", columns="feature_set", values="mean_roc_auc")

    candidate_driven_candidate = pivot.loc["candidate_driven", "candidate_margin_rank"]
    candidate_driven_system = pivot.loc["candidate_driven", "system_landscape_activity"]
    neighborhood_candidate = pivot.loc["neighborhood_driven", "candidate_margin_rank"]
    neighborhood_system = pivot.loc["neighborhood_driven", "system_landscape_activity"]
    noise_neighborhood = pivot.loc["neighborhood_driven", "negative_control_noise"]

    assert candidate_driven_candidate >= 0.70
    assert candidate_driven_candidate - candidate_driven_system >= 0.10
    assert neighborhood_system >= 0.70
    assert neighborhood_candidate <= 0.60
    assert neighborhood_system - neighborhood_candidate >= 0.15
    assert noise_neighborhood < neighborhood_system


def test_phase79_go_no_go_supports_breadth_with_explicit_conditions() -> None:
    gates = pd.read_csv(OUT / "table_controlled_simulation_go_no_go.csv")
    assert {"candidate_driven_signature", "neighborhood_driven_signature", "phase_b_breadth_support"} == set(gates["gate"])
    assert gates["pass"].astype(bool).all()
    breadth = gates[gates["gate"].eq("phase_b_breadth_support")].iloc[0]
    assert "controlled simulation supports" in breadth["interpretation"]
    assert gates["evidence_scope"].str.contains("not_release_certificate").all()
    assert gates["evidence_scope"].str.contains("not_DFT_evidence").all()


def test_phase79_group_split_and_predictions_are_valid() -> None:
    folds = pd.read_csv(OUT / "table_controlled_simulation_fold_metrics.csv")
    predictions = pd.read_csv(OUT / "table_controlled_simulation_prediction_sample.csv")
    assert folds["group_split"].eq("GroupKFold_by_system_id").all()
    assert folds["test_systems"].gt(0).all()
    assert predictions["predicted_flip_risk"].between(0, 1).all()
    assert predictions["evidence_scope"].str.contains("synthetic_mechanism_demonstration").all()
    assert set(predictions["post_update_flip"]).issubset({0, 1})


def test_phase79_materials_mapping_keeps_scope_clear() -> None:
    mapping = pd.read_csv(OUT / "table_controlled_simulation_materials_mapping.csv")
    assert mapping["guardrail"].str.contains("synthetic mechanism demonstration", case=False, regex=False).any()
    assert mapping["paper_use"].str.contains("breadth-supporting mechanism", case=False, regex=False).any()
    prereg = (OUT / "CONTROLLED_EVOLVING_REFERENCE_PREREGISTRATION.md").read_text(encoding="utf-8")
    assert "GO requires both" in prereg
    assert "not a new empirical domain" in prereg


def test_phase79_ledger_and_reproduce_target() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("SIM-BREADTH-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "yes"
    assert "do_not_claim_external_domain" in row.iloc[0]["overclaim_guardrail"]

    result = subprocess.run(
        ["make", "reproduce-ncs-phase79-controlled-evolving-reference-simulation"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "completed_controlled_generality_simulation" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase79_controlled_evolving_reference_simulation"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
