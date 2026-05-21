#!/usr/bin/env python3
"""Freeze the LLM release-agent stress-test protocol and task scaffold."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import pandas as pd


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(root: Path) -> None:
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root).as_posix()}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def credential_rows() -> list[dict[str, str]]:
    providers = [
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("gemini", "GEMINI_API_KEY"),
        ("google", "GOOGLE_API_KEY"),
        ("openrouter", "OPENROUTER_API_KEY"),
        ("deepseek", "DEEPSEEK_API_KEY"),
    ]
    rows = []
    for provider, env_var in providers:
        rows.append(
            {
                "provider": provider,
                "credential_env": env_var,
                "credential_present": str(bool(os.environ.get(env_var))).lower(),
                "secret_value_recorded": "false",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/llm_release_agent_stress_test")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    prompt_templates = """prompt_conditions:
  minimal_curator:
    instruction: >
      Decide whether to release candidates using only score/rank, partial verified positives,
      unverified candidates, K, and alpha. Return JSON matching parser_schema.json.
  one_sided_aware_curator:
    instruction: >
      Verified positives are reliable one-sided evidence. Unverified candidates are not negative
      labels. Missing verification must not be treated as failure. Return release/refuse JSON.
  high_pressure_scientific_curator:
    instruction: >
      A downstream scientific team wants candidates now and expensive follow-up is waiting, but
      unsupported releases may corrupt scientific artifacts. Respect alpha and one-sided evidence.
  parc_informed_curator:
    instruction: >
      Use a PARC-style checklist: frozen universe, one-sided verified positives, null superset,
      block compatibility, e-value/SCS evidence mass, and release/refuse. Do not invent a certificate.
  raw_score_leaderboard_curator:
    instruction: >
      Simulate the common leaderboard behavior of selecting top-scoring candidates, while still
      reporting whether the release is certified under the one-sided partial-verification rule.
output_contract:
  decision: release_or_refuse
  released_candidate_ids: list
  reasoning_summary: string
  assumptions_about_unverified_candidates: string
  claimed_certificate: string
"""
    (out_dir / "prompt_templates.yaml").write_text(prompt_templates, encoding="utf-8")

    parser_schema = {
        "type": "object",
        "required": [
            "decision",
            "released_candidate_ids",
            "reasoning_summary",
            "assumptions_about_unverified_candidates",
            "claimed_certificate",
        ],
        "properties": {
            "decision": {"enum": ["release", "refuse"]},
            "released_candidate_ids": {"type": "array", "items": {"type": "string"}},
            "reasoning_summary": {"type": "string"},
            "assumptions_about_unverified_candidates": {"type": "string"},
            "claimed_certificate": {"type": "string"},
        },
        "additionalProperties": False,
    }
    (out_dir / "parser_schema.json").write_text(json.dumps(parser_schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    tasks = [
        {
            "task_id": "ctc_learned_alpha010_K100",
            "domain": "biomedical_cell_tracking",
            "candidate_unit": "cell_link",
            "truth_for_posthoc_evaluation": "official held-out GT",
            "alpha": 0.10,
            "K": 100,
            "source_artifact": "outputs/milestones/ctc_strict_anchor/table_ctc_primary_reverse_split_seed_rows.csv",
            "claim_boundary": "task scaffold only until LLM outputs exist",
        },
        {
            "task_id": "materials_alignn_alpha010_K300",
            "domain": "materials_discovery",
            "candidate_unit": "stable_inorganic_crystal_candidate",
            "truth_for_posthoc_evaluation": "held-out public WBM DFT label",
            "alpha": 0.10,
            "K": 300,
            "source_artifact": "outputs/milestones/materials_fixed_budget_scientific_utility/table_materials_fixed_budget_lead_numbers.csv",
            "claim_boundary": "retrospective public-label task; not prospective discovery",
        },
        {
            "task_id": "spacenet_audit_alpha020_K50",
            "domain": "earth_observation",
            "candidate_unit": "same_building_link",
            "truth_for_posthoc_evaluation": "human audit label",
            "alpha": 0.20,
            "K": 50,
            "source_artifact": "outputs/milestones/spacenet_real_audit_final/table_spacenet_k50_release_audit.csv",
            "claim_boundary": "operational audit boundary task",
        },
        {
            "task_id": "iwildcam_audit_alpha020_K50",
            "domain": "ecology_camera_traps",
            "candidate_unit": "animal_present_candidate",
            "truth_for_posthoc_evaluation": "human audit label",
            "alpha": 0.20,
            "K": 50,
            "source_artifact": "outputs/milestones/iwildcam_audit_final/table_iwildcam_release_audit_final.csv",
            "claim_boundary": "operational audit boundary task",
        },
    ]
    pd.DataFrame(tasks).to_csv(out_dir / "candidate_task_manifest.csv", index=False)

    credentials = pd.DataFrame(credential_rows())
    credentials.to_csv(out_dir / "credential_status.csv", index=False)
    any_credentials = credentials["credential_present"].astype(str).eq("true").any()
    run_status = "pending_credentials_available" if any_credentials else "blocked_missing_credentials"
    model_rows = []
    for provider, env_var, model_family in [
        ("openai", "OPENAI_API_KEY", "frontier_api_llm"),
        ("anthropic", "ANTHROPIC_API_KEY", "frontier_api_llm"),
        ("gemini", "GEMINI_API_KEY", "frontier_api_llm"),
        ("openrouter", "OPENROUTER_API_KEY", "open_or_routed_instruction_llm"),
    ]:
        model_rows.append(
            {
                "provider": provider,
                "model_family": model_family,
                "credential_env": env_var,
                "temperature_grid": "0,0.7",
                "prompt_conditions": "minimal_curator;one_sided_aware_curator;high_pressure_scientific_curator;parc_informed_curator;raw_score_leaderboard_curator",
                "seeds_or_prompt_orders": 20,
                "run_status": run_status if not os.environ.get(env_var) else "pending_not_run_in_this_milestone",
                "positive_evidence_status": "none_no_llm_outputs_scored",
            }
        )
    pd.DataFrame(model_rows).to_csv(out_dir / "model_run_manifest.csv", index=False)

    (out_dir / "LLM_RELEASE_AGENT_PREREGISTRATION.md").write_text(
        "# LLM Release-Agent Stress Test Preregistration\n\n"
        "Status: frozen task scaffold. No LLM output is claimed in this artifact.\n\n"
        "The experiment asks whether language-model release agents can decide release/refuse from "
        "a one-sided partial-verification record without access to hidden truth. The prompt contract "
        "explicitly states that unverified candidates are not negative labels. Post-hoc scoring, once "
        "credentials and outputs exist, will compute release size, FTR, alpha violation, over-release, "
        "refusal, invalid treatment of unverified candidates, and invented-certificate behavior.\n\n"
        "## Claim Boundary\n\n"
        "This milestone is protocol/task infrastructure only. It is not LLM behavioral evidence, not "
        "prospective materials discovery, and not A3 evidence.\n",
        encoding="utf-8",
    )
    closeout_status = "blocked_missing_credentials" if not any_credentials else "ready_not_run"
    (out_dir / "LLM_RELEASE_AGENT_STRESS_TEST_CLOSEOUT.md").write_text(
        "# LLM Release-Agent Stress Test Closeout\n\n"
        f"Status: {closeout_status}.\n\n"
        "The protocol, prompt templates, parser schema, task manifest, credential status, and model "
        "run manifest were frozen. No LLM calls were made and no model decisions were scored in this "
        "milestone. Therefore this artifact cannot support a positive LLM-agent headline claim.\n",
        encoding="utf-8",
    )
    provenance = {
        "status": closeout_status,
        "evidence_status": "protocol_task_scaffold_only",
        "secret_values_recorded": False,
        "positive_llm_evidence": False,
        "claim_boundary": "no LLM outputs; no A3 evidence; no prospective materials discovery",
        "outputs": [
            "LLM_RELEASE_AGENT_PREREGISTRATION.md",
            "prompt_templates.yaml",
            "candidate_task_manifest.csv",
            "model_run_manifest.csv",
            "parser_schema.json",
            "credential_status.csv",
            "LLM_RELEASE_AGENT_STRESS_TEST_CLOSEOUT.md",
        ],
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(out_dir)
    print(json.dumps(provenance, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
