from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "ncs_phase82_ctc_ai_preannotation_for_human_review"


def test_phase82_outputs_exist_and_scope_is_pending_human_review() -> None:
    expected = {
        "README_evidence_scope.md",
        "AI_ASSISTED_HUMAN_REVIEW_RUBRIC.md",
        "table_ctc_ai_preannotations.csv",
        "ai_assisted_human_review_template.csv",
        "human_review_without_ai_template.csv",
        "table_ctc_ai_preannotation_summary.csv",
        "table_ctc_ai_preannotation_existing_label_diagnostic.csv",
        "table_ctc_ai_preannotation_by_hidden_arm_diagnostic.csv",
        "table_ctc_ai_preannotation_input_audit.csv",
        "table_ctc_ai_preannotation_claim_gate.csv",
        "figure_ctc_ai_preannotation_inputs.csv",
        "MANIFEST_SHA256.txt",
    }
    assert expected.issubset({path.name for path in OUT.iterdir()})
    readme = (OUT / "README_evidence_scope.md").read_text(encoding="utf-8")
    assert "ai_preannotations_completed_human_review_pending" in readme
    assert "review aids only" in readme
    assert "new CTC ground truth" in readme


def test_phase82_preannotations_are_sized_and_geometry_only() -> None:
    pre = pd.read_csv(OUT / "table_ctc_ai_preannotations.csv")
    assert len(pre) == 600
    assert pre["audit_item_id"].is_unique
    assert set(pre["ai_label"]).issubset({"same_cell_supported", "unsupported", "uncertain"})
    assert pre["ai_model_id"].eq("phase82_geometry_only_rule_v1").all()
    assert pre["evidence_scope"].str.contains("ai_assistive_labels_only").all()
    assert pre["evidence_scope"].str.contains("not_completed_positive_evidence").all()
    for col in [
        "center_distance_px",
        "normalized_distance",
        "bbox_area_ratio",
        "frame_gap",
    ]:
        assert col in pre.columns


def test_phase82_human_review_templates_keep_blinding_and_pending_fields() -> None:
    assisted = pd.read_csv(OUT / "ai_assisted_human_review_template.csv")
    unassisted = pd.read_csv(OUT / "human_review_without_ai_template.csv")
    assert len(assisted) == 600
    assert len(unassisted) == 600
    assert assisted["audit_item_id"].tolist() == unassisted["audit_item_id"].tolist()
    for col in ["ai_label", "ai_confidence", "ai_support_score", "ai_reason"]:
        assert col in assisted.columns
    for col in ["human_label", "human_confidence", "human_notes", "human_accepts_ai_label"]:
        assert col in assisted.columns
        assert assisted[col].fillna("").eq("").all()

    forbidden = {
        "intended_arm",
        "source_audit_id",
        "path_id",
        "candidate_rank",
        "score",
        "queue_membership",
        "human_verified_positive_for_calibration",
    }
    assert not forbidden.intersection(assisted.columns)
    assert not {"ai_label", "ai_confidence", "ai_support_score", "ai_reason"}.intersection(unassisted.columns)


def test_phase82_input_audit_and_claim_gate_prevent_positive_claims() -> None:
    audit = pd.read_csv(OUT / "table_ctc_ai_preannotation_input_audit.csv")
    checks = {row["check"]: row for _, row in audit.iterrows()}
    assert checks["ai_input_has_no_arm_score_rank_prior_label_or_GT_columns"]["passes"] == True
    assert checks["human_review_pending"]["passes"] == False
    assert checks["ai_labels_not_positive_evidence"]["passes"] == True

    gate = pd.read_csv(OUT / "table_ctc_ai_preannotation_claim_gate.csv")
    assert len(gate) == 1
    row = gate.iloc[0]
    assert row["status"] == "ai_preannotations_completed_human_review_pending"
    assert row["positive_evidence"] == "no"
    assert "expert microscopy adjudication" in row["forbidden_current_claim"]
    assert "CTC ground truth" in row["forbidden_current_claim"]


def test_phase82_diagnostics_are_not_used_for_ai_generation() -> None:
    diagnostic = pd.read_csv(OUT / "table_ctc_ai_preannotation_existing_label_diagnostic.csv")
    assert len(diagnostic) == 600
    assert diagnostic["diagnostic_scope"].str.contains("not_used_for_AI_generation").all()
    assert diagnostic["diagnostic_scope"].str.contains("not_a_new_human_review_result").all()

    by_arm = pd.read_csv(OUT / "table_ctc_ai_preannotation_by_hidden_arm_diagnostic.csv")
    assert "intended_arm" in by_arm.columns
    assert by_arm["evidence_scope"].str.contains("human_review_pending").all()


def test_phase82_ledger_claim_table_and_artifact_index_guardrails() -> None:
    ledger = pd.read_csv(ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv")
    row = ledger[ledger["claim_id"].eq("CTC-AI-PREANNOTATION-001")]
    assert len(row) == 1
    assert row.iloc[0]["positive_evidence"] == "no"
    assert "do_not_claim_completed_human_review" in row.iloc[0]["overclaim_guardrail"]

    claim_table = (ROOT / "docs/claim_table.md").read_text(encoding="utf-8")
    assert "Phase82 CTC AI Preannotation for Human Review" in claim_table
    assert "not completed human evidence" in claim_table

    artifact_index = pd.read_csv(ROOT / "outputs/artifact_index.csv")
    idx = artifact_index[artifact_index["milestone"].eq("ncs_phase82_ctc_ai_preannotation_for_human_review")]
    assert len(idx) == 1
    assert idx.iloc[0]["evidence_state"] == "ai_preannotations_completed_human_review_pending_not_positive_evidence"


def test_phase82_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase82-ctc-ai-preannotation-for-human-review"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ai_preannotations_completed_human_review_pending" in result.stdout

    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase82_ctc_ai_preannotation_for_human_review"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
