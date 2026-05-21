from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "non_a3_experiment_bridge"


def test_non_a3_bridge_outputs_exist() -> None:
    required = {
        "table_non_a3_bridge_status.csv",
        "table_non_a3_bridge_initial_results.csv",
        "NON_A3_EXPERIMENT_BRIDGE_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (MILESTONE / name).exists()]
    assert not missing


def test_non_a3_bridge_keeps_a3_out_of_headline() -> None:
    status = pd.read_csv(MILESTONE / "table_non_a3_bridge_status.csv")
    assert "verified_positive_contamination_sensitivity" in set(status["milestone"])
    assert "materials_selection_conditional_discordance" in set(status["milestone"])
    assert "audit_budget_release_frontier" in set(status["milestone"])
    assert "llm_release_agent_stress_test" in set(status["milestone"])
    assert not status["milestone"].astype(str).str.contains("A3", case=False).any()
    text = (MILESTONE / "NON_A3_EXPERIMENT_BRIDGE_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "A3 remains outside headline-positive evidence" in text


def test_non_a3_bridge_claim_boundaries_are_scoped() -> None:
    status = pd.read_csv(MILESTONE / "table_non_a3_bridge_status.csv")
    joined = " ".join(status["claim_boundary"].astype(str))
    assert "not prospective discovery" in joined
    assert "not positive independent validation" in joined
    assert "not formal guarantees" in joined
    assert "hypothesis B not supported" in joined
    assert "simulated audit only" in joined
    assert "no LLM behavioral evidence" in joined
    audit = status[status["milestone"].eq("external_blind_audit_packet")].iloc[0]
    assert audit["status"] == "packet_completed_labels_pending"


def test_selection_conditional_discordance_is_no_go_in_bridge() -> None:
    status = pd.read_csv(MILESTONE / "table_non_a3_bridge_status.csv")
    row = status[status["milestone"].eq("materials_selection_conditional_discordance")].iloc[0]
    assert row["status"] == "completed_no_go_diagnostic"
    assert row["paper_role"] == "selection_conditional_go_no_go_diagnostic"
    assert "do not promote" in row["claim_boundary"]


def test_llm_agent_bridge_row_is_not_completed_evidence() -> None:
    status = pd.read_csv(MILESTONE / "table_non_a3_bridge_status.csv")
    row = status[status["milestone"].eq("llm_release_agent_stress_test")].iloc[0]
    assert row["status"] == "blocked_missing_credentials_protocol_frozen"
    assert row["paper_role"] == "protocol_scaffold_pending_model_outputs"
    assert "no LLM behavioral evidence" in row["claim_boundary"]
