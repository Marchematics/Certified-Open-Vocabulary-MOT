from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "b_phase87_minimal_claim_registry"


def test_phase87_outputs_exist_and_are_registry_only() -> None:
    expected = {
        "PHASE87_MINIMAL_CLAIM_REGISTRY_PROTOCOL.md",
        "README_evidence_scope.md",
        "table_phase87_minimal_claim_registry.csv",
        "table_phase87_ingest_summary.csv",
        "table_phase87_current_reference_query_manifest.csv",
        "table_phase87_claim_gate.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "minimal_registry_frozen_current_reference_verdicts_pending" in readme
    assert "does not query current references" in readme
    assert "does not compute claim" in readme


def test_phase87_registry_has_two_sources_and_minimum_rows() -> None:
    registry = pd.read_csv(OUT / "table_phase87_minimal_claim_registry.csv")
    assert len(registry) == 300
    counts = registry["source_family"].value_counts().to_dict()
    assert counts["matbench_discovery_wbm"] == 150
    assert counts["gnome_public_stable_materials"] == 150
    assert registry["claim_uid"].is_unique
    assert registry["original_structure_hash"].astype(str).str.len().eq(64).all()
    assert registry["evidence_scope"].str.contains("current_reference_verdicts_pending").all()


def test_phase87_summary_records_proxy_hash_and_query_limits() -> None:
    summary = pd.read_csv(OUT / "table_phase87_ingest_summary.csv")
    assert set(summary["source_family"]) == {
        "matbench_discovery_wbm",
        "gnome_public_stable_materials",
    }
    assert summary["registry_rows"].min() >= 150
    assert summary["meets_minimum_row_gate"].all()
    assert not summary["exact_raw_structure_hash_available"].any()
    assert summary["current_reference_query_ready"].str.contains("structure").all()


def test_phase87_query_manifest_has_pending_mp_and_oqmd_rows() -> None:
    registry = pd.read_csv(OUT / "table_phase87_minimal_claim_registry.csv")
    manifest = pd.read_csv(OUT / "table_phase87_current_reference_query_manifest.csv")
    assert len(manifest) == 2 * len(registry)
    assert set(manifest["reference_source"]) == {"materials_project_current", "oqmd_current"}
    assert set(manifest["match_status"]) == {"not_queried_phase87"}
    assert manifest["current_stability_verdict"].isna().all() or manifest["current_stability_verdict"].eq("").all()


def test_phase87_claim_gate_ledger_and_claim_table_guardrails() -> None:
    claim = pd.read_csv(OUT / "table_phase87_claim_gate.csv")
    assert len(claim) == 1
    row = claim.iloc[0]
    assert row["positive_evidence"] == "no"
    assert "current_reference_verdicts_pending" in row["status"]
    assert row["total_registry_rows"] == 300
    assert "Do not claim claim decay" in row["forbidden_current_claim"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    ledger_row = ledger[ledger["claim_id"].eq("B-PHASE87-MINIMAL-REGISTRY-001")]
    assert len(ledger_row) == 1
    assert ledger_row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_decay" in ledger_row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    flat = " ".join(claim_table.split())
    assert "Phase87 Minimal External Claim Registry" in claim_table
    assert "no current-reference verdicts have been produced" in flat


def test_phase87_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-b-phase87-minimal-claim-registry"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "minimal_registry_frozen_current_reference_verdicts_pending" in result.stdout

    result = subprocess.run(
        [
            "python",
            "scripts/validate_public_bundle.py",
            "outputs/milestones/b_phase87_minimal_claim_registry",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
