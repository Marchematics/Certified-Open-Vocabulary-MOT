from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "protocol_claim_alignment"


def test_primary_headlines_have_completed_artifacts_hashes_and_sentences() -> None:
    alignment = pd.read_csv(MILESTONE / "table_claim_to_evidence_alignment.csv")
    primary = alignment[alignment["manuscript_role"] == "primary_headline"]

    assert not primary.empty
    assert primary["evidence_completed"].astype(bool).all()
    assert primary["source_sha256"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()
    assert primary["completed_artifact"].astype(str).str.len().gt(0).all()
    assert primary["exact_manuscript_sentence"].fillna("").astype(str).str.len().gt(20).all()

    banned_states = {"diagnostic_only", "failed_gate", "protocol_only", "pending"}
    assert not set(primary["evidence_state"].astype(str)).intersection(banned_states)


def test_diagnostic_and_pending_rows_are_not_headlines() -> None:
    audit = pd.read_csv(MILESTONE / "table_predeclared_endpoint_audit.csv")

    external = audit[audit["result_id"].astype(str).str.contains("OQMD|alex_mp")]
    assert not external.empty
    assert not external["allowed_manuscript_role"].eq("primary_headline").any()
    assert set(external["allowed_manuscript_role"]).issubset({"diagnostic_only", "stress_test"})

    a3 = audit[audit["result_id"].astype(str).str.contains("A3")]
    assert len(a3) == 1
    assert a3["allowed_manuscript_role"].iloc[0] == "pending"
    assert not bool(a3["evidence_completed"].iloc[0])


def test_materials_and_ctc_roles_are_aligned_to_protocol_family() -> None:
    audit = pd.read_csv(MILESTONE / "table_predeclared_endpoint_audit.csv")

    cgcnn = audit[audit["result_id"].eq("materials_cgcnn_ensemble_learned_materials_model_alpha0.1_K100")]
    assert len(cgcnn) == 1
    assert cgcnn["allowed_manuscript_role"].iloc[0] in {"calibration_check", "validity_check"}

    alignn = audit[
        audit["result_id"].isin(
            {
                "materials_alignn_ff_modern_learned_materials_model_alpha0.1_K300",
                "materials_alignn_ff_modern_learned_materials_model_alpha0.1_K500",
            }
        )
    ]
    assert len(alignn) == 2
    assert set(alignn["allowed_manuscript_role"]) == {"primary_headline"}
    assert alignn["protocol_family_member"].astype(bool).all()

    ctc = audit[audit["result_id"].eq("ctc_strict_anchor_alpha010_K300")]
    assert len(ctc) == 1
    assert ctc["allowed_manuscript_role"].iloc[0] == "primary_headline"
    assert bool(ctc["evidence_completed"].iloc[0])

