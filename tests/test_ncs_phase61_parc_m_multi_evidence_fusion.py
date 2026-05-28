from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE61 = ROOT / "outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion"


def test_phase61_outputs_exist() -> None:
    expected = {
        "PARC_M_PREREGISTRATION.md",
        "table_parc_m_primary_results.csv",
        "table_parc_m_candidate_level.csv",
        "table_parc_m_gate_audit.csv",
        "table_parc_m_source_evalue_audit.csv",
        "figure_parc_m_fusion_inputs.csv",
        "NCS_PHASE61_PARC_M_MULTI_EVIDENCE_FUSION.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE61 / name).exists()]


def test_phase61_primary_results_have_medium_signal_but_no_headline() -> None:
    table = pd.read_csv(PHASE61 / "table_parc_m_primary_results.csv")
    for k in [300, 500]:
        subset = table[table["K"].eq(k)].set_index("method")
        parc = subset.loc["PARC original release"]
        best = subset[subset.index.str.startswith("PARC-M-")].sort_values("t1_FTR").iloc[0]
        assert best["release_size"] >= 100
        assert best["t1_FTR"] < parc["t1_FTR"]
        assert best["t1_original_PARC_minus_method"] >= 0.03
        assert best["t1_original_PARC_minus_method"] < 0.05
        assert "proxy_fusion_not_theorem_grade" in best["theorem_grade_status"]
        assert "not_DFT_evidence" in best["evidence_scope"]
        assert "not_prospective_discovery" in best["evidence_scope"]


def test_phase61_gate_audit_marks_medium_not_strong_and_blocks_headline() -> None:
    gate = pd.read_csv(PHASE61 / "table_parc_m_gate_audit.csv")
    for k in [300, 500]:
        subset = gate[gate["K"].eq(k)].set_index("gate")
        assert subset.loc["PARC_M_best_empirical_t1_improvement_ge_0p03", "status"] == "PASS"
        assert subset.loc["PARC_M_best_empirical_t1_improvement_ge_0p05", "status"] == "FAIL"
        assert subset.loc["PARC_M_best_release_size_ge_100", "status"] == "PASS"
        assert subset.loc["theorem_grade_all_evalue_sources_available", "status"] == "FAIL"
        assert subset.loc["PARC_M_headline_claim_allowed", "status"] == "FAIL"


def test_phase61_source_audit_requires_full_null_calibration_for_theorem() -> None:
    audit = pd.read_csv(PHASE61 / "table_parc_m_source_evalue_audit.csv")
    assert set(audit["source"]) == {
        "original_PARC_evalue",
        "ALIGNN_rank_proxy",
        "CHGNet_rank_proxy",
        "MACE_rank_proxy",
    }
    proxy_rows = audit[audit["source"].str.contains("proxy")]
    assert proxy_rows["theorem_grade_status"].eq("not_theorem_grade").all()
    assert proxy_rows["blocking_issue"].str.contains("null|calibration|queue", case=False, regex=True).all()


def test_phase61_closeout_forbids_overclaims() -> None:
    text = (PHASE61 / "NCS_PHASE61_PARC_M_MULTI_EVIDENCE_FUSION.md").read_text(encoding="utf-8")
    for phrase in [
        "no theorem-grade multi-evidence e-value certificate",
        "no t1 alpha control",
        "no DFT evidence",
        "no prospective materials discovery",
    ]:
        assert phrase in text
    assert "empirical_medium_signal_not_claim_ready" in text


def test_phase61_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase61-parc-m-multi-evidence-fusion"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "wrote outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion" in result.stdout
