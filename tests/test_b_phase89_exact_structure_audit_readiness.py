from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "b_phase89_exact_structure_audit_readiness"


def test_phase89_b_outputs_exist_and_are_readiness_only() -> None:
    expected = {
        "README_evidence_scope.md",
        "PHASE89_EXACT_STRUCTURE_AUDIT_PROTOCOL.md",
        "table_phase89_endpoint_and_cache_status.csv",
        "table_phase89_source_readiness.csv",
        "table_phase89_gnome_structure_ingest_manifest.csv",
        "table_phase89_exact_match_execution_plan.csv",
        "table_phase89_execution_commands.csv",
        "table_phase89_claim_gate.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "readiness_and_protocol_only_current_verdicts_pending" in readme
    assert "Raw GNoME structures are intentionally cached under `cache/`" in readme


def test_phase89_b_endpoint_and_source_readiness_scope() -> None:
    endpoints = pd.read_csv(OUT / "table_phase89_endpoint_and_cache_status.csv")
    gnome = endpoints[endpoints["source"].eq("gnome_by_id_zip")].iloc[0]
    assert bool(gnome["reachable"])
    assert int(gnome["content_length_bytes"]) > 400_000_000
    assert not bool(gnome["raw_data_versioned_in_git"])

    sources = pd.read_csv(OUT / "table_phase89_source_readiness.csv")
    assert set(sources["source_family"]) == {"matbench_discovery_wbm", "gnome_public_stable_materials"}
    assert sources["claim_status_after_phase89"].eq("readiness_only").all()
    assert sources["evidence_scope"].str.contains("current_reference_verdicts_pending").all()


def test_phase89_b_ingest_manifest_and_execution_plan() -> None:
    ingest = pd.read_csv(OUT / "table_phase89_gnome_structure_ingest_manifest.csv")
    assert len(ingest) == 150
    assert ingest["material_id"].astype(str).str.len().gt(0).all()
    assert ingest["redistribution_policy"].eq("do_not_commit_raw_structure;derived_hashes_only").all()

    plan = pd.read_csv(OUT / "table_phase89_exact_match_execution_plan.csv")
    assert {"raw_structure_ingest", "mp_prefilter", "structure_match", "current_reference_verdict"}.issubset(
        set(plan["operation"])
    )
    assert plan["guardrail"].str.contains("do_not").all()


def test_phase89_b_gate_ledger_claim_table_and_reproduce() -> None:
    gate = pd.read_csv(OUT / "table_phase89_claim_gate.csv")
    assert gate.iloc[0]["positive_evidence"] == "no"
    assert "Do not claim completed exact matching" in gate.iloc[0]["forbidden_current_claim"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("B-PHASE89-EXACT-STRUCTURE-READINESS-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase89 B-Line Exact-Structure Audit Readiness" in claim_table
    assert "not claim-decay evidence" in claim_table

    result = subprocess.run(
        ["make", "reproduce-b-phase89-exact-structure-audit-readiness"],
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
            "outputs/milestones/b_phase89_exact_structure_audit_readiness",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
