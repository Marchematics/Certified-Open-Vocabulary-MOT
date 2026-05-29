from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase77_ncs_architecture_freeze"


def test_phase77_outputs_exist() -> None:
    expected = {
        "NCS_SPINE.md",
        "NCS_CLAIM_HIERARCHY.csv",
        "NCS_DISPLAY_PLAN.md",
        "NCS_OVERCLAIM_GUARDRAILS.md",
        "README_evidence_scope.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})


def test_phase77_spine_freezes_ncs_lifecycle_story() -> None:
    text = (OUT / "NCS_SPINE.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    required = [
        "Budgeted release certification for scientific AI candidate queues",
        "release cards rather than static top-K",
        "PARC-A is the primary empirical positive",
        "Materials is the lifecycle stress test, not the main positive",
        "Stop tuning materials K, margin, risk gates or active recertification",
        "Do not wait for DFT v2",
        "not a prospective materials-discovery claim",
        "not a current-MP alpha certificate",
    ]
    for phrase in required:
        assert phrase in normalized


def test_phase77_claim_hierarchy_has_roles_and_guardrails() -> None:
    claims = pd.read_csv(OUT / "NCS_CLAIM_HIERARCHY.csv")
    required_ids = {
        "NCS-THESIS",
        "PARC-CORE",
        "PARC-A-CTC",
        "PARC-A-MECHANISM",
        "PHASE76-LIFECYCLE",
        "MATERIALS-STRESS",
        "PARC-D-TRIAGE",
        "PARC-D-CERT-NOGO",
        "ACTIVE-RECERT-NOGO",
        "DFT-V2-PENDING",
    }
    assert required_ids == set(claims["claim_id"])

    ctc = claims[claims["claim_id"].eq("PARC-A-CTC")].iloc[0]
    assert ctc["manuscript_role"] == "primary_empirical_positive"
    assert "2000 released links" in ctc["claim_text"]
    assert "disclose_masked_label_emulation" in ctc["overclaim_guardrail"]

    materials = claims[claims["claim_id"].eq("MATERIALS-STRESS")].iloc[0]
    assert materials["manuscript_role"] == "materials_stress_test"
    assert "prospective discovery" in materials["forbidden_language"]
    assert "materials_not_main_positive" in materials["overclaim_guardrail"]

    triage = claims[claims["claim_id"].eq("PARC-D-TRIAGE")].iloc[0]
    assert "top 30%" in triage["claim_text"]
    assert "not a repaired alpha certificate" in triage["claim_text"]
    assert "triage_not_certificate" in triage["overclaim_guardrail"]

    dft = claims[claims["claim_id"].eq("DFT-V2-PENDING")].iloc[0]
    assert dft["evidence_state"] == "execution_checkpoint_only"
    assert "DFT validation" in dft["forbidden_language"]


def test_phase77_display_plan_has_six_non_overclaiming_figures() -> None:
    text = (OUT / "NCS_DISPLAY_PLAN.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    for idx in range(1, 7):
        assert f"Figure {idx}:" in text
    assert "PARC-A active verification primary positive" in text
    assert "Materials lifecycle stress test" in text
    assert "dropping the top" in text
    assert "label-free deployment predictor or current-MP certificate" in text
    assert "DFT v2 enters only after stable_exact and workflow gates pass" in normalized


def test_phase77_guardrails_block_known_overclaims() -> None:
    text = (OUT / "NCS_OVERCLAIM_GUARDRAILS.md").read_text(encoding="utf-8")
    forbidden = [
        "Do not claim prospective materials discovery",
        "Do not claim current-MP alpha certificate from materials",
        "Do not call Phase69b PARC-D a full certificate",
        "Do not soften Phase74 or Phase75 no-go",
        "Do not claim DFT v2 evidence before stable_exact outcomes",
        "Do not add new materials filters to rescue alpha",
    ]
    for phrase in forbidden:
        assert phrase in text


def test_phase77_ledger_and_artifact_index() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("NCS-ARCH-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "yes"
    assert "do_not_claim_new_empirical_evidence" in row.iloc[0]["overclaim_guardrail"]

    index = pd.read_csv(ROOT / "outputs/artifact_index.csv")
    artifact = index[index["milestone"].eq("ncs_phase77_ncs_architecture_freeze")]
    assert len(artifact) == 1
    assert artifact.iloc[0]["path"] == "outputs/milestones/ncs_phase77_ncs_architecture_freeze/"


def test_phase77_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase77-architecture-freeze"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "completed_NCS_architecture_freeze" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase77_ncs_architecture_freeze"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
