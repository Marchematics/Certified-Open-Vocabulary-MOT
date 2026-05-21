from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "materials_label_discordance_preregistration"


def test_discordance_preregistration_files_exist_and_do_not_store_credentials() -> None:
    required = [
        "DATA_ACCESS_GO_NO_GO.md",
        "protocol_discordance_study.yaml",
        "table_source_access_inventory.csv",
        "table_matching_rules_preregistered.csv",
        "table_downstream_conclusion_flip_endpoints.csv",
        "table_go_no_go_gates.csv",
        "table_data_access_smoke.csv",
        "table_step0_access_go_status.csv",
        "table_minimal_discordance_probe.csv",
        "table_model_score_eligibility.csv",
        "table_downstream_ranking_metrics.csv",
        "table_downstream_ranking_flip_summary.csv",
        "table_discovered_count_delta.csv",
        "MATERIALS_LABEL_DISCORDANCE_EXPERIMENT_CLOSEOUT.md",
        "DISCORDANCE_STUDY_PREREGISTRATION.md",
        "MANIFEST_SHA256.txt",
    ]
    for name in required:
        path = MILESTONE / name
        assert path.exists(), name

    combined = "\n".join(path.read_text(encoding="utf-8") for path in MILESTONE.iterdir() if path.is_file())
    assert "MP_API_KEY" in combined
    assert "never_commit" in combined or "never stored" in combined
    credential_like = re.findall(r"(?i)(?:api[_-]?key|token|secret|credential)\s*[:=]\s*['\"]?([A-Za-z0-9_-]{16,})", combined)
    assert credential_like == []


def test_source_access_gate_requires_independent_sources_and_secret_policy() -> None:
    inventory = pd.read_csv(MILESTONE / "table_source_access_inventory.csv")

    assert {"Materials Project", "Alexandria", "OQMD", "Matbench Discovery / WBM"}.issubset(
        set(inventory["source"])
    )
    assert inventory["secret_policy"].astype(str).str.contains("public|do_not_commit", regex=True).all()

    hard = inventory[inventory["go_no_go_role"].isin(["hard_gate", "hard_context_gate"])]
    assert len(hard) >= 3
    mp = inventory[inventory["source"].eq("Materials Project")]
    assert len(mp) == 1
    assert "environment" in mp["access_requirement"].iloc[0]
    assert "hard_gate" == mp["go_no_go_role"].iloc[0]


def test_data_access_smoke_records_status_without_secret() -> None:
    smoke = pd.read_csv(MILESTONE / "table_data_access_smoke.csv")
    assert len(smoke) == 1
    row = smoke.iloc[0]
    assert row["source"] == "Materials Project"
    assert row["secret_written_to_artifact"] in {False, "false"}
    assert row["credential_env_present"] in {True, False, "true", "false"}
    assert row["status"] in {
        "pass",
        "blocked_missing_MP_API_KEY_env",
        "failed_empty_response",
        "failed_exception",
    }


def test_matching_rules_forbid_formula_only_headline_discordance() -> None:
    rules = pd.read_csv(MILESTONE / "table_matching_rules_preregistered.csv")

    primary = rules[rules["primary_or_sensitivity"].eq("primary")]
    assert not primary.empty
    assert primary["allowed_in_primary_discordance"].astype(bool).all()

    formula = rules[rules["rule_id"].eq("T1_formula_only_tag")]
    assert len(formula) == 1
    assert not bool(formula["allowed_in_primary_discordance"].iloc[0])
    assert formula["formula_only_allowed"].iloc[0] == "tag_only"


def test_go_no_go_endpoints_include_discordance_and_conclusion_flip_gates() -> None:
    endpoints = pd.read_csv(MILESTONE / "table_downstream_conclusion_flip_endpoints.csv")
    endpoint_ids = set(endpoints["endpoint_id"])

    assert "E1_pairwise_binary_discordance" in endpoint_ids
    assert "E3_model_ranking_flip" in endpoint_ids
    assert "E4_discovered_stable_count_delta" in endpoint_ids
    assert "E5_release_decision_flip_probe" in endpoint_ids

    e1 = endpoints[endpoints["endpoint_id"].eq("E1_pairwise_binary_discordance")].iloc[0]
    assert "discordance >= 0.40" in e1["pass_gate"]
    assert "discordance <= 0.10" in e1["no_go_gate"]
    assert "matched_n >= 200" in e1["pass_gate"]


def test_step0_access_status_is_go_but_not_headline_evidence() -> None:
    status = pd.read_csv(MILESTONE / "table_step0_access_go_status.csv")
    assert len(status) == 1
    row = status.iloc[0]
    assert row["materials_project_api_smoke"] == "pass"
    assert row["step0_minimal_go_no_go"] == "GO_for_freezing_exact_match_probe_inputs"
    assert "pass Step1 and Step2" in row["remaining_before_headline_claim"]


def test_preregistration_claim_boundaries_keep_parc_secondary() -> None:
    protocol = (MILESTONE / "protocol_discordance_study.yaml").read_text(encoding="utf-8")
    prereg = (MILESTONE / "DISCORDANCE_STUDY_PREREGISTRATION.md").read_text(encoding="utf-8")

    assert "parc_role: optional_release_refuse_probe_only" in protocol
    assert "primary_contribution: public_DFT_stability_label_reproducibility" in protocol
    assert "The primary contribution is not PARC" in prereg
    assert "Do not claim prospective materials discovery" in prereg


def test_minimal_experiment_passes_discordance_but_not_primary_ranking_gate() -> None:
    probe = pd.read_csv(MILESTONE / "table_minimal_discordance_probe.csv")
    assert len(probe) == 1
    row = probe.iloc[0]
    assert int(row["matched_n"]) >= 200
    assert float(row["discordance_rate"]) >= 0.40
    assert row["launch_gate_discordance_ge_0_40"] in {True, "true"}
    assert "not_final_MP_vs_alex" in row["paper_role"]

    flips = pd.read_csv(MILESTONE / "table_downstream_ranking_flip_summary.csv")
    primary = flips[flips["endpoint"].eq("primary_frontier_model_ranking")]
    assert len(primary) == 1
    assert primary["status"].iloc[0] == "run"
    assert primary["go_no_go"].iloc[0] == "NO_GO_primary_no_material_F1_ranking_flip"

    auxiliary = flips[flips["endpoint"].eq("auxiliary_available_public_prediction_ranking")]
    assert len(auxiliary) == 1
    assert auxiliary["status"].iloc[0] == "completed_auxiliary_diagnostic"


def test_primary_model_eligibility_requires_same_denominator_scores() -> None:
    eligibility = pd.read_csv(MILESTONE / "table_model_score_eligibility.csv")
    primary = eligibility[eligibility["pre_registered_role"].eq("primary_model_set")]
    assert set(primary["model"]) == {"ALIGNN-FF", "CHGNet", "MACE-MP"}
    eligible = set(primary[primary["eligible_primary_ranking"].astype(str).str.lower().eq("true")]["model"])
    assert eligible == {"ALIGNN-FF", "CHGNet", "MACE-MP"}
    assert (primary["valid_scores_on_exact_denominator"].astype(int) >= 200).all()
