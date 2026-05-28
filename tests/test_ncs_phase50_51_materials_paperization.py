from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE50 = ROOT / "outputs/milestones/ncs_phase50_materials_version_shift_paperization"
PHASE51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"
PHASE49 = ROOT / "outputs/milestones/materials_t0_t1_snapshot_acquisition"


def test_phase50_phase49_exact_audit_tables_exist_and_scope_is_attached() -> None:
    expected = {
        "table_t1_hull_shift_summary.csv",
        "table_t1_ftr_by_k_and_policy.csv",
        "table_t1_stable_to_unstable_drift.csv",
        "table_t1_drift_matrix_by_policy.csv",
        "table_t1_chemical_system_coverage.csv",
        "table_t1_unmatched_or_failed_entries.csv",
        "figure_t1_hull_shift_inputs.csv",
        "README_evidence_scope.md",
    }
    assert not [name for name in expected if not (PHASE49 / name).exists()]
    ftr = pd.read_csv(PHASE49 / "table_t1_ftr_by_k_and_policy.csv")
    assert set(ftr["policy"]) == {"PARC", "raw_topK", "raw_topR"}
    assert set(ftr["K"]) == {300, 500}
    scope = set(ftr["evidence_scope"])
    assert scope == {
        "completed_current_MP_hull_shift_utility_audit;not_strict_alpha_temporal_certificate;not_prospective_discovery;no_t1_label_used_for_selection"
    }
    parc = ftr[ftr["policy"].eq("PARC")].set_index("K")
    raw = ftr[ftr["policy"].eq("raw_topK")].set_index("K")
    assert (raw["ftr_t1"] > parc["ftr_t1"]).all()


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
        "table_materials_candidate_level_t1_mlip_audit.csv",
        "table_materials_t1_false_explanation_summary.csv",
        "table_t1_false_release_decomposition.csv",
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
    alias = pd.read_csv(PHASE51 / "table_materials_candidate_level_t1_mlip_audit.csv")
    required = {
        "candidate_id",
        "structure_hash",
        "policy_status",
        "parc_released",
        "t0_e_above_hull",
        "t1_e_above_hull",
        "drift_type",
        "alignn_ff_score",
        "mlip_consensus_label",
        "is_t1_false_release",
        "failure_explanation_class",
    }
    assert required.issubset(alias.columns)
    assert alias["structure_hash"].astype(str).str.fullmatch(r"[0-9a-f]{64}").all()


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
    decomposition = pd.read_csv(PHASE51 / "table_t1_false_release_decomposition.csv")
    assert {
        "near_hull_boundary",
        "MLIP_disagreement",
        "stable_to_unstable_drift",
        "chemistry_family_cluster",
        "far_from_hull_consensus_negative",
        "unexplained",
    }.issubset(set(decomposition["failure_explanation_class"]))
    assert set(decomposition["assignment_policy"]) == {"overlapping_nonexclusive_diagnostic_categories"}


def test_phase50_51_public_safety_text() -> None:
    for milestone in [PHASE50, PHASE51]:
        for path in milestone.rglob("*"):
            if not path.is_file() or path.stat().st_size > 20_000_000:
                continue
            text = path.read_text(encoding="utf-8")
            assert "/home/waas" not in text, path
            assert "/root/" not in text, path
            assert "MP_API_KEY" not in text, path
