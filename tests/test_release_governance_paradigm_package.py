from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "release_governance_problem_paradigm"


def test_release_governance_outputs_exist() -> None:
    required = {
        "table_release_governance_paradigm_components.csv",
        "table_release_governance_claim_evidence_map.csv",
        "table_release_governance_figure_blueprint.csv",
        "release_governance_abstract_v2.md",
        "release_governance_maintext_skeleton.md",
        "RELEASE_GOVERNANCE_PARADIGM_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (MILESTONE / name).exists()]
    assert not missing


def test_route2_components_close_the_main_evidence_loop() -> None:
    components = pd.read_csv(MILESTONE / "table_release_governance_paradigm_components.csv")
    expected = {
        "problem_definition",
        "ctc_active_audit_primary_anchor",
        "t1_empirical_baseline_frontier",
        "materials_fixed_budget_frontier",
        "materials_validation_boundary",
        "refusal_attribution_closure",
        "human_audit_uncertainty_boundary",
    }
    assert expected.issubset(set(components["component_id"]))
    primary = components[components["manuscript_role"].eq("primary_headline")]
    assert len(primary) == 1
    assert primary.iloc[0]["component_id"] == "ctc_active_audit_primary_anchor"
    assert "20/20" in primary.iloc[0]["lead_number"]
    assert "200x" in primary.iloc[0]["lead_number"]


def test_claim_map_has_hashes_and_no_materials_overclaim() -> None:
    claims = pd.read_csv(MILESTONE / "table_release_governance_claim_evidence_map.csv")
    assert claims["source_artifact"].astype(str).str.len().gt(0).all()
    assert claims["source_sha256"].astype(str).str.len().eq(64).all()
    text = " ".join(claims["exact_sentence"].astype(str)).lower()
    assert "prospective materials discovery" not in text
    assert "independent validation success" not in text
    primary = claims[claims["support_status"].eq("supported_primary_headline")]
    assert len(primary) == 1
    assert primary.iloc[0]["evidence_component"] == "ctc_active_audit_primary_anchor"


def test_abstract_frames_release_governance_not_generator() -> None:
    abstract = (MILESTONE / "release_governance_abstract_v2.md").read_text(encoding="utf-8").lower()
    assert "release-time governance" in abstract
    assert "one-sided verification" in abstract
    assert "200x" in abstract
    assert "generator" not in abstract
    assert "prospective materials discovery" not in abstract
    assert "external-source and dft-follow-up routes remain outside positive evidence" in abstract


def test_figure_blueprint_prioritizes_ctc_and_t1() -> None:
    figures = pd.read_csv(MILESTONE / "table_release_governance_figure_blueprint.csv")
    roles = set(figures["paper_role"])
    assert "primary_headline" in roles
    assert "clean_acceptance_support" in roles
    primary = figures[figures["paper_role"].eq("primary_headline")].iloc[0]
    assert "audit_budget_frontier_strong_positive" in primary["source_artifact"]
    t1 = figures[figures["paper_role"].eq("clean_acceptance_support")].iloc[0]
    assert "t1_clean_acceptance_package" in t1["source_artifact"]
