from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "b_phase88_current_reference_smoke"


def test_phase88_b_outputs_exist_and_are_smoke_only() -> None:
    expected = {
        "README_evidence_scope.md",
        "PHASE88_CURRENT_REFERENCE_SMOKE_PROTOCOL.md",
        "table_phase88_current_reference_smoke_rows.csv",
        "table_phase88_current_reference_smoke_summary.csv",
        "table_phase88_smoke_claim_gate.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    flat_readme = " ".join(readme.split())
    assert "low_cost_smoke_completed_not_claim_decay" in readme
    assert "does not perform exact-structure matching" in flat_readme
    assert "Forbidden claims" in readme


def test_phase88_b_rows_cover_registry_and_keep_gnome_pending() -> None:
    registry = pd.read_csv(ROOT / "outputs/milestones/b_phase87_minimal_claim_registry/table_phase87_minimal_claim_registry.csv")
    rows = pd.read_csv(OUT / "table_phase88_current_reference_smoke_rows.csv")
    assert len(rows) == len(registry)
    assert set(rows["source_family"]) == {"matbench_discovery_wbm", "gnome_public_stable_materials"}

    wbm = rows[rows["source_family"].eq("matbench_discovery_wbm")]
    gnome = rows[rows["source_family"].eq("gnome_public_stable_materials")]
    assert len(wbm) == 150
    assert wbm["match_status"].eq("matched_existing_t1_snapshot_by_wbm_material_id").all()
    assert set(wbm["current_stability_verdict"]).issubset(
        {"stable_current_reference_smoke", "unstable_current_reference_smoke"}
    )
    assert len(gnome) == 150
    assert gnome["match_status"].eq("not_queried_low_cost_phase88").all()
    assert gnome["current_stability_verdict"].isna().all() or gnome["current_stability_verdict"].eq("").all()


def test_phase88_b_summary_and_gate_scope() -> None:
    summary = pd.read_csv(OUT / "table_phase88_current_reference_smoke_summary.csv")
    wbm = summary[summary["source_family"].eq("matbench_discovery_wbm")].iloc[0]
    gnome = summary[summary["source_family"].eq("gnome_public_stable_materials")].iloc[0]
    assert wbm["low_cost_smoke_matched_rows"] == 150
    assert wbm["current_claim_status"] == "weak_smoke_only"
    assert gnome["low_cost_smoke_matched_rows"] == 0
    assert gnome["current_claim_status"] == "pending"
    assert not summary["exact_raw_structure_hash_available"].any()

    gate = pd.read_csv(OUT / "table_phase88_smoke_claim_gate.csv")
    assert gate.iloc[0]["positive_evidence"] == "weak_smoke_only"
    assert "Do not claim exact-structure claim decay" in gate.iloc[0]["forbidden_current_claim"]


def test_phase88_b_ledger_claim_table_and_reproduce() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("B-PHASE88-CURRENT-REFERENCE-SMOKE-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "weak_smoke_only"
    assert "not_SCDR" in row.iloc[0]["scope"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase88 B-Line Current-Reference Smoke" in claim_table
    assert "no source-level claim-decay metric is allowed" in claim_table

    result = subprocess.run(
        ["make", "reproduce-b-phase88-current-reference-smoke"],
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
            "outputs/milestones/b_phase88_current_reference_smoke",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
