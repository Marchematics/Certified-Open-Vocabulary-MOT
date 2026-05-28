from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE50 = ROOT / "outputs/milestones/ncs_phase50_materials_version_shift_paperization"
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"


def test_phase50_outputs_exist_and_display_plan_has_six_items() -> None:
    expected = {
        "figure_materials_version_shift_inputs.csv",
        "table_materials_t1_hull_shift_summary.csv",
        "table_materials_drift_matrix.csv",
        "table_materials_evidence_status.csv",
        "table_ncs_display_item_plan.csv",
        "ncs_abstract_materials_first_draft.md",
        "NCS_PHASE50_MATERIALS_VERSION_SHIFT_PAPERIZATION.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE50 / name).exists()]
    display = pd.read_csv(PHASE50 / "table_ncs_display_item_plan.csv")
    assert len(display) == 6
    assert set(display["display_item"]) == {f"Figure {i}" for i in range(1, 7)}


def test_phase50_evidence_status_keeps_utility_and_alpha_claims_separate() -> None:
    evidence = pd.read_csv(PHASE50 / "table_materials_evidence_status.csv")
    status = dict(zip(evidence["gate"], evidence["status"]))
    assert status["PARC_release_lower_t1_FTR_than_raw_topK"] == "PASS"
    assert status["stable_to_unstable_drift_not_concentrated_in_PARC"] == "PASS"
    assert status["strict_alpha010_t1_hull_certificate"] == "FAIL"
    assert status["overall_t0_t1_hull_shift_audit"] == "PASS_UTILITY_DRIFT_NO_STRICT_ALPHA_CERTIFICATE"
    text = " ".join(evidence["allowed_manuscript_sentence"].dropna().astype(str)).lower()
    assert "not a strict alpha=0.10 temporal certificate" in text
    assert "not a prospective materials-discovery claim" in text


def test_phase50_figure_inputs_cover_ftr_and_drift_for_k300_k500() -> None:
    fig = pd.read_csv(PHASE50 / "figure_materials_version_shift_inputs.csv")
    assert set(fig["K"]) == {300, 500}
    assert set(fig["arm"]) == {"PARC_release", "raw_topK"}
    assert set(fig["metric"]) == {
        "conservative_t1_false_release_fraction",
        "stable_to_unstable_drift_rate",
    }
    assert fig["value"].between(0, 1).all()
    assert (fig["alpha_reference_line"] == 0.10).all()
    assert set(fig["paper_interpretation"]) == {"version_shift_utility_not_t1_certificate"}


def test_phase50_abstract_is_ncs_sized_and_does_not_overclaim() -> None:
    abstract = (PHASE50 / "ncs_abstract_materials_first_draft.md").read_text(encoding="utf-8")
    assert len(abstract.split()) <= 150
    lower = abstract.lower()
    assert "prospective materials discovery" not in lower
    assert "discovers new stable materials" not in lower
    assert "current-label ftr" in lower


def test_phase51_outputs_exist_and_candidate_audit_is_candidate_level() -> None:
    expected = {
        "table_materials_t1_mlip_candidate_audit.csv",
        "table_materials_t1_false_explanation_summary.csv",
        "figure_materials_t1_false_explanation_inputs.csv",
        "figure_materials_mlip_t1_distribution_inputs.csv",
        "table_materials_chemistry_coverage_diagnostic.csv",
        "table_materials_mlip_availability_status.csv",
        "table_phase51_go_no_go.csv",
        "NCS_PHASE51_MATERIALS_T1_CANDIDATE_EXPLANATION.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    assert not [name for name in expected if not (PHASE51 / name).exists()]
    audit = pd.read_csv(PHASE51 / "table_materials_t1_mlip_candidate_audit.csv")
    assert set(audit["K"]) == {300, 500}
    assert audit[["material_id", "K"]].drop_duplicates().shape[0] == len(audit)
    assert audit["material_id"].nunique() == 1191
    assert {"PARC_release", "raw_only_requested_budget"}.issubset(set(audit["primary_queue_status"]))


def test_phase51_records_model_availability_without_fake_mlip_consensus() -> None:
    availability = pd.read_csv(PHASE51 / "table_materials_mlip_availability_status.csv")
    assert set(availability["model"]).issuperset({"alignn_ff", "cgcnn_ens10", "megnet", "CHGNet", "MACE-MP"})
    assert availability[availability["model"].eq("alignn_ff")]["candidate_level_scores_available"].astype(bool).all()
    unavailable = availability[availability["model"].isin(["CHGNet", "MACE-MP"])]
    assert not unavailable["candidate_level_scores_available"].astype(bool).any()
    assert unavailable["claim_use"].str.contains("must_not_claim_MLIP_consensus", regex=False).all()


def test_phase51_go_no_go_and_false_explanation_scope() -> None:
    gates = pd.read_csv(PHASE51 / "table_phase51_go_no_go.csv")
    assert "NO_GO_FOR_MLIP_CONSENSUS" in set(gates["status"])
    assert (gates[gates["gate"].eq("far_from_hull_alignn_negative_PARC_false_low")]["status"] == "PASS").all()
    false_summary = pd.read_csv(PHASE51 / "table_materials_t1_false_explanation_summary.csv")
    assert not false_summary.empty
    assert set(false_summary["primary_queue_status"]) == {"PARC_release", "raw_only_requested_budget"}
    assert false_summary["fraction_of_false"].between(0, 1).all()


def test_phase50_51_public_safety_text() -> None:
    for milestone in [PHASE50, PHASE51]:
        for path in milestone.rglob("*"):
            if not path.is_file() or path.stat().st_size > 20_000_000:
                continue
            text = path.read_text(encoding="utf-8")
            assert "/home/waas" not in text, path
            assert "/root/" not in text, path
            assert "MP_API_KEY" not in text, path
