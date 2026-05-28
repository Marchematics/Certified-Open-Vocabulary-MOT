from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE64 = ROOT / "outputs/milestones/ncs_phase64_parc_r_versioned_recertification"


def test_phase64_outputs_exist() -> None:
    expected = {
        "PARC_R_PREREGISTRATION.md",
        "table_parc_r_seed_rows.csv",
        "table_parc_r_primary_results.csv",
        "table_parc_r_gate_audit.csv",
        "table_parc_r_candidate_level_seed0.csv",
        "table_parc_r_refusal_diagnostics.csv",
        "figure_parc_r_versioned_recertification_inputs.csv",
        "NCS_PHASE64_PARC_R_VERSIONED_RECERTIFICATION.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE64 / name).exists()]


def test_phase64_primary_results_are_versioned_refusal_boundary() -> None:
    table = pd.read_csv(PHASE64 / "table_parc_r_primary_results.csv")
    assert len(table) == 4
    assert set(table["K"]) == {300, 500}
    assert set(table["rho_t1_positive_support"]) == {0.1, 1.0}
    assert table["nonempty_seeds"].eq(0).all()
    assert table["mean_release_size"].eq(0).all()
    assert table["recertification_status"].eq("versioned_refusal").all()
    assert table["claim_status"].eq("completed_versioned_recertification_refusal_boundary").all()
    assert table["old_t0_PARC_release_FTR_t1"].gt(0.10).all()
    assert table["evidence_scope"].str.contains("not_DFT_evidence").all()
    assert table["evidence_scope"].str.contains("not_prospective_discovery").all()


def test_phase64_gate_audit_forbids_positive_recertification_headline() -> None:
    gate = pd.read_csv(PHASE64 / "table_parc_r_gate_audit.csv")
    headline = gate[gate["gate"].eq("headline_positive_recertification_allowed")]
    assert len(headline) == 4
    assert headline["status"].eq("FAIL").all()

    refusal = gate[gate["gate"].eq("versioned_refusal_claim_allowed")]
    assert len(refusal) == 4
    assert refusal["status"].eq("PASS").all()

    nonempty = gate[gate["gate"].eq("t1_recertification_nonempty_ge_18_seeds")]
    assert nonempty["status"].eq("FAIL").all()


def test_phase64_candidate_table_has_split_and_no_release() -> None:
    table = pd.read_csv(PHASE64 / "table_parc_r_candidate_level_seed0.csv")
    required = {
        "candidate_id",
        "K",
        "raw_score",
        "t0_label",
        "t1_label",
        "partition",
        "observed_t1_positive_for_recertification",
        "recert_evalue",
        "recertified_release",
        "recertification_decision",
        "evidence_scope",
    }
    assert required.issubset(table.columns)
    assert set(table["partition"]) == {"calibration", "followup"}
    assert not table["recertified_release"].astype(bool).any()
    assert table["observed_t1_positive_for_recertification"].astype(bool).any()
    assert table["evidence_scope"].str.contains("not_full_WBM_recertification").all()


def test_phase64_closeout_and_ledger_guardrails() -> None:
    closeout = (PHASE64 / "NCS_PHASE64_PARC_R_VERSIONED_RECERTIFICATION.md").read_text(encoding="utf-8")
    for phrase in [
        "Headline positive PARC-R allowed: `false`",
        "no prospective materials discovery",
        "no DFT evidence",
        "no t1 alpha certificate for the old t0 release",
        "no claim that PARC-R creates a nonempty current-MP materials release",
    ]:
        assert phrase in closeout

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("M-PARCR-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "partial"
    assert "refusal_not_nonempty_release" in row.iloc[0]["scope"]
    assert "do_not_claim_nonempty_t1_alpha_release" in row.iloc[0]["overclaim_guardrail"]


def test_phase64_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase64-parc-r-versioned-recertification"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase64_parc_r_versioned_recertification" in result.stdout
