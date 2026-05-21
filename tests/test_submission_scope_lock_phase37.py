from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs/milestones/submission_scope_lock_phase37"


def test_phase37_outputs_exist() -> None:
    expected = {
        "table_submission_evidence_hierarchy.csv",
        "table_release_contract_comparator_matrix.csv",
        "table_forbidden_to_allowed_submission_claims.csv",
        "table_two_anchor_manuscript_map.csv",
        "SUBMISSION_SCOPE_LOCK_PHASE37.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in expected if not (MILESTONE / name).exists()]
    assert not missing


def test_only_two_primary_hard_anchors_and_no_pending_primary() -> None:
    evidence = pd.read_csv(MILESTONE / "table_submission_evidence_hierarchy.csv")
    primary = evidence[evidence["manuscript_role"].eq("primary")]
    assert set(primary["evidence_block"]) == {
        "Materials fixed-budget release utility",
        "CTC strict release and artifact consequence",
    }
    assert primary["completed_status"].eq("completed").all()
    assert primary["source_sha256"].astype(str).str.len().ge(40).all()
    forbidden_primary = evidence[
        evidence["evidence_block"].str.contains("A3|External blind audit|discordance|alex|OQMD", case=False, na=False)
        & evidence["manuscript_role"].eq("primary")
    ]
    assert forbidden_primary.empty


def test_external_materials_rows_are_diagnostic_not_validation() -> None:
    evidence = pd.read_csv(MILESTONE / "table_submission_evidence_hierarchy.csv")
    external = evidence[evidence["evidence_block"].str.contains("discordance|MP-Alex|overlay", case=False, na=False)]
    assert not external.empty
    assert set(external["manuscript_role"]) == {"diagnostic"}
    assert external["forbidden_claim"].str.contains("validation|independent", case=False).all()


def test_a3_and_external_audit_are_pending_only() -> None:
    evidence = pd.read_csv(MILESTONE / "table_submission_evidence_hierarchy.csv")
    pending = evidence[evidence["evidence_block"].isin(["A3 MatterGen prospective DFT", "External blind audit packet"])]
    assert len(pending) == 2
    assert set(pending["manuscript_role"]) == {"pending"}
    assert pending["headline_sentence"].str.contains("No headline sentence allowed").all()


def test_release_contract_comparator_marks_only_parc_full_contract() -> None:
    matrix = pd.read_csv(MILESTONE / "table_release_contract_comparator_matrix.csv")
    full = matrix[matrix["solves_full_release_refuse_contract"].astype(bool)]
    assert set(full["method"]) == {"PARC"}
    non_parc = matrix[~matrix["method"].eq("PARC")]
    assert not non_parc["solves_full_release_refuse_contract"].astype(bool).any()
    assert {"raw top-R", "e-BH-style rule", "selective conformal", "nnPU classifier-release"}.issubset(
        set(matrix["method"])
    )


def test_forbidden_claims_cover_reviewer_minimum_fixes() -> None:
    forbidden = pd.read_csv(MILESTONE / "table_forbidden_to_allowed_submission_claims.csv")
    text = " ".join(forbidden["forbidden_claim"].astype(str).str.lower())
    assert "prospective materials discovery" in text
    assert "independent materials validation" in text
    assert "broad success" in text
    assert "external blind audit completed" in text
    assert "fixed-size ranking" in text
