from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE56 = ROOT / "outputs/milestones/ncs_phase56_version_shift_accounting"


def test_phase56_outputs_exist() -> None:
    expected = {
        "supplement_version_shift_accounting.tex",
        "table_version_shift_decomposition.csv",
        "figure_version_shift_decomposition_inputs.csv",
        "NCS_PHASE56_VERSION_SHIFT_ACCOUNTING.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in expected if not (PHASE56 / name).exists()]
    assert not missing


def test_version_shift_accounting_identity_is_exact_and_scoped() -> None:
    table = pd.read_csv(PHASE56 / "table_version_shift_decomposition.csv")
    assert set(table["K"]) == {300, 500}
    assert set(table["policy"]) == {"PARC", "raw_topK", "raw_topR"}
    assert table["accounting_residual"].abs().max() < 1e-12
    assert (table["conservative_upper_bound"] >= table["FTR_t1_conservative"]).all()
    assert table["evidence_scope"].str.contains("not_new_alpha_certificate").all()
    assert table["evidence_scope"].str.contains("not_prospective_discovery").all()


def test_parc_t1_burden_is_explained_by_drift_not_new_certificate() -> None:
    table = pd.read_csv(PHASE56 / "table_version_shift_decomposition.csv")
    parc = table[table["policy"].eq("PARC")].set_index("K")
    assert (parc["FTR_t1_conservative"] > 0.10).all()
    assert (parc["stable_to_current_not_stable_rate"] > 0).all()
    assert (parc["not_stable_to_current_stable_rate"] > 0).all()
    tex = (PHASE56 / "supplement_version_shift_accounting.tex").read_text(encoding="utf-8")
    assert "not a new PARC guarantee" in tex
    assert "does not certify" in tex


def test_phase56_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase56-version-shift-accounting"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "wrote outputs/milestones/ncs_phase56_version_shift_accounting" in result.stdout
