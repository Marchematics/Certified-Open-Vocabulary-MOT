from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "nmi_presubmission_package"


def test_presubmission_lead_numbers_are_completed_primary_claims() -> None:
    lead = pd.read_csv(MILESTONE / "table_lead_numbers_for_editor.csv")

    assert not lead.empty
    assert set(lead["manuscript_role"]) == {"primary_headline"}
    banned = {"diagnostic_only", "failed_gate", "protocol_only", "pending"}
    assert not set(lead["evidence_state"].astype(str)).intersection(banned)
    assert lead["source_artifact"].astype(str).str.len().gt(0).all()
    assert lead["source_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()


def test_one_page_evidence_table_has_source_provenance_for_every_row() -> None:
    evidence = pd.read_csv(MILESTONE / "one_page_evidence_table.csv")

    assert not evidence.empty
    assert evidence["source_artifact"].astype(str).str.len().gt(0).all()
    assert evidence["source_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()
    assert evidence["lead_consequence"].astype(str).str.len().gt(0).all()

    stress = evidence[evidence["evidence_block"].astype(str).str.contains("external-source")]
    assert len(stress) == 1
    assert stress["manuscript_role"].iloc[0] == "stress_test"
    assert "not promoted as positive validation" in stress["parc_decision"].iloc[0]


def test_presubmission_inquiry_scope_and_exclusions() -> None:
    text = (MILESTONE / "presubmission_inquiry_v1.md").read_text(encoding="utf-8")

    assert "release-time certification" in text or "release/refuse" in text
    assert "release set or a certified refusal" in text
    assert "prospective materials discovery is not claimed" in text
    assert "not as positive independent validation" in text
    assert "K=300: raw top-K FTR" in text
    assert "K=500: raw top-K FTR" in text


def test_abstract_does_not_claim_prospective_materials_discovery() -> None:
    text = (MILESTONE / "nmi_abstract_v1.md").read_text(encoding="utf-8")

    assert "without claiming prospective discovery" in text
    assert "source-discordance stress tests" in text
    assert "governs release under partial evidence" in text
    assert "new materials discovered" not in text.lower()
    assert "experimental synthesis" not in text.lower()

