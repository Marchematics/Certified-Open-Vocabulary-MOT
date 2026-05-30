from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "b_phase90_gnome_raw_structure_ingest"


def test_phase90_outputs_exist_and_scope_is_ingest_only() -> None:
    expected = {
        "PHASE90_GNOME_RAW_STRUCTURE_INGEST_PROTOCOL.md",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
        "table_phase90_claim_gate.csv",
        "table_phase90_gnome_ingest_summary.csv",
        "table_phase90_gnome_raw_structure_ingest.csv",
        "table_phase90_next_match_steps.csv",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "derived_structure_ingest_completed_current_verdicts_pending" in readme
    assert "not claim-decay evidence" in readme
    assert "Raw CIF files remain outside" not in readme  # wording belongs in claim table, not public scope summary


def test_phase90_ingests_all_frozen_gnome_rows_without_raw_cif_columns() -> None:
    rows = pd.read_csv(OUT / "table_phase90_gnome_raw_structure_ingest.csv")
    assert len(rows) == 150
    assert rows["raw_cif_present_in_local_cache"].astype(bool).all()
    assert rows["parse_status"].eq("parsed").all()
    assert rows["raw_cif_sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert "raw_cif_text" not in rows.columns
    assert "cif" not in {col.lower() for col in rows.columns if col.lower() == "raw_cif_text"}
    assert rows["pymatgen_n_sites"].astype(int).gt(0).all()
    assert rows["pymatgen_chemical_system"].astype(str).str.len().gt(0).all()
    assert rows["evidence_scope"].str.contains("current_reference_verdicts_pending").all()


def test_phase90_summary_keeps_verdict_and_matching_pending() -> None:
    summary = pd.read_csv(OUT / "table_phase90_gnome_ingest_summary.csv").iloc[0]
    assert int(summary["registry_rows"]) == 150
    assert int(summary["raw_cif_present_rows"]) == 150
    assert int(summary["parsed_rows"]) == 150
    assert not bool(summary["raw_cif_committed_to_git"])
    assert not bool(summary["current_reference_verdicts_available"])
    assert not bool(summary["exact_structure_matching_completed"])
    assert summary["claim_status"] == "derived_structure_ingest_completed_current_verdicts_pending"


def test_phase90_gate_ledger_claim_table_and_reproduce() -> None:
    gate = pd.read_csv(OUT / "table_phase90_claim_gate.csv")
    assert len(gate) == 1
    assert gate.iloc[0]["positive_evidence"] == "no"
    assert "Do not claim completed exact matching" in gate.iloc[0]["forbidden_current_claim"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("B-PHASE90-GNOME-STRUCTURE-INGEST-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_completed_exact_matching_or_decay" in row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase90 B-Line GNoME Raw-Structure Ingest" in claim_table
    assert "not claim-decay evidence" in claim_table

    result = subprocess.run(
        ["make", "reproduce-b-phase90-gnome-raw-structure-ingest"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "derived_structure_ingest_completed_current_verdicts_pending" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/b_phase90_gnome_raw_structure_ingest"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
