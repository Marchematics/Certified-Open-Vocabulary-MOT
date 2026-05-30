from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase88_low_cost_editorial_hardening"


def test_phase88_editorial_outputs_exist_and_scope_is_synthesis_only() -> None:
    expected = {
        "README_evidence_scope.md",
        "NCS_PHASE88_LOW_COST_EDITORIAL_HARDENING.md",
        "cover_letter_core.md",
        "intro_first_screen.md",
        "table_low_cost_action_matrix.csv",
        "table_editorial_capability_table.csv",
        "table_phase81_phase83_write_permissions.csv",
        "table_editorial_overclaim_scrub.csv",
        "table_caption_first_lines.csv",
        "table_phase88_editorial_claim_gate.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "completed_editorial_synthesis_not_new_evidence" in readme
    assert "does not add new empirical evidence" in readme
    assert "B-line claim-decay evidence" in readme


def test_phase88_editorial_action_matrix_covers_low_cost_items() -> None:
    actions = pd.read_csv(OUT / "table_low_cost_action_matrix.csv")
    assert {
        "rewrite_first_screen",
        "front_existing_real_audit_envelopes",
        "front_phase83_necessity_and_prevented_harm",
        "insert_capability_table",
        "overclaim_scrub",
    }.issubset(set(actions["action"]))
    assert actions["new_evidence_required"].eq("no").all()
    assert actions["evidence_scope"].str.contains("no_new_empirical_result").all()


def test_phase88_capability_table_distinguishes_lifecycle_from_ebh() -> None:
    cap = pd.read_csv(OUT / "table_editorial_capability_table.csv")
    assert len(cap) >= 8
    assert cap["PARC_release_card_lifecycle"].eq("yes").all()
    expiry = cap[cap["capability"].eq("reference-version expiry")].iloc[0]
    assert expiry["eBH_or_evalue_selection"] == "no"
    assert expiry["PARC_release_card_lifecycle"] == "yes"


def test_phase88_permissions_and_overclaim_guardrails() -> None:
    perms = pd.read_csv(OUT / "table_phase81_phase83_write_permissions.csv")
    phase81 = perms[perms["item"].str.contains("Phase81")].iloc[0]
    assert "pending" in phase81["current_status"]
    assert "internal_ledger_only" in phase81["submission_permission"]
    assert "External blind audit confirms" in phase81["forbidden_sentence"]

    scrub = pd.read_csv(OUT / "table_editorial_overclaim_scrub.csv")
    risky = " ".join(scrub["forbidden_or_risky_phrase"].astype(str))
    assert "prospective materials discovery" in risky
    assert "current-MP alpha certificate" in risky


def test_phase88_editorial_gate_ledger_claim_table_and_reproduce() -> None:
    gate = pd.read_csv(OUT / "table_phase88_editorial_claim_gate.csv")
    assert gate.iloc[0]["positive_evidence"] == "synthesis_only"
    assert "Do not claim new labels" in gate.iloc[0]["forbidden_current_claim"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("NCS-PHASE88-EDITORIAL-HARDENING-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "synthesis_only"

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase88 Low-Cost Editorial Hardening" in claim_table
    assert "synthesis only" in claim_table

    result = subprocess.run(
        ["make", "reproduce-ncs-phase88-low-cost-editorial-hardening"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    result = subprocess.run(
        [
            "python",
            "scripts/validate_public_bundle.py",
            "outputs/milestones/ncs_phase88_low_cost_editorial_hardening",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
