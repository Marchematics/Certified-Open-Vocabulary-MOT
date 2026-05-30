from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "b_phase86_claim_decay_access_preflight"


def test_phase86_outputs_exist_and_are_preflight_only() -> None:
    expected = {
        "PHASE86_ACCESS_PREFLIGHT_PROTOCOL.md",
        "README_evidence_scope.md",
        "table_phase86_local_dependency_status.csv",
        "table_phase86_source_access_smoke.csv",
        "table_phase86_mp_version_status.csv",
        "claim_registry_template.csv",
        "claim_registry_schema.json",
        "current_reference_query_manifest_template.csv",
        "table_phase86_ingest_preflight_plan.csv",
        "table_phase86_claim_gate.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "access_preflight_completed_claim_registry_empty" in readme
    assert "does not ingest claims" in readme
    assert "does not compute any current-reference verdict" in readme


def test_phase86_dependency_and_access_tables_are_safe() -> None:
    deps = pd.read_csv(OUT / "table_phase86_local_dependency_status.csv")
    assert {"requests", "pymatgen", "mp_api", "ase", "pandas"}.issubset(set(deps["dependency"]))
    assert deps["evidence_scope"].str.contains("source_access_smoke_only").all()

    access = pd.read_csv(OUT / "table_phase86_source_access_smoke.csv")
    assert {
        "matbench_discovery_wbm",
        "gnome_public_stable_materials",
        "alexandria_hull_or_claim_surface",
        "materials_project_current",
        "oqmd_current",
    }.issubset(set(access["source_id"]))
    assert "MP_API_KEY" not in access.to_csv(index=False)
    assert access["evidence_scope"].str.contains("current_reference_verdicts_pending").all()


def test_phase86_mp_version_status_does_not_leak_key() -> None:
    mp = pd.read_csv(OUT / "table_phase86_mp_version_status.csv")
    assert len(mp) == 1
    assert "MP_API_KEY" not in mp.to_csv(index=False)
    assert set(mp["status"]).issubset(
        {"version_captured", "version_query_failed", "blocked_missing_MP_API_KEY"}
    )


def test_phase86_templates_are_empty_and_have_required_columns() -> None:
    claim_registry = pd.read_csv(OUT / "claim_registry_template.csv")
    assert claim_registry.empty
    assert {
        "claim_uid",
        "source_family",
        "original_claim_text",
        "original_structure_hash",
        "ingest_status",
        "evidence_scope",
    }.issubset(claim_registry.columns)

    query_manifest = pd.read_csv(OUT / "current_reference_query_manifest_template.csv")
    assert query_manifest.empty
    assert {
        "query_uid",
        "claim_uid",
        "reference_source",
        "reference_version",
        "current_stability_verdict",
        "evidence_scope",
    }.issubset(query_manifest.columns)


def test_phase86_claim_gate_ledger_and_claim_table_guardrails() -> None:
    claim = pd.read_csv(OUT / "table_phase86_claim_gate.csv")
    assert len(claim) == 1
    row = claim.iloc[0]
    assert row["positive_evidence"] == "no"
    assert "claim_registry_empty" in row["status"]
    assert "Do not claim source decay" in row["forbidden_current_claim"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    ledger_row = ledger[ledger["claim_id"].eq("B-PHASE86-ACCESS-PREFLIGHT-001")]
    assert len(ledger_row) == 1
    assert ledger_row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_decay_rate" in ledger_row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    flat = " ".join(claim_table.split())
    assert "Phase86 Claim-Decay Access Preflight" in claim_table
    assert "no current-reference verdicts have been produced" in flat


def test_phase86_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-b-phase86-claim-decay-access-preflight"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "access_preflight_completed_claim_registry_empty" in result.stdout

    result = subprocess.run(
        [
            "python",
            "scripts/validate_public_bundle.py",
            "outputs/milestones/b_phase86_claim_decay_access_preflight",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
