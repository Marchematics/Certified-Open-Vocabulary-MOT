from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONE = ROOT / "outputs" / "milestones" / "llm_release_agent_stress_test"


def test_llm_release_agent_scaffold_outputs_exist() -> None:
    required = {
        "LLM_RELEASE_AGENT_PREREGISTRATION.md",
        "prompt_templates.yaml",
        "candidate_task_manifest.csv",
        "model_run_manifest.csv",
        "parser_schema.json",
        "credential_status.csv",
        "LLM_RELEASE_AGENT_STRESS_TEST_CLOSEOUT.md",
        "provenance.json",
        "MANIFEST_SHA256.txt",
    }
    missing = [name for name in required if not (MILESTONE / name).exists()]
    assert not missing


def test_llm_release_agent_does_not_record_secrets_or_positive_evidence() -> None:
    credentials = pd.read_csv(MILESTONE / "credential_status.csv")
    assert set(credentials["secret_value_recorded"].astype(str)) == {"False"} or set(
        credentials["secret_value_recorded"].astype(str)
    ) == {"false"}
    runs = pd.read_csv(MILESTONE / "model_run_manifest.csv")
    assert set(runs["positive_evidence_status"]) == {"none_no_llm_outputs_scored"}
    assert not runs["run_status"].astype(str).str.contains("completed_positive", case=False).any()


def test_llm_release_agent_prompts_encode_one_sided_rule() -> None:
    prompts = (MILESTONE / "prompt_templates.yaml").read_text(encoding="utf-8")
    assert "unverified candidates are not negative" in prompts.lower()
    assert "release/refuse" in prompts.lower()
    assert "Do not invent a certificate" in prompts
    closeout = (MILESTONE / "LLM_RELEASE_AGENT_STRESS_TEST_CLOSEOUT.md").read_text(encoding="utf-8")
    assert "No LLM calls were made" in closeout
    assert "cannot support a positive LLM-agent headline claim" in closeout


def test_llm_release_agent_tasks_cover_scientific_domains() -> None:
    tasks = pd.read_csv(MILESTONE / "candidate_task_manifest.csv")
    assert {"biomedical_cell_tracking", "materials_discovery"}.issubset(set(tasks["domain"]))
    assert "not prospective discovery" in " ".join(tasks["claim_boundary"].astype(str))
