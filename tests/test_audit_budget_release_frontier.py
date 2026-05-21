from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "audit_budget_release_frontier"


def test_audit_budget_frontier_outputs_exist() -> None:
    required = {
        "AUDIT_BUDGET_FRONTIER_PREREGISTRATION.md",
        "audit_policy.yaml",
        "budget_grid.csv",
        "domain_task_manifest.csv",
        "table_audit_budget_frontier_seed_rows.csv",
        "table_audit_budget_frontier_summary.csv",
        "figure_audit_budget_frontier_source.csv",
        "AUDIT_BUDGET_FRONTIER_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (MILESTONE / name).exists()]
    assert not missing


def test_audit_budget_frontier_grid_is_frozen() -> None:
    grid = pd.read_csv(MILESTONE / "budget_grid.csv")
    assert grid["audit_budget_fraction"].round(3).tolist() == [0.0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20]
    seed_rows = pd.read_csv(MILESTONE / "table_audit_budget_frontier_seed_rows.csv")
    assert set(seed_rows["audit_policy"]) == {
        "random",
        "top_score",
        "block_balanced_top_score",
        "diversity_round_robin",
    }
    assert seed_rows["seed"].nunique() == 20
    assert seed_rows["target_row"].nunique() == 5


def test_audit_budget_frontier_uses_only_simulated_audit_claim_scope() -> None:
    summary = pd.read_csv(MILESTONE / "table_audit_budget_frontier_summary.csv")
    assert set(summary["evidence_status"]) == {"completed_simulated_audit_frontier"}
    assert summary["first_safe_release_budget_fraction"].notna().any()
    assert (
        summary.loc[summary["audit_budget_fraction"] > 0, "audit_candidates_inspected_mean"].astype(float) > 0
    ).all()
    text = (MILESTONE / "AUDIT_BUDGET_FRONTIER_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "simulated audit-budget experiment" in text
    assert "not prospective materials discovery" in text
    assert "does not modify A3 selection or DFT manifests" in text


def test_audit_budget_frontier_figure_source_is_plot_ready() -> None:
    figure = pd.read_csv(MILESTONE / "figure_audit_budget_frontier_source.csv")
    required_cols = {
        "domain",
        "target_row",
        "audit_policy",
        "audit_budget_fraction",
        "release_rate",
        "safe_release_rate",
        "mean_release",
        "actual_FTR_mean",
        "alpha",
        "cost_per_true_release_mean",
    }
    assert required_cols.issubset(figure.columns)
    assert (figure["actual_FTR_mean"].astype(float) >= 0).all()
