from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase91_ctc_strong_model_annotation"


def test_phase91_outputs_exist_and_scope_is_surrogate_only() -> None:
    expected = {
        "PHASE91_CTC_STRONG_MODEL_ANNOTATION_PROTOCOL.md",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
        "figure_phase91_strong_model_annotation_inputs.csv",
        "phase91_model_surrogate_human_label_replacement.csv",
        "table_phase91_claim_gate.csv",
        "table_phase91_ctc_strong_model_annotations.csv",
        "table_phase91_input_audit.csv",
        "table_phase91_strong_model_by_hidden_arm_diagnostic.csv",
        "table_phase91_strong_model_by_packet_summary.csv",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "strong_model_surrogate_annotations_completed_not_human_evidence" in readme
    assert "not external human evidence" in readme


def test_phase91_annotations_cover_all_phase84_rows_and_have_image_features() -> None:
    rows = pd.read_csv(OUT / "table_phase91_ctc_strong_model_annotations.csv")
    assert len(rows) == 600
    assert rows["image_pair_available"].astype(bool).all()
    assert rows["strong_model_label"].isin({"same_cell_supported", "unsupported", "uncertain"}).all()
    assert rows["strong_model_support_score"].between(0, 1).all()
    assert rows["source_image_sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert rows["target_image_sha256"].str.fullmatch(r"[0-9a-f]{64}").all()
    assert rows["evidence_scope"].str.contains("not_external_human_audit").all()
    assert rows["evidence_scope"].str.contains("not_CTC_ground_truth").all()


def test_phase91_replacement_labels_are_human_compatible_but_scoped() -> None:
    repl = pd.read_csv(OUT / "phase91_model_surrogate_human_label_replacement.csv")
    assert len(repl) == 600
    assert {"human_label", "human_confidence", "human_notes", "auditor_id"}.issubset(repl.columns)
    assert repl["human_label"].isin({"same_cell_supported", "unsupported", "uncertain"}).all()
    assert repl["auditor_id"].str.contains("phase91_ctc_image_template_segmentation_surrogate_v1").all()
    assert repl["human_notes"].str.contains("not external human evidence").all()


def test_phase91_gate_ledger_claim_table_and_reproduce() -> None:
    gate = pd.read_csv(OUT / "table_phase91_claim_gate.csv")
    assert len(gate) == 1
    row = gate.iloc[0]
    assert row["positive_evidence"] == "no"
    assert row["status"] == "strong_model_surrogate_annotations_completed_not_human_evidence"
    assert "external human audit success" in row["forbidden_current_claim"]

    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    claim = ledger[ledger["claim_id"].eq("CTC-PHASE91-STRONG-MODEL-ANNOTATION-001")]
    assert len(claim) == 1
    assert claim.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_external_human_audit_success" in claim.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase91 CTC Strong-Model Surrogate Annotation" in claim_table
    assert "not external human audit evidence" in claim_table

    result = subprocess.run(
        ["make", "reproduce-ncs-phase91-ctc-strong-model-annotation"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "strong_model_surrogate_annotations_completed_not_human_evidence" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase91_ctc_strong_model_annotation"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
