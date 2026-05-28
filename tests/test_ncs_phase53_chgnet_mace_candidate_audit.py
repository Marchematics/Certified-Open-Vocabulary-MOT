from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE53 = ROOT / "outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit"


def test_phase53_outputs_exist() -> None:
    expected = {
        "table_materials_candidate_level_chgnet_mace_audit.csv",
        "table_chgnet_mace_support_by_policy.csv",
        "table_chgnet_mace_disagreement_by_t1_status.csv",
        "figure_chgnet_mace_release_vs_tail_inputs.csv",
        "table_chgnet_mace_raw_scores.csv",
        "table_phase53_go_no_go.csv",
        "NCS_PHASE53_CHGNET_MACE_CANDIDATE_AUDIT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in expected if not (PHASE53 / name).exists()]
    assert not missing


def test_candidate_level_table_has_required_fields_and_score_boundaries() -> None:
    table = pd.read_csv(PHASE53 / "table_materials_candidate_level_chgnet_mace_audit.csv")
    required = {
        "candidate_id",
        "structure_hash",
        "formula",
        "chemical_system",
        "policy_status",
        "K",
        "t0_label",
        "t1_label",
        "t1_drift_type",
        "chgnet_predicted_ehull_or_score",
        "mace_predicted_ehull_or_score",
        "chgnet_label",
        "mace_label",
        "chgnet_mace_consensus_label",
        "chgnet_mace_disagreement",
        "near_hull_t1_25mev",
        "near_hull_t1_50mev",
        "failure_explanation_class",
        "evidence_scope",
    }
    assert required.issubset(table.columns)
    assert set(table["K"]) == {300, 500}
    assert table["candidate_id"].nunique() == 1191
    assert table["chgnet_predicted_ehull_or_score"].notna().all()
    assert table["mace_predicted_ehull_or_score"].notna().all()
    assert table["evidence_scope"].str.contains("score_support_proxy_not_reference_hull_ehull").all()
    assert table["evidence_scope"].str.contains("not_prospective_discovery").all()


def test_raw_score_cache_is_complete_and_public_safe() -> None:
    scores = pd.read_csv(PHASE53 / "table_chgnet_mace_raw_scores.csv")
    assert len(scores) == 1191
    assert scores["candidate_id"].is_unique
    assert scores["chgnet_score_status"].eq("scored").all()
    assert scores["mace_score_status"].eq("scored").all()
    assert scores["structure_source"].eq("local_private_WBM_raw_structure_cache_not_distributed").all()
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in PHASE53.glob("*") if path.is_file())
    assert "/home/waas" not in text
    assert "/root" not in text
    assert "MP_API_KEY" not in text


def test_policy_support_contrast_and_matched_volume_boundary() -> None:
    support = pd.read_csv(PHASE53 / "table_chgnet_mace_support_by_policy.csv")
    expected_groups = {"PARC release", "raw top-K", "matched raw top-R", "raw-only extra-tail"}
    for k in [300, 500]:
        subset = support[support["K"].eq(k)]
        assert set(subset["policy_group"]) == expected_groups
        by_group = subset.set_index("policy_group")
        release = by_group.loc["PARC release", "chgnet_mace_consensus_stable_fraction_proxy"]
        tail = by_group.loc["raw-only extra-tail", "chgnet_mace_consensus_stable_fraction_proxy"]
        assert release > tail
        assert by_group.loc["PARC release", "n_candidates"] == by_group.loc["matched raw top-R", "n_candidates"]
        assert (
            by_group.loc["PARC release", "chgnet_mace_consensus_stable_fraction_proxy"]
            == by_group.loc["matched raw top-R", "chgnet_mace_consensus_stable_fraction_proxy"]
        )
    assert support["evidence_scope"].str.contains("not_DFT_evidence").all()


def test_go_no_go_keeps_false_case_mechanism_as_diagnostic() -> None:
    go = pd.read_csv(PHASE53 / "table_phase53_go_no_go.csv")
    assert not go["status"].eq("FAIL").any()
    support_gate = go[go["gate"].eq("PARC_release_consensus_support_exceeds_extra_tail")]
    assert set(support_gate["status"]) == {"PASS"}
    mechanism_gate = go[go["gate"].eq("t1_false_cases_boundary_or_model_disagreement")]
    assert set(mechanism_gate["status"]) == {"DIAGNOSTIC_WEAK"}
    assert mechanism_gate["claim_boundary"].str.contains("not_alpha_certificate").all()


def test_phase53_reproduce_target_runs_from_cache() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase53-chgnet-mace-candidate-audit"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "wrote outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit" in result.stdout
