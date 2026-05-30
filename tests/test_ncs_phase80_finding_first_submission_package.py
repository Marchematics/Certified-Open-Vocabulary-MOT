from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase80_finding_first_submission_package"


def test_phase80_outputs_exist_and_scope_guardrails() -> None:
    required = [
        "README_evidence_scope.md",
        "NCS_FINDING_FIRST_SPINE.md",
        "finding_first_abstract_150w.md",
        "table_phase80_finding_hierarchy.csv",
        "table_phase80_display_plan.csv",
        "table_phase80_venue_go_no_go.csv",
        "cover_letter_core_points.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    ]
    for name in required:
        assert (OUT / name).exists(), name

    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "not a new empirical result",
        "not a release certificate",
        "not DFT evidence",
        "not prospective materials-discovery evidence",
        "Do not claim NC/NCS stable desk acceptance",
        "Do not claim Phase79 is a new external empirical domain",
    ]:
        assert phrase in readme


def test_phase80_abstract_is_ncs_length_and_finding_first() -> None:
    text = (OUT / "finding_first_abstract_150w.md").read_text(encoding="utf-8")
    abstract = text.split("Word count:")[0].strip()
    assert len(abstract.split()) <= 150
    assert "release cards" in abstract
    assert "targeted one-sided audit" in abstract
    assert "reference updates" in abstract
    assert "controlled evolving-reference simulation" in abstract


def test_phase80_finding_hierarchy_uses_phase79_without_overclaim() -> None:
    findings = pd.read_csv(OUT / "table_phase80_finding_hierarchy.csv")
    assert set(findings["finding_id"]) >= {
        "F2_ACTIVE_VERIFICATION",
        "F4_DURABILITY_RISK",
        "F6_CONTROLLED_BREADTH",
        "F8_DFT_QUARANTINE",
    }
    phase79 = findings[findings["finding_id"].eq("F6_CONTROLLED_BREADTH")].iloc[0]
    assert "controlled mechanism demonstration" in phase79["allowed_claim"]
    assert "not a new external empirical domain" in phase79["guardrail"]
    assert "table_controlled_simulation_go_no_go.csv" in phase79["main_evidence"]

    dft = findings[findings["finding_id"].eq("F8_DFT_QUARANTINE")].iloc[0]
    assert "pending" in dft["paper_role"]
    assert "exclude from main claims" in dft["guardrail"]


def test_phase80_display_plan_promotes_breadth_but_keeps_scope() -> None:
    display = pd.read_csv(OUT / "table_phase80_display_plan.csv")
    fig4 = display[display["figure"].eq("Figure 4")].iloc[0]
    assert bool(fig4["include_phase79"]) is True
    assert "Controlled evolving-reference mechanisms" in fig4["title"]
    assert "not new external domain" in fig4["guardrail"]

    fig5 = display[display["figure"].eq("Figure 5")].iloc[0]
    assert "expire" in fig5["dominant_claim"]
    assert "not current-MP alpha certificate" in fig5["guardrail"]


def test_phase80_venue_go_no_go_is_honest_about_ncs() -> None:
    venue = pd.read_csv(OUT / "table_phase80_venue_go_no_go.csv")
    ncs = venue[venue["venue_track"].eq("Nature Computational Science")].iloc[0]
    assert ncs["go_no_go"] == "attempt_after_phase80_if_claims_remain_scoped"
    assert "not stable desk acceptance" in ncs["risk"]

    nc = venue[venue["venue_track"].eq("Nature Communications")].iloc[0]
    assert nc["go_no_go"] == "do_not_describe_as_stable"


def test_phase80_ledger_and_reproduce_target() -> None:
    ledger = pd.read_csv(
        ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    )
    row = ledger[ledger["claim_id"].eq("NCS-PHASE80-001")]
    assert len(row) == 1
    assert "not_new_empirical_result" in row.iloc[0]["scope"]
    assert row.iloc[0]["validation_command"] == "make reproduce-ncs-phase80-finding-first-submission-package"

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "reproduce-ncs-phase80-finding-first-submission-package" in makefile


def test_phase80_public_bundle_validation() -> None:
    subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase80_finding_first_submission_package"],
        cwd=ROOT,
        check=True,
    )
