from pathlib import Path
import subprocess

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE66 = ROOT / "outputs/milestones/ncs_phase66_certificate_durability"
K_GRID = {10, 15, 20, 25, 50, 75, 100, 150, 200, 300, 500}
SUPPORT_MODES = {"t1_10pct_support", "t1_full_calibration_block_support"}


def test_phase66_reports_full_predeclared_k_grid() -> None:
    frontier = pd.read_csv(PHASE66 / "table_parc_r_k_sweep_frontier.csv")
    assert set(frontier["K"]) == K_GRID
    assert set(frontier["support_mode"]) == SUPPORT_MODES
    assert len(frontier) == len(K_GRID) * len(SUPPORT_MODES)
    assert frontier["operational_selector_rule"].str.contains("report_all_K").all()
    assert frontier["evidence_scope"].str.contains("reports_all_predeclared_K_values").all()


def test_phase66_positive_gate_requires_nonempty_safe_seed_stability() -> None:
    frontier = pd.read_csv(PHASE66 / "table_parc_r_k_sweep_frontier.csv")
    gate = pd.read_csv(PHASE66 / "table_parc_r_k_sweep_gate_audit.csv")
    positive = gate[gate["gate"].eq("constructive_current_MP_recertification_positive")]
    assert len(positive) == len(K_GRID) * len(SUPPORT_MODES)
    assert (
        positive["status"].eq("PASS").reset_index(drop=True)
        == frontier["primary_success"].astype(bool).reset_index(drop=True)
    ).all()
    assert not frontier["primary_success"].astype(bool).any()
    assert (frontier["safe_seeds"] < 18).all()


def test_phase66_seed_rows_have_no_hidden_k_selection() -> None:
    seed_rows = pd.read_csv(PHASE66 / "table_parc_r_k_sweep_seed_rows.csv")
    counts = seed_rows.groupby(["K", "support_mode"])["seed"].nunique()
    assert counts.eq(20).all()
    assert seed_rows["candidate_universe"].eq("frozen_K500_WBM_queue_union").all()
    assert seed_rows["evidence_scope"].str.contains("not_full_WBM_recertification").all()
    assert seed_rows["evidence_scope"].str.contains("not_DFT_evidence").all()


def test_phase66_reproduce_target_runs() -> None:
    result = subprocess.run(
        ["make", "reproduce-ncs-phase66-certificate-durability"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ncs_phase66_certificate_durability" in result.stdout
