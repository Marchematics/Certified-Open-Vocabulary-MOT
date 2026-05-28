from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE60 = ROOT / "outputs/milestones/ncs_phase60_parc_v_version_aware_release"


def test_phase60_outputs_exist() -> None:
    expected = {
        "PARC_V_PREREGISTRATION.md",
        "table_parc_v_candidate_level.csv",
        "table_parc_v_primary_results.csv",
        "table_parc_v_baseline_comparison.csv",
        "table_parc_v_gate_audit.csv",
        "figure_parc_v_version_aware_release_inputs.csv",
        "NCS_PHASE60_PARC_V_VERSION_AWARE_RELEASE.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE60 / name).exists()]


def test_phase60_candidate_table_has_support_gate_and_boundaries() -> None:
    table = pd.read_csv(PHASE60 / "table_parc_v_candidate_level.csv")
    required = {
        "candidate_id",
        "structure_hash",
        "formula",
        "chemical_system",
        "K",
        "parc_released",
        "t0_label",
        "t1_label",
        "chgnet_predicted_ehull_or_score",
        "mace_predicted_ehull_or_score",
        "chgnet_mace_consensus_label",
        "support_rank_mean",
        "parc_v_consensus_eligible",
        "parc_v_top_050pct_support_eligible",
        "evidence_scope",
    }
    assert required.issubset(table.columns)
    assert set(table["K"]) == {300, 500}
    assert table["evidence_scope"].str.contains("not_full_SCS_rerun").all()
    assert table["evidence_scope"].str.contains("not_DFT_evidence").all()
    assert table["evidence_scope"].str.contains("not_prospective_discovery").all()


def test_phase60_primary_results_show_no_headline_parc_v_pass() -> None:
    table = pd.read_csv(PHASE60 / "table_parc_v_primary_results.csv")
    for k in [300, 500]:
        subset = table[table["K"].eq(k)].set_index("method")
        parc = subset.loc["PARC"]
        parc_v = subset.loc["PARC-V consensus gate"]
        raw = subset.loc["raw top-K"]
        assert parc_v["release_size"] > 25
        assert parc_v["release_size"] < parc["release_size"]
        assert parc_v["t1_FTR"] < raw["t1_FTR"]
        assert parc_v["t1_FTR"] > 0.15
        assert parc_v["t1_original_PARC_minus_method"] < 0.05
        assert "not_full_SCS_rerun" in parc_v["evidence_scope"]


def test_phase60_gate_audit_blocks_positive_headline() -> None:
    gate = pd.read_csv(PHASE60 / "table_parc_v_gate_audit.csv")
    for k in [300, 500]:
        subset = gate[gate["K"].eq(k)].set_index("gate")
        assert subset.loc["parc_v_consensus_nonempty", "status"] == "PASS"
        assert subset.loc["parc_v_consensus_t1_FTR_le_0p15", "status"] == "FAIL"
        assert subset.loc["parc_v_consensus_t1_FTR_le_alpha", "status"] == "FAIL"
        assert subset.loc["parc_v_consensus_improves_original_PARC_by_0p05", "status"] == "FAIL"
        assert subset.loc["full_theorem_grade_PARC_V_claim_allowed", "status"] == "FAIL"


def test_phase60_closeout_forbids_overclaims() -> None:
    text = (PHASE60 / "NCS_PHASE60_PARC_V_VERSION_AWARE_RELEASE.md").read_text(encoding="utf-8")
    forbidden_phrases = [
        "no new theorem-grade PARC-V certificate",
        "no t1 alpha control",
        "no DFT evidence",
        "no prospective materials discovery",
    ]
    for phrase in forbidden_phrases:
        assert phrase in text
    assert "no_go_for_headline" in text


def test_phase60_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase60-parc-v-version-aware-release"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "wrote outputs/milestones/ncs_phase60_parc_v_version_aware_release" in result.stdout
