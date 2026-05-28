from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE66 = ROOT / "outputs/milestones/ncs_phase66_certificate_durability"


def test_phase66_required_outputs_exist() -> None:
    expected = {
        "supplement_certificate_durability.tex",
        "table_parc_r_k_sweep_frontier.csv",
        "table_parc_r_k_sweep_bootstrap.csv",
        "table_version_shift_decomposition_by_k.csv",
        "table_margin_frontier_by_k.csv",
        "table_historical_drift_tail_by_margin.csv",
        "figure_recertification_frontier_inputs.csv",
        "figure_margin_durability_frontier_inputs.csv",
        "README_evidence_scope.md",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in expected if not (PHASE66 / name).exists()]
    assert not missing


def test_version_shift_accounting_identity_by_seed() -> None:
    table = pd.read_csv(PHASE66 / "table_version_shift_decomposition_by_k.csv")
    assert len(table) == 11 * 2 * 20
    assert table["accounting_residual"].abs().max() < 1e-12
    assert (table["conservative_upper_bound"] + 1e-12 >= table["FTR_t1"]).all()
    assert table["evidence_scope"].str.contains("not_strict_t1_alpha_certificate").all()
    assert table["evidence_scope"].str.contains("not_prospective_discovery").all()


def test_supplement_names_accounting_as_proposition_not_deep_theorem() -> None:
    tex = (PHASE66 / "supplement_certificate_durability.tex").read_text(encoding="utf-8")
    assert "Proposition X.1: exact version-shift accounting" in tex
    assert "Theorem X.5: versioned recertification" in tex
    assert "not prospective" in tex or "not a" in tex
