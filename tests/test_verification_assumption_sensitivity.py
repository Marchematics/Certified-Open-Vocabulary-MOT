from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "verification_assumption_sensitivity"


def test_verification_assumption_sensitivity_outputs_exist() -> None:
    required = {
        "table_verified_positive_contamination_sensitivity_seed_rows.csv",
        "table_verified_positive_contamination_sensitivity_summary.csv",
        "figure_verified_positive_contamination_sensitivity_source.csv",
        "VERIFICATION_ASSUMPTION_SENSITIVITY_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (MILESTONE / name).exists()]
    assert not missing


def test_contamination_grid_and_target_rows_are_complete() -> None:
    summary = pd.read_csv(MILESTONE / "table_verified_positive_contamination_sensitivity_summary.csv")
    assert set(summary["epsilon_false_verified_positive"].round(3)) == {0.0, 0.005, 0.01, 0.02, 0.05, 0.10}
    assert set(summary["contamination_mode"]) == {"random", "adversarial"}
    assert {
        "ctc_learned_strict_alpha010_K100",
        "ctc_learned_strict_alpha010_K300",
        "materials_cgcnn_exact_stable_alpha010_K100",
        "materials_alignn_exact_stable_alpha010_K300",
        "materials_alignn_exact_stable_alpha010_K500",
    }.issubset(set(summary["target_row"]))
    assert summary["seeds"].eq(20).all()


def test_nonzero_contamination_is_not_formal_guarantee() -> None:
    summary = pd.read_csv(MILESTONE / "table_verified_positive_contamination_sensitivity_summary.csv")
    nonzero = summary[summary["epsilon_false_verified_positive"].astype(float) > 0]
    assert not nonzero.empty
    assert set(nonzero["evidence_status"]) == {
        "assumption_violation_sensitivity_not_formal_guarantee"
    }
    assert set(nonzero["paper_role"]) == {"verification_assumption_boundary_diagnostic"}
    text = (MILESTONE / "VERIFICATION_ASSUMPTION_SENSITIVITY_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "not formal PARC guarantees" in text
    assert "prospective discovery" in text


def test_adversarial_contamination_can_expose_boundary() -> None:
    summary = pd.read_csv(MILESTONE / "table_verified_positive_contamination_sensitivity_summary.csv")
    adversarial = summary[
        summary["contamination_mode"].eq("adversarial")
        & (summary["epsilon_false_verified_positive"].astype(float) > 0)
    ]
    assert (adversarial["false_candidates_injected_as_verified_positive_mean"].astype(float) > 0).all()
    materials = adversarial[adversarial["domain"].eq("materials_discovery")]
    assert (materials["actual_FTR_max"].astype(float) > materials["alpha"].astype(float)).any()


def test_figure_source_matches_summary_claim_scope() -> None:
    summary = pd.read_csv(MILESTONE / "table_verified_positive_contamination_sensitivity_summary.csv")
    fig = pd.read_csv(MILESTONE / "figure_verified_positive_contamination_sensitivity_source.csv")
    assert len(fig) == len(summary)
    assert set(fig["evidence_status"]).issubset(set(summary["evidence_status"]))
    assert {
        "release_rate",
        "mean_release",
        "actual_FTR_mean",
        "violation_rate",
        "best_mass_ratio_mean",
    }.issubset(fig.columns)
