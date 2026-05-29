from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE67 = ROOT / "outputs/milestones/ncs_phase67_margin_stable_certification"
K_GRID = {10, 15, 20, 25, 50, 75, 100, 150, 200, 300, 500}
MARGIN_GRID = {0.0, 0.01, 0.025, 0.05, 0.075, 0.10, 0.15, 0.20, 0.30, 0.50, 1.00, 1.50, 2.00, 2.50, 3.00}
SUPPORT_MODES = {"margin_10pct_support", "margin_full_calibration_block_support"}


def test_phase67_reports_full_margin_k_support_grid() -> None:
    frontier = pd.read_csv(PHASE67 / "table_margin_stable_certification_frontier.csv")
    assert set(frontier["K"]) == K_GRID
    assert set(frontier["margin_m_eV_atom"].round(6)) == MARGIN_GRID
    assert set(frontier["support_mode"]) == SUPPORT_MODES
    assert len(frontier) == len(K_GRID) * len(MARGIN_GRID) * len(SUPPORT_MODES)
    assert frontier["validity_event"].eq("t0_e_above_hull_le_minus_m").all()
    assert frontier["ranking_score"].eq("t0_margin_descending").all()


def test_phase67_seed_rows_are_complete_and_scoped() -> None:
    seed_rows = pd.read_csv(PHASE67 / "table_margin_stable_seed_rows.csv")
    counts = seed_rows.groupby(["margin_m_eV_atom", "K", "support_mode"])["seed"].nunique()
    assert counts.eq(20).all()
    assert seed_rows["candidate_universe"].eq("frozen_K500_WBM_queue_union").all()
    assert seed_rows["selection_rule"].eq("rank_by_t0_margin_then_SCS_evalue_self_consistency").all()
    assert seed_rows["evidence_scope"].str.contains("t1_used_only_for_post_release_survival_audit").all()
    assert seed_rows["evidence_scope"].str.contains("not_prospective_discovery").all()
    assert seed_rows["evidence_scope"].str.contains("not_DFT_evidence").all()


def test_phase67_headline_positive_requires_full_gate() -> None:
    frontier = pd.read_csv(PHASE67 / "table_margin_stable_certification_frontier.csv")
    gate = pd.read_csv(PHASE67 / "table_margin_stable_gate_audit.csv")
    positive = frontier[frontier["primary_success"].astype(bool)]
    for _, row in positive.iterrows():
        assert row["nonempty_seeds"] >= 18
        assert row["t1_survival_safe_seeds"] >= 18
        assert row["mean_FTR_t1_stability_if_nonempty"] <= 0.10
        gates = gate[
            gate["margin_m_eV_atom"].eq(row["margin_m_eV_atom"])
            & gate["K"].eq(row["K"])
            & gate["support_mode"].eq(row["support_mode"])
            & gate["gate"].eq("constructive_margin_stable_t1_survival_positive")
        ]
        assert len(gates) == 1
        assert gates.iloc[0]["status"] == "PASS"


def test_phase67_readme_forbids_overclaiming() -> None:
    text = (PHASE67 / "README_evidence_scope.md").read_text(encoding="utf-8")
    for phrase in [
        "no prospective materials discovery",
        "no independent DFT evidence",
        "no claim that t0 margin labels are hidden from selection",
        "no post-hoc K or margin selection",
    ]:
        assert phrase in text


def test_phase67_reproduce_target_and_public_bundle() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase67-margin-stable-certification"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase67_margin_stable_certification" in result.stdout
    result = subprocess.run(
        ["python", "scripts/validate_public_bundle.py", "outputs/milestones/ncs_phase67_margin_stable_certification"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
