from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE66 = ROOT / "outputs/milestones/ncs_phase66_certificate_durability"


def test_historical_drift_tail_is_monotone_in_margin() -> None:
    tail = pd.read_csv(PHASE66 / "table_historical_drift_tail_by_margin.csv")
    tail = tail.sort_values("margin_m_eV_atom")
    assert tail["pi_hat"].between(0, 1).all()
    assert tail["pi_hat"].is_monotonic_decreasing
    assert ((tail["alpha_plus_pi_hat"] - (0.10 + tail["pi_hat"])).abs() < 1e-12).all()
    assert tail["guardrail"].eq("historical_drift_tail_not_future_guarantee").all()


def test_margin_frontier_matches_release_frontier_rows() -> None:
    frontier = pd.read_csv(PHASE66 / "table_parc_r_k_sweep_frontier.csv")
    margin = pd.read_csv(PHASE66 / "table_margin_frontier_by_k.csv")
    keys = ["K", "support_mode"]
    merged = frontier.merge(margin, on=keys, suffixes=("_frontier", "_margin"), validate="one_to_one")
    assert len(merged) == len(frontier)
    assert (merged["nonempty_seeds_frontier"] == merged["nonempty_seeds_margin"]).all()
    assert (merged["safe_seeds_frontier"] == merged["safe_seeds_margin"]).all()
    assert (merged["mean_release_size_frontier"] - merged["mean_release_size_margin"]).abs().max() < 1e-12


def test_margin_figure_has_recertification_and_tail_panels() -> None:
    fig = pd.read_csv(PHASE66 / "figure_margin_durability_frontier_inputs.csv")
    assert {"released_margin_vs_t1_burden", "historical_drift_tail"}.issubset(set(fig["panel"]))
    assert fig["evidence_scope"].str.contains("historical_drift_tail_not_future_guarantee").all()
