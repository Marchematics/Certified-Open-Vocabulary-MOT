from pathlib import Path
import json
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase76_parc_lifecycle_calculus"


def test_phase76_outputs_exist() -> None:
    expected = {
        "supplement_parc_lifecycle_calculus.tex",
        "release_card_schema.json",
        "table_release_card_states.csv",
        "table_lifecycle_replay_ctc.csv",
        "table_lifecycle_replay_materials.csv",
        "figure_lifecycle_replay_inputs.csv",
        "table_lifecycle_baseline_capabilities.csv",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})


def test_theory_supplement_contains_required_calculus_blocks() -> None:
    text = (OUT / "supplement_parc_lifecycle_calculus.tex").read_text(encoding="utf-8")
    required = [
        "Least-favourable null-superset dominance",
        "Refusal lower bound",
        "Active audit gain",
        "Versioned certificate accounting",
        "Versioned recertification",
    ]
    for phrase in required:
        assert phrase in text
    assert "not be read as prospective materials discovery" in text


def test_release_card_schema_and_states_are_complete() -> None:
    schema = json.loads((OUT / "release_card_schema.json").read_text(encoding="utf-8"))
    states = set(schema["properties"]["lifecycle_state"]["enum"])
    required = {
        "certified_release",
        "certified_refusal",
        "expired_after_reference_update",
        "recertified_release",
        "recertified_refusal",
        "risk_triage_required",
        "active_audit_required",
    }
    assert required == states
    table = pd.read_csv(OUT / "table_release_card_states.csv")
    assert required == set(table["state"])
    assert table["forbidden_claim"].str.contains("prospective|absolute|automatic|negatives|alpha", case=False, regex=True).any()


def test_two_domain_lifecycle_replay_preserves_ctc_positive_and_materials_no_go() -> None:
    ctc = pd.read_csv(OUT / "table_lifecycle_replay_ctc.csv")
    assert {"active_audit_required", "certified_release"}.issubset(set(ctc["lifecycle_state"]))
    release = ctc[ctc["lifecycle_state"].eq("certified_release")].iloc[0]
    assert int(release["safe_seeds"]) == 20
    assert float(release["observed_FTR"]) == 0.0

    materials = pd.read_csv(OUT / "table_lifecycle_replay_materials.csv")
    assert {"expired_after_reference_update", "risk_triage_required", "recertified_refusal"}.issubset(
        set(materials["lifecycle_state"])
    )
    assert materials["interpretation"].str.contains("does not recover|does not repair|triage", case=False, regex=True).any()
    assert not materials["interpretation"].str.contains("prospective discovery", case=False, regex=False).any()


def test_baseline_capability_table_distinguishes_lifecycle_from_e_bh() -> None:
    table = pd.read_csv(OUT / "table_lifecycle_baseline_capabilities.csv")
    required_columns = {
        "method",
        "one_sided_validity",
        "can_release",
        "can_refuse",
        "can_acquire_audit",
        "can_expire_certificate",
        "can_recertify",
        "has_release_card",
        "handles_reference_drift",
    }
    assert required_columns.issubset(table.columns)
    lifecycle = table[table["method"].eq("PARC lifecycle")].iloc[0]
    assert bool(lifecycle["can_acquire_audit"])
    assert bool(lifecycle["can_expire_certificate"])
    assert bool(lifecycle["can_recertify"])
    assert bool(lifecycle["has_release_card"])

    ebh = table[table["method"].eq("e-BH selection")].iloc[0]
    assert bool(ebh["can_release"])
    assert not bool(ebh["one_sided_validity"])
    assert not bool(ebh["can_acquire_audit"])
    assert not bool(ebh["can_expire_certificate"])
    assert not bool(ebh["can_recertify"])
    assert not bool(ebh["has_release_card"])


def test_phase76_claim_ledger_and_guardrails() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("PARC-LIFECYCLE-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "yes"
    assert "do_not_claim_new_empirical_evidence" in row.iloc[0]["overclaim_guardrail"]
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "no DFT evidence",
        "no prospective materials discovery",
        "no current-MP alpha certificate",
        "e-BH is compared on lifecycle capability",
    ]:
        assert phrase in readme


def test_phase76_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase76-parc-lifecycle-calculus"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "completed_lifecycle_calculus_synthesis" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase76_parc_lifecycle_calculus"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
