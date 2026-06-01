from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "b_phase92_gnome_mp_neighbor_gap_analysis"


def test_phase92_b_outputs_exist_and_scope_is_gap_only() -> None:
    expected = {
        "PHASE92_GNOME_MP_NEIGHBOR_GAP_PROTOCOL.md",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
        "table_phase92_claim_gate.csv",
        "table_phase92_gnome_mp_neighbor_candidates.csv",
        "table_phase92_gnome_mp_neighbor_gap_summary.csv",
        "table_phase92_neighbor_gap_overview.csv",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "neighbor_gap_analysis_completed_no_exact_match_path" in readme
    assert "not claim-decay evidence" in readme


def test_phase92_b_confirms_no_exact_formula_path_and_no_verdicts() -> None:
    summary = pd.read_csv(OUT / "table_phase92_gnome_mp_neighbor_gap_summary.csv")
    neighbors = pd.read_csv(OUT / "table_phase92_gnome_mp_neighbor_candidates.csv")
    assert len(summary) == 150
    assert summary["mp_exact_formula_candidate_count"].eq(0).all()
    assert not summary["exact_match_path_available"].astype(bool).any()
    assert neighbors["exact_reduced_formula_match"].eq(False).all()
    assert not neighbors["structure_matching_completed"].astype(bool).any()
    assert not neighbors["current_stability_verdict_reported"].astype(bool).any()
    assert neighbors["composition_l1_distance"].ge(0).all()
    assert neighbors["evidence_scope"].str.contains("current_stability_verdicts_not_reported").all()


def test_phase92_b_overview_and_gate_are_no_positive_evidence() -> None:
    overview = pd.read_csv(OUT / "table_phase92_neighbor_gap_overview.csv").iloc[0]
    assert int(overview["gnome_rows"]) == 150
    assert int(overview["rows_with_exact_formula_candidates"]) == 0
    assert not bool(overview["structure_matching_completed"])
    assert not bool(overview["current_stability_verdicts_reported"])
    assert overview["claim_status"] == "neighbor_gap_analysis_completed_no_exact_match_path"

    gate = pd.read_csv(OUT / "table_phase92_claim_gate.csv").iloc[0]
    assert gate["positive_evidence"] == "no"
    assert "Do not claim exact structure matching" in gate["forbidden_current_claim"]


def test_phase92_b_ledger_claim_table_reproduce_and_public_bundle() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("B-PHASE92-GNOME-MP-NEIGHBOR-GAP-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_exact_structure_matching" in row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase92 B-Line GNoME MP Neighbor Gap Analysis" in claim_table
    assert "not exact" in claim_table

    result = subprocess.run(
        ["make", "reproduce-b-phase92-gnome-mp-neighbor-gap-analysis"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "neighbor_gap_analysis_completed_no_exact_match_path" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/b_phase92_gnome_mp_neighbor_gap_analysis"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
