from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "b_phase91_gnome_mp_formula_prefilter"


def test_phase91_b_outputs_exist_and_scope_is_prefilter_only() -> None:
    expected = {
        "PHASE91_GNOME_MP_FORMULA_PREFILTER_PROTOCOL.md",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
        "table_phase91_claim_gate.csv",
        "table_phase91_gnome_mp_formula_prefilter.csv",
        "table_phase91_mp_formula_prefilter_candidates.csv",
        "table_phase91_mp_formula_prefilter_summary.csv",
        "table_phase91_next_match_steps.csv",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "mp_formula_prefilter_completed_exact_matching_pending" in readme
    assert "does not claim decay" in readme


def test_phase91_b_prefilter_rows_do_not_report_stability_verdicts() -> None:
    rows = pd.read_csv(OUT / "table_phase91_gnome_mp_formula_prefilter.csv")
    candidates = pd.read_csv(OUT / "table_phase91_mp_formula_prefilter_candidates.csv")
    assert len(rows) == 150
    assert rows["formula_prefilter_complete"].astype(bool).all()
    assert not rows["structure_matching_completed"].astype(bool).any()
    assert not rows["current_stability_verdict_reported"].astype(bool).any()
    assert not rows["claim_decay_evidence"].astype(bool).any()
    assert rows["evidence_scope"].str.contains("current_stability_verdicts_not_reported").all()
    forbidden = {"energy_above_hull", "is_stable", "formation_energy_per_atom"}
    assert forbidden.isdisjoint(candidates.columns)
    assert candidates["formula_prefilter_only"].astype(bool).all()
    assert not candidates["structure_matching_completed"].astype(bool).any()
    assert not candidates["current_stability_verdict_reported"].astype(bool).any()


def test_phase91_b_summary_and_gate_are_no_claim_decay() -> None:
    summary = pd.read_csv(OUT / "table_phase91_mp_formula_prefilter_summary.csv").iloc[0]
    assert int(summary["gnome_rows"]) == 150
    assert int(summary["total_mp_candidate_records"]) >= 0
    assert not bool(summary["structure_matching_completed"])
    assert not bool(summary["current_stability_verdicts_reported"])
    assert summary["claim_status"] == "mp_formula_prefilter_completed_exact_matching_pending"

    gate = pd.read_csv(OUT / "table_phase91_claim_gate.csv").iloc[0]
    assert gate["positive_evidence"] == "no"
    assert "Do not claim exact structure matching" in gate["forbidden_current_claim"]


def test_phase91_b_ledger_claim_table_and_reproduce() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("B-PHASE91-GNOME-MP-FORMULA-PREFILTER-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_exact_structure_matching" in row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase91 B-Line GNoME MP Formula Prefilter" in claim_table
    assert "not source-level claim-decay evidence" in claim_table

    result = subprocess.run(
        ["make", "reproduce-b-phase91-gnome-mp-formula-prefilter"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "mp_formula_prefilter_completed_exact_matching_pending" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/b_phase91_gnome_mp_formula_prefilter"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
