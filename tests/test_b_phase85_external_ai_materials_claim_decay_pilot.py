from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "b_phase85_external_ai_materials_claim_decay_pilot"


def test_phase85_outputs_exist_and_are_pending_protocol() -> None:
    expected = {
        "PHASE85_EXTERNAL_AI_MATERIALS_CLAIM_DECAY_PROTOCOL.md",
        "LICENSE_AND_PUBLICATION_BOUNDARY.md",
        "README_evidence_scope.md",
        "source_registry.yaml",
        "table_phase85_source_registry.csv",
        "table_phase85_claim_ontology.csv",
        "table_phase85_metric_definitions.csv",
        "table_phase85_go_no_go_gates.csv",
        "table_phase85_sampling_plan.csv",
        "table_phase85_pilot_timeline.csv",
        "table_phase85_claim_gate.csv",
        "phase85_ambiguity_adjudication_template.csv",
        "ambiguous_match_adjudication_schema.json",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "protocol_frozen_current_reference_verdicts_pending" in readme
    assert "not completed evidence" in readme
    assert "not part of the A-paper main evidence chain" in readme


def test_phase85_source_registry_freezes_primary_and_reference_sources() -> None:
    registry = pd.read_csv(OUT / "table_phase85_source_registry.csv")
    sources = set(registry["source_id"])
    assert {
        "matbench_discovery_wbm",
        "gnome_public_stable_materials",
        "alexandria_hull_or_claim_surface",
        "materials_project_current",
        "oqmd_current",
    }.issubset(sources)
    primary = registry[registry["role"].eq("primary_claim_surface")]
    assert set(primary["source_id"]) == {
        "matbench_discovery_wbm",
        "gnome_public_stable_materials",
    }
    assert primary["minimum_pilot_claims"].min() >= 150
    assert registry["evidence_scope"].str.contains("not_completed_positive_evidence").all()


def test_phase85_metrics_and_gates_match_protocol() -> None:
    metrics = pd.read_csv(OUT / "table_phase85_metric_definitions.csv")
    primary_metrics = set(metrics[metrics["headline_role"].eq("primary")]["metric"])
    assert primary_metrics == {"SCDR", "TDB@100", "EDMB"}
    assert "CAR" in set(metrics["metric"])
    assert metrics["evidence_scope"].str.contains("current_reference_verdicts_pending").all()

    gates = pd.read_csv(OUT / "table_phase85_go_no_go_gates.csv")
    assert {
        "source_freeze_before_current_reference",
        "minimum_pilot_size",
        "strong_decay_signal",
        "cross_source_replication",
        "ambiguity_control",
    }.issubset(set(gates["gate"]))
    assert gates["current_status"].str.contains("pending|frozen", regex=True).all()
    assert gates["required_for_strong_claim"].all()


def test_phase85_claim_gate_and_ledger_prevent_overclaim() -> None:
    claim = pd.read_csv(OUT / "table_phase85_claim_gate.csv")
    assert len(claim) == 1
    row = claim.iloc[0]
    assert row["positive_evidence"] == "no"
    assert "verdicts_pending" in row["status"]
    assert "Do not claim any decay rate" in row["forbidden_current_claim"]
    assert "not_A_paper_main_evidence" in row["evidence_scope"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    ledger_row = ledger[ledger["claim_id"].eq("B-PHASE85-CLAIM-DECAY-PILOT-001")]
    assert len(ledger_row) == 1
    assert ledger_row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_decay_rate" in ledger_row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    flat = " ".join(claim_table.split())
    assert "Phase85 External AI-Materials Claim-Decay Audit Pilot" in claim_table
    assert "no current-reference verdicts have been produced" in flat


def test_phase85_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-b-phase85-external-ai-materials-claim-decay-pilot"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "protocol_frozen_current_reference_verdicts_pending" in result.stdout

    result = subprocess.run(
        [
            "python",
            "scripts/validate_public_bundle.py",
            "outputs/milestones/b_phase85_external_ai_materials_claim_decay_pilot",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
