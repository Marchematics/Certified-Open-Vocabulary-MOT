from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "b_phase93_wbm_versioned_claim_decay_pilot"


def test_phase93_b_outputs_exist_and_scope_is_public_reference_only() -> None:
    expected = {
        "PHASE93_WBM_VERSIONED_CLAIM_DECAY_PROTOCOL.md",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
        "figure_phase93_wbm_versioned_claim_decay_inputs.csv",
        "table_phase93_claim_gate.csv",
        "table_phase93_wbm_decay_by_chemical_system.csv",
        "table_phase93_wbm_versioned_claim_decay_rows.csv",
        "table_phase93_wbm_versioned_claim_decay_summary.csv",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "public_versioned_reference_decay_pilot_completed_not_independent_DFT" in readme
    assert "versioned public-label" in readme
    assert "drift only" in readme


def test_phase93_b_wbm_rows_join_and_report_drift_without_dft_claim() -> None:
    rows = pd.read_csv(OUT / "table_phase93_wbm_versioned_claim_decay_rows.csv")
    assert len(rows) == 150
    assert rows["material_id"].notna().all()
    assert rows["formula"].notna().all()
    assert rows["stable_exact_t0"].astype(bool).all()
    assert rows["evidence_scope"].str.contains("not_independent_DFT").all()
    assert rows["claim_decay_status"].isin(
        {
            "retained_current_reference_stable",
            "decayed_to_current_reference_unstable",
            "unresolved_current_reference_label",
            "other_or_unresolved",
        }
    ).all()


def test_phase93_b_summary_and_gate_are_pilot_not_independent_validation() -> None:
    summary = pd.read_csv(OUT / "table_phase93_wbm_versioned_claim_decay_summary.csv").iloc[0]
    assert int(summary["registry_rows"]) == 150
    assert int(summary["joined_to_t0_t1_rows"]) == 150
    assert int(summary["decayed_to_current_reference_unstable"]) > 0
    assert 0 <= float(summary["decay_fraction_labelable"]) <= 1

    gate = pd.read_csv(OUT / "table_phase93_claim_gate.csv").iloc[0]
    assert gate["positive_evidence"] == "weak_public_reference_pilot_only"
    assert "independent DFT validation" in gate["forbidden_current_claim"]
    assert "A-paper main evidence" in gate["forbidden_current_claim"]


def test_phase93_b_ledger_claim_table_reproduce_and_public_bundle() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("B-PHASE93-WBM-VERSIONED-CLAIM-DECAY-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "weak_smoke_only"
    assert "do_not_claim_independent_DFT" in row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase93 B-Line WBM Versioned Claim-Decay Pilot" in claim_table
    assert "not independent DFT validation" in claim_table

    result = subprocess.run(
        ["make", "reproduce-b-phase93-wbm-versioned-claim-decay-pilot"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "public_versioned_reference_decay_pilot_completed_not_independent_DFT" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/b_phase93_wbm_versioned_claim_decay_pilot"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
