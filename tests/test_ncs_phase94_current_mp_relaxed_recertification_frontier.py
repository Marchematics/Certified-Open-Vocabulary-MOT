from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase94_current_mp_relaxed_recertification_frontier"


def test_phase94_outputs_exist_and_scope_guardrails() -> None:
    expected = {
        "PHASE94_CURRENT_MP_RELAXED_RECERTIFICATION_PROTOCOL.md",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
        "figure_phase94_current_mp_frontier_inputs.csv",
        "table_phase94_best_operating_rows.csv",
        "table_phase94_gate_audit.csv",
        "table_phase94_recertification_alpha_frontier_seed_rows.csv",
        "table_phase94_recertification_alpha_frontier_summary.csv",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "not_DFT_evidence" in readme
    assert "not_strict_alpha_0p10_certificate_if_relaxed_only" in readme


def test_phase94_reports_full_small_k_alpha_grid() -> None:
    summary = pd.read_csv(OUT / "table_phase94_recertification_alpha_frontier_summary.csv")
    assert {0.10, 0.15, 0.20}.issubset(set(summary["alpha"].round(2)))
    assert {25, 50, 75, 100, 150, 200}.issubset(set(summary["K"]))
    assert {
        "random_t1_audit",
        "score_targeted_t1_audit",
        "low_risk_score_targeted_t1_audit",
        "blockmax_gain_t1_audit",
    }.issubset(set(summary["audit_policy"]))
    assert {
        "t1_10pct_support",
        "t1_full_calibration_block_support",
    }.issubset(set(summary["support_mode"]))
    assert summary["evidence_scope"].str.contains("test_side_t1_labels_used_only_after_release_for_FTR").all()


def test_phase94_no_strict_or_relaxed_positive_gate_is_overclaimed() -> None:
    gate = pd.read_csv(OUT / "table_phase94_gate_audit.csv").set_index("gate")
    assert gate.loc["full_grid_reported", "status"] == "PASS"
    assert gate.loc["strict_alpha_0p10_current_mp_recertified_release", "status"] in {"PASS", "FAIL"}
    assert gate.loc["relaxed_alpha_current_mp_operating_release", "status"] in {"PASS", "FAIL"}

    best = pd.read_csv(OUT / "table_phase94_best_operating_rows.csv")
    assert len(best) > 0
    if gate.loc["strict_alpha_0p10_current_mp_recertified_release", "status"] == "FAIL":
        strict = pd.read_csv(OUT / "table_phase94_recertification_alpha_frontier_summary.csv")
        assert not strict["strict_alpha_0p10_success"].astype(bool).any()


def test_phase94_no_leakage_flags_and_recomputed_denominator() -> None:
    seeds = pd.read_csv(OUT / "table_phase94_recertification_alpha_frontier_seed_rows.csv")
    assert not seeds["policy_uses_t1_test_labels"].astype(bool).any()
    assert not seeds["heldout_t1_used_for_selection"].astype(bool).any()
    assert seeds["t1_labels_used_only_for_calibration_audit"].astype(bool).all()
    assert seeds["denominator_recomputed_after_audit"].astype(bool).all()
    assert seeds["evalues_recomputed_after_audit"].astype(bool).all()


def test_phase94_ledger_claim_table_reproduce_and_public_bundle() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("NCS-PHASE94-CURRENT-MP-RECERT-FRONTIER-001")]
    assert len(row) == 1
    assert "do_not_claim_DFT_evidence" in row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase94 Current-MP Relaxed Recertification Frontier" in claim_table
    assert "not DFT evidence" in claim_table

    result = subprocess.run(
        ["make", "reproduce-ncs-phase94-current-mp-relaxed-recertification-frontier"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "[phase94] status=" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase94_current_mp_relaxed_recertification_frontier"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
