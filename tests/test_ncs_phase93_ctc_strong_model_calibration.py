from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase93_ctc_strong_model_calibration"


def test_phase93_ctc_outputs_exist_and_scope_is_retrospective_calibration() -> None:
    expected = {
        "PHASE93_CTC_STRONG_MODEL_CALIBRATION_PROTOCOL.md",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
        "figure_phase93_strong_model_calibration_inputs.csv",
        "table_phase93_high_confidence_gate.csv",
        "table_phase93_strong_model_by_packet_calibration.csv",
        "table_phase93_strong_model_confusion.csv",
        "table_phase93_strong_model_vs_existing_human_labels.csv",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "retrospective_surrogate_calibration_passed_against_existing_human_labels" in readme
    assert "not a new external human audit" in readme


def test_phase93_ctc_join_and_high_confidence_gate() -> None:
    rows = pd.read_csv(OUT / "table_phase93_strong_model_vs_existing_human_labels.csv")
    assert len(rows) == 600
    assert rows["human_label"].notna().all()
    assert rows["strong_model_label"].notna().all()
    assert rows["evidence_scope"].str.contains("not_external_human_audit").all()

    gate = pd.read_csv(OUT / "table_phase93_high_confidence_gate.csv").iloc[0]
    assert gate["positive_evidence"] == "no"
    assert int(gate["joined_rows"]) == 600
    assert int(gate["high_confidence_positive_rows"]) > 0
    assert int(gate["high_confidence_false_positive_count"]) == 0
    assert "external human audit evidence" in gate["forbidden_current_claim"]


def test_phase93_ctc_confusion_includes_uncertain_and_controls() -> None:
    confusion = pd.read_csv(OUT / "table_phase93_strong_model_confusion.csv")
    assert {"same_cell_supported", "uncertain", "unsupported"}.issubset(set(confusion["strong_model_label"]))

    by_group = pd.read_csv(OUT / "table_phase93_strong_model_by_packet_calibration.csv")
    packets = by_group[by_group["group_name"].eq("packet")]
    assert {
        "calibration_audit",
        "release_audit",
        "hard_negative_or_uncertain_control",
        "random_same_budget_control",
        "raw_overlap_diagnostic",
    }.issubset(set(packets["group_value"]))
    hard = packets[packets["group_value"].eq("hard_negative_or_uncertain_control")].iloc[0]
    assert int(hard["human_negative"]) > 0


def test_phase93_ctc_ledger_claim_table_reproduce_and_public_bundle() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("CTC-PHASE93-STRONG-MODEL-CALIBRATION-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_new_external_human_audit" in row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase93 CTC Strong-Model Calibration" in claim_table
    assert "not new external human audit" in claim_table

    result = subprocess.run(
        ["make", "reproduce-ncs-phase93-ctc-strong-model-calibration"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "retrospective_surrogate_calibration_passed_against_existing_human_labels" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase93_ctc_strong_model_calibration"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
