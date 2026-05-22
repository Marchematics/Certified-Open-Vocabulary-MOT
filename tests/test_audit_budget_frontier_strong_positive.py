from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "audit_budget_frontier_strong_positive"


def test_strong_positive_outputs_exist() -> None:
    required = {
        "table_strong_positive_gate_audit.csv",
        "table_ctc_primary_seed_rows.csv",
        "table_audit_budget_policy_contrast.csv",
        "table_active_audit_effect_sizes.csv",
        "figure_active_audit_strong_positive_source.csv",
        "ACTIVE_AUDIT_BUDGET_STRONG_POSITIVE_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (MILESTONE / name).exists()]
    assert not missing


def test_only_ctc_k100_is_primary_strong_positive() -> None:
    gate = pd.read_csv(MILESTONE / "table_strong_positive_gate_audit.csv")
    primary = gate[gate["manuscript_role"].eq("primary_strong_positive")]
    assert len(primary) == 1
    row = primary.iloc[0]
    assert row["target_row"] == "ctc_learned_strict_alpha010_K100"
    assert row["domain"] == "biomedical_cell_tracking"
    assert int(row["top_safe_seeds"]) == 20
    assert int(row["top_nonempty_seeds"]) == 20
    assert float(row["top_total_false_releases"]) == 0.0
    assert int(row["random_same_nonempty_seeds"]) == 0
    assert int(row["random_full_safe_seeds"]) == 20
    assert float(row["budget_ratio_vs_random_full"]) == 200.0


def test_ctc_k300_is_support_only_due_to_seed_instability() -> None:
    gate = pd.read_csv(MILESTONE / "table_strong_positive_gate_audit.csv")
    row = gate[gate["target_row"].eq("ctc_learned_strict_alpha010_K300")].iloc[0]
    assert row["manuscript_role"] == "secondary_support_not_primary"
    assert int(row["top_safe_seeds"]) == 19
    assert row["strong_positive_gate"] == "SUPPORT_ONLY"


def test_no_materials_or_a3_claims_enter_strong_positive_package() -> None:
    gate = pd.read_csv(MILESTONE / "table_strong_positive_gate_audit.csv")
    assert not gate["domain"].astype(str).str.contains("materials", case=False).any()
    joined = " ".join(gate["claim_boundary"].astype(str)).lower()
    assert "no materials prospective discovery" in joined
    assert "does not modify a3" in joined
    closeout = (MILESTONE / "ACTIVE_AUDIT_BUDGET_STRONG_POSITIVE_CLOSEOUT.md").read_text(encoding="utf-8").lower()
    assert "materials rows are excluded" in closeout
    assert "not for a3" in closeout


def test_policy_contrast_has_matched_budget_random_control() -> None:
    contrast = pd.read_csv(MILESTONE / "table_audit_budget_policy_contrast.csv")
    k100 = contrast[contrast["target_row"].eq("ctc_learned_strict_alpha010_K100")]
    roles = set(k100["policy_role"])
    assert "efficient_targeted_audit" in roles
    assert "matched_budget_random_control" in roles
    assert "full_random_audit_transition_control" in roles


def test_effect_sizes_are_seed_paired_and_positive() -> None:
    effects = pd.read_csv(MILESTONE / "table_active_audit_effect_sizes.csv")
    k100 = effects[effects["target_row"].eq("ctc_learned_strict_alpha010_K100")].iloc[0]
    assert k100["contrast"] == "top_score_0.005_minus_random_0.005_release_count"
    assert float(k100["mean_delta_release"]) == 100.0
    assert float(k100["bootstrap_CI_low"]) == 100.0
    assert float(k100["bootstrap_CI_high"]) == 100.0
