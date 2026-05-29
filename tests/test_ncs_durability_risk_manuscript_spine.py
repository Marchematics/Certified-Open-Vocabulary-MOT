from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SPINE = ROOT / "outputs" / "milestones" / "ncs_durability_risk_manuscript_spine"
DFT = ROOT / "outputs" / "milestones" / "ncs_phase68_dft_v2_pilot"


def test_dft_v2_numeric_gate_discloses_timing_and_blocks_overclaim():
    text = (DFT / "DFT_V2_NUMERIC_GATE_ADDENDUM.md").read_text()
    assert "9 `completed` VASP jobs and 2 `failed` VASP jobs" in text
    assert "before any `e_above_hull`" in text
    assert "workflow failure fraction among jobs included in the primary" in text
    assert "at most 10%" in text
    assert "completed-only FTR is secondary" in text
    assert "not allowed to wait on DFT v2" in text


def test_dft_v2_gate_table_requires_workflow_and_efficacy_gates():
    table = pd.read_csv(DFT / "table_dft_v2_numeric_gate_addendum.csv")
    assert {"workflow_validity", "efficacy"}.issubset(set(table["gate_type"]))
    assert table["pass_condition"].str.contains("<= 0.10|alpha=0.10", regex=True).any()
    assert table["failure_action"].str.contains("workflow-limited|cannot support", regex=True).any()


def test_finding_first_abstract_scopes_durability_risk_correctly():
    text = (SPINE / "finding_first_abstract_v1.md").read_text()
    assert "AUC 0.544" in text
    assert "AUC 0.844" in text
    assert "22.7% to 12.7%" in text
    assert "risk triage rather than a repaired alpha certificate" in text
    forbidden = ["prospective materials discovery", "t1 alpha control", "DFT v2 validation"]
    for phrase in forbidden:
        assert phrase in text


def test_six_display_plan_decouples_dft_v2_from_completed_core():
    plan = pd.read_csv(SPINE / "six_display_item_plan.csv")
    assert len(plan) == 6
    assert "durability_risk_flagship" in set(plan["role"])
    dft = plan[plan["role"].eq("execution_and_optional_dft")].iloc[0]
    assert dft["status"] == "pending_bonus_arm"
    assert dft["v2_dependency"] == "pending"
    assert "No stable/unstable DFT outcome claim" in dft["overclaim_guardrail"]

