from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE58 = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening"


def test_phase58_outputs_exist() -> None:
    expected = {
        "REPRODUCE_PHASE49.md",
        "REPRODUCE_T1_HULL_AUDIT.md",
        "REPRODUCE_MLIP_AUDIT.md",
        "DATA_PROVENANCE_MATERIALS.md",
        "EVIDENCE_SCOPE_LEDGER.csv",
        "NCS_PHASE58_REPRODUCIBILITY_HARDENING.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE58 / name).exists()]


def test_evidence_ledger_has_hashes_guardrails_and_no_overclaim_scope() -> None:
    ledger = pd.read_csv(PHASE58 / "EVIDENCE_SCOPE_LEDGER.csv")
    required = {
        "claim_id",
        "claim_text",
        "evidence_type",
        "positive_evidence",
        "scope",
        "artifact_path",
        "hash",
        "validation_command",
        "status",
        "overclaim_guardrail",
    }
    assert required.issubset(ledger.columns)
    assert ledger["claim_id"].is_unique
    assert (ledger["status"] == "PASS").all()
    assert ledger["hash"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()
    assert ledger["overclaim_guardrail"].astype(str).str.len().gt(10).all()
    positive = ledger[ledger["positive_evidence"].eq("yes")]
    assert not positive["scope"].isin(["pending", "protocol_only", "diagnostic_only", "failed_gate"]).any()
    mlip = ledger[ledger["claim_id"].eq("M-MLIP-001")].iloc[0]
    assert "CHGNet/MACE score-support proxies favor PARC" in mlip["claim_text"]
    assert mlip["positive_evidence"] == "yes"
    assert "score_support_proxy" in mlip["scope"]
    boundary = ledger[ledger["claim_id"].eq("M-MLIP-002")].iloc[0]
    assert boundary["positive_evidence"] == "no"
    assert "partial_false_case_mechanism" in boundary["scope"]
    version = ledger[ledger["claim_id"].eq("M-VSHIFT-001")].iloc[0]
    assert "decomposes into t0 FTR" in version["claim_text"]
    assert "t1_alpha_control" in version["overclaim_guardrail"]
    baseline = ledger[ledger["claim_id"].eq("M-BASE-T1-001")].iloc[0]
    assert "matched-volume boundary" in baseline["claim_text"]
    assert "not_equal_target_object" in baseline["scope"]
    parc_v = ledger[ledger["claim_id"].eq("M-PARCV-001")].iloc[0]
    assert parc_v["positive_evidence"] == "no"
    assert "no_go_for_headline" in parc_v["scope"]
    assert "t1_alpha_control" in parc_v["overclaim_guardrail"]
    parc_m = ledger[ledger["claim_id"].eq("M-PARCM-001")].iloc[0]
    assert parc_m["positive_evidence"] == "partial"
    assert "empirical_medium_signal" in parc_m["scope"]
    assert "multi_evidence_evalue_certificate" in parc_m["overclaim_guardrail"]


def test_validate_evidence_ledger_script_passes() -> None:
    result = subprocess.run(
        ["python", "scripts/validate_evidence_ledger.py"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "validated" in result.stdout
