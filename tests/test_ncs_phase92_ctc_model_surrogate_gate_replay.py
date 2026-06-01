from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase92_ctc_model_surrogate_gate_replay"


def test_phase92_outputs_exist_and_scope_is_not_human_evidence() -> None:
    expected = {
        "PHASE92_CTC_MODEL_SURROGATE_GATE_REPLAY_PROTOCOL.md",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
        "figure_phase92_model_surrogate_gate_replay_inputs.csv",
        "table_phase92_claim_gate.csv",
        "table_phase92_model_surrogate_gate_replay.csv",
        "table_phase92_model_surrogate_packet_summary.csv",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "model_surrogate_gate_replay_completed_not_human_evidence" in readme
    assert "not external human evidence" in readme


def test_phase92_packet_summary_has_expected_packets_and_conservative_bounds() -> None:
    summary = pd.read_csv(OUT / "table_phase92_model_surrogate_packet_summary.csv")
    assert {
        "calibration_audit",
        "release_audit",
        "random_same_budget_control",
        "raw_overlap_diagnostic",
        "hard_negative_or_uncertain_control",
    }.issubset(set(summary["packet"]))
    assert summary["rows"].sum() == 600
    assert summary["cp95_upper_conservative_fail_fraction"].between(0, 1).all()
    assert summary["evidence_scope"].str.contains("not_external_human_audit").all()


def test_phase92_gate_replay_is_operational_not_positive_claim() -> None:
    gates = pd.read_csv(OUT / "table_phase92_model_surrogate_gate_replay.csv").set_index("gate")
    assert gates.loc["model_surrogate_calibration_support_available", "status"] in {"PASS", "FAIL"}
    assert gates.loc["model_surrogate_release_conservative_FTR_point", "status"] in {"PASS", "FAIL"}
    assert gates.loc["random_same_budget_control_not_empty_under_surrogate", "status"] == "DIAGNOSTIC"

    claim = pd.read_csv(OUT / "table_phase92_claim_gate.csv").iloc[0]
    assert claim["positive_evidence"] == "no"
    assert "external human audit success" in claim["forbidden_current_claim"]


def test_phase92_ledger_claim_table_reproduce_and_public_bundle() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("CTC-PHASE92-MODEL-SURROGATE-GATE-REPLAY-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_external_human_audit_success" in row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase92 CTC Model-Surrogate Gate Replay" in claim_table
    assert "not external human audit evidence" in claim_table

    result = subprocess.run(
        ["make", "reproduce-ncs-phase92-ctc-model-surrogate-gate-replay"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "model_surrogate_gate_replay_completed_not_human_evidence" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase92_ctc_model_surrogate_gate_replay"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
