from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "nmi_maintext_evidence_package"


def test_nmi_maintext_evidence_outputs_exist() -> None:
    required = {
        "table_headline_evidence_hierarchy.csv",
        "table_maintext_claim_sentences.csv",
        "figure_audit_budget_maintext_source.csv",
        "figure_reviewer_p0_support_source.csv",
        "table_figures_to_artifacts.csv",
        "NMI_MAINTEXT_EVIDENCE_PACKAGE.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (MILESTONE / name).exists()]
    assert not missing


def test_only_ctc_active_audit_is_primary_headline() -> None:
    hierarchy = pd.read_csv(MILESTONE / "table_headline_evidence_hierarchy.csv")
    primary = hierarchy[hierarchy["allowed_manuscript_role"].eq("primary_headline")]
    assert len(primary) == 1
    assert primary.iloc[0]["evidence_block"] == "active_audit_ctc_strong_positive"
    assert "0.5%" in primary.iloc[0]["exact_manuscript_sentence"]
    assert "20/20" in primary.iloc[0]["exact_manuscript_sentence"]
    assert "200x" in primary.iloc[0]["exact_manuscript_sentence"]
    assert primary.iloc[0]["source_sha256"]


def test_materials_prospective_discovery_is_forbidden_not_claimed() -> None:
    claims = pd.read_csv(MILESTONE / "table_maintext_claim_sentences.csv")
    material_gap = claims[claims["evidence_block"].eq("materials_prospective_gap")].iloc[0]
    assert material_gap["status"] == "not_completed_positive_evidence"
    assert material_gap["allowed_manuscript_role"] == "explicit_limitation_or_no_go"
    assert "do not claim prospective materials discovery" not in " ".join(
        claims[claims["allowed_manuscript_role"].eq("primary_headline")]["exact_manuscript_sentence"].astype(str)
    ).lower()


def test_materials_audit_budget_is_boundary_secondary() -> None:
    figure = pd.read_csv(MILESTONE / "figure_audit_budget_maintext_source.csv")
    materials = figure[figure["domain"].eq("materials_discovery")]
    assert not materials.empty
    assert set(materials["role"]) == {"boundary_secondary"}
    assert (materials["alpha_violation_rate"].astype(float) > 0).all()


def test_ctc_k100_is_strong_positive_figure_row() -> None:
    figure = pd.read_csv(MILESTONE / "figure_audit_budget_maintext_source.csv")
    row = figure[figure["target_row"].eq("ctc_learned_strict_alpha010_K100")].iloc[0]
    assert row["role"] == "primary_strong_positive"
    assert float(row["top_score_budget"]) == 0.005
    assert row["efficiency_gain"] == "200.0x"
    assert float(row["actual_FTR"]) == 0.0


def test_all_claim_sentences_have_source_hashes() -> None:
    claims = pd.read_csv(MILESTONE / "table_maintext_claim_sentences.csv")
    assert claims["source_artifact"].astype(str).str.len().gt(0).all()
    assert claims["source_sha256"].astype(str).str.len().eq(64).all()


def test_t1_baseline_frontier_is_claim_source() -> None:
    claims = pd.read_csv(MILESTONE / "table_maintext_claim_sentences.csv")
    row = claims[claims["evidence_block"].eq("baseline_target_object_frontier")].iloc[0]
    assert row["status"] == "completed_T1_empirical_baseline_frontier"
    assert "T1 empirical baseline frontier" in row["exact_manuscript_sentence"]
    assert "t1_clean_acceptance_package" in row["source_artifact"]
    figures = pd.read_csv(MILESTONE / "table_figures_to_artifacts.csv")
    assert "t1_empirical_baseline_frontier" in set(figures["figure_or_table"])
