#!/usr/bin/env python3
"""Build the non-A3 experiment-bridge closeout tables."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def update_manifest(out_dir: Path) -> None:
    rows = []
    for path in sorted(out_dir.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(out_dir).as_posix()}")
    (out_dir / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/non_a3_experiment_bridge")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    status_rows = [
        {
            "milestone": "materials_label_source_discordance_atlas",
            "priority": "MUST",
            "status": "completed_existing_artifact",
            "source_artifact": "outputs/milestones/materials_label_source_discordance_atlas/table_mp_alex_discordance_atlas_summary.csv",
            "paper_role": "frontier_benchmark_reliability_result",
            "claim_boundary": "not PARC validation; not prospective discovery",
        },
        {
            "milestone": "verified_positive_contamination_sensitivity",
            "priority": "MUST",
            "status": "completed_new_run",
            "source_artifact": "outputs/milestones/verification_assumption_sensitivity/table_verified_positive_contamination_sensitivity_summary.csv",
            "paper_role": "verification_assumption_boundary_diagnostic",
            "claim_boundary": "nonzero contamination rows are not formal guarantees",
        },
        {
            "milestone": "audit_budget_release_frontier",
            "priority": "MUST",
            "status": "completed_simulated_audit_frontier",
            "source_artifact": "outputs/milestones/audit_budget_release_frontier/table_audit_budget_frontier_summary.csv",
            "paper_role": "active_audit_budget_methodological_frontier",
            "claim_boundary": "simulated audit only; not prospective discovery; does not modify A3",
        },
        {
            "milestone": "audit_budget_release_frontier_headline",
            "priority": "MUST",
            "status": "completed_paper_facing_postprocess",
            "source_artifact": "outputs/milestones/audit_budget_release_frontier_headline/table_audit_budget_transition_primary.csv",
            "paper_role": "strict_CTC_headline_plus_materials_boundary",
            "claim_boundary": "CTC strict headline candidate; materials ALIGNN rows are mean-operating boundary secondary rows",
        },
        {
            "milestone": "nmi_reviewer_p0_hardening",
            "priority": "MUST",
            "status": "completed_aggregation_package",
            "source_artifact": "outputs/milestones/nmi_reviewer_p0_hardening/table_p0_reviewer_gap_action_matrix.csv",
            "paper_role": "reviewer_facing_p0_risk_hardening",
            "claim_boundary": "does not create prospective materials evidence; diagnostic rows remain scoped",
        },
        {
            "milestone": "llm_release_agent_stress_test",
            "priority": "MUST",
            "status": "blocked_missing_credentials_protocol_frozen",
            "source_artifact": "outputs/milestones/llm_release_agent_stress_test/model_run_manifest.csv",
            "paper_role": "protocol_scaffold_pending_model_outputs",
            "claim_boundary": "no LLM behavioral evidence until model outputs are run and scored",
        },
        {
            "milestone": "materials_label_discordance_preregistration",
            "priority": "SUPPORT",
            "status": "completed_preregistration_and_minimal_probe",
            "source_artifact": "outputs/milestones/materials_label_discordance_preregistration/table_minimal_discordance_probe.csv",
            "paper_role": "preregistration_probe_not_primary_claim",
            "claim_boundary": "not PARC primary contribution; not prospective discovery",
        },
        {
            "milestone": "materials_selection_conditional_discordance",
            "priority": "SUPPORT",
            "status": "completed_no_go_diagnostic",
            "source_artifact": "outputs/milestones/materials_selection_conditional_discordance/table_selection_conditional_go_no_go.csv",
            "paper_role": "selection_conditional_go_no_go_diagnostic",
            "claim_boundary": "hypothesis B not supported; do not promote as positive validation",
        },
        {
            "milestone": "materials_queue_source_uncertainty_overlay",
            "priority": "NICE",
            "status": "completed_existing_diagnostic",
            "source_artifact": "outputs/milestones/materials_queue_source_uncertainty_overlay/table_materials_queue_overlay_summary.csv",
            "paper_role": "diagnostic_only_source_uncertainty_overlay",
            "claim_boundary": "not positive independent validation",
        },
        {
            "milestone": "external_blind_audit_packet",
            "priority": "NICE",
            "status": "packet_completed_labels_pending",
            "source_artifact": "outputs/milestones/external_blind_audit_packet/table_external_blind_audit_packet_summary.csv",
            "paper_role": "pending_trust_upgrade",
            "claim_boundary": "no positive audit claim until labels/adjudication return",
        },
    ]
    write_csv(out_dir / "table_non_a3_bridge_status.csv", status_rows)

    result_rows = [
        {
            "result": "MP-Alex exact-structure discordance atlas",
            "lead_number": "43139 strict matches; 5060 exact-stability disagreements; rate 0.1173",
            "source_artifact": "outputs/milestones/materials_label_source_discordance_atlas/table_mp_alex_discordance_atlas_summary.csv",
            "claim_scope": "benchmark reliability / source uncertainty",
        },
        {
            "result": "verified-positive contamination grid",
            "lead_number": "1200 seed rows; 60 summary rows; 5 target rows; 6 epsilon values; 2 modes",
            "source_artifact": "outputs/milestones/verification_assumption_sensitivity/table_verified_positive_contamination_sensitivity_summary.csv",
            "claim_scope": "assumption-boundary diagnostic",
        },
        {
            "result": "active audit budget frontier",
            "lead_number": "5 target rows; 20 seeds; 4 audit policies; 7 audit budgets",
            "source_artifact": "outputs/milestones/audit_budget_release_frontier/table_audit_budget_frontier_summary.csv",
            "claim_scope": "completed simulated-audit release/refusal frontier",
        },
        {
            "result": "audit budget strict transition package",
            "lead_number": "CTC K=100/K=300 strict seed-stable transition at 0.5% top-score audit budget; random reaches at 100% in extended grid",
            "source_artifact": "outputs/milestones/audit_budget_release_frontier_headline/table_audit_budget_transition_primary.csv",
            "claim_scope": "paper-facing transition package with materials rows scoped as boundary/secondary",
        },
        {
            "result": "NMI reviewer P0 hardening package",
            "lead_number": "P0 gap/action matrix; audit CP/Wilson/Jeffreys intervals; baseline target-object map; assumption diagnostics map; refusal attribution table",
            "source_artifact": "outputs/milestones/nmi_reviewer_p0_hardening/table_p0_reviewer_gap_action_matrix.csv",
            "claim_scope": "reviewer-facing aggregation; no new prospective materials evidence",
        },
        {
            "result": "LLM release-agent stress test",
            "lead_number": "protocol, prompt templates, parser schema, task manifest, and model run manifest frozen; credentials blocked",
            "source_artifact": "outputs/milestones/llm_release_agent_stress_test/model_run_manifest.csv",
            "claim_scope": "protocol scaffold only; no positive LLM evidence",
        },
        {
            "result": "minimal materials label-discordance probe",
            "lead_number": "matched_n >= 200 and discordance >= 0.40 in the preregistered minimal probe",
            "source_artifact": "outputs/milestones/materials_label_discordance_preregistration/table_minimal_discordance_probe.csv",
            "claim_scope": "preregistration/probe only; not final MP-Alex headline",
        },
        {
            "result": "selection-conditional discordance hypothesis B",
            "lead_number": "n_common 287; baseline discordance 0.1080; models_supporting_rule 0; NO-GO",
            "source_artifact": "outputs/milestones/materials_selection_conditional_discordance/table_selection_conditional_go_no_go.csv",
            "claim_scope": "completed no-go diagnostic",
        },
        {
            "result": "source-uncertainty overlay",
            "lead_number": "ALIGNN K=300/500 exact-match-only overlay summary completed",
            "source_artifact": "outputs/milestones/materials_queue_source_uncertainty_overlay/table_materials_queue_overlay_summary.csv",
            "claim_scope": "diagnostic only; not validation",
        },
        {
            "result": "external blind audit packet",
            "lead_number": "484 blinded items frozen; labels pending",
            "source_artifact": "outputs/milestones/external_blind_audit_packet/table_external_blind_audit_packet_summary.csv",
            "claim_scope": "packet only until labels return",
        },
    ]
    write_csv(out_dir / "table_non_a3_bridge_initial_results.csv", result_rows)

    (out_dir / "NON_A3_EXPERIMENT_BRIDGE_CLOSEOUT.md").write_text(
        "# Non-A3 Experiment Bridge Closeout\n\n"
        "Status: completed initial bridge execution.\n\n"
        "The bridge executed the non-A3 reinforcement plan without modifying A3 selection, "
        "DFT manifests, or DFT run packages. The core new run is the verified-positive "
        "contamination sensitivity grid. Existing completed atlas, label-discordance preregistration, "
        "selection-conditional discordance no-go, overlay, and blind-audit-packet artifacts were "
        "inventoried and scoped. The active audit budget frontier was added as a completed simulated-audit "
        "methodological frontier, while the LLM release-agent stress test was frozen as a credentials-blocked "
        "protocol scaffold with no behavioral evidence claimed.\n\n"
        "## Claim Boundary\n\n"
        "- A3 remains outside headline-positive evidence.\n"
        "- MP-Alex/OQMD remain source-discordance diagnostics, not positive independent validation.\n"
        "- Nonzero verified-positive contamination rows are assumption-violation diagnostics, not formal guarantees.\n"
        "- Audit-budget rows are simulated-audit results over existing labels, not new verification labels.\n"
        "- LLM release-agent rows are protocol scaffolds until model outputs are run and scored.\n"
        "- External blind audit packets remain pending until labels and adjudication return.\n",
        encoding="utf-8",
    )
    provenance = {
        "status": "completed",
        "skill": "experiment-bridge",
        "auto_deploy": "local_cpu",
        "code_review": "local_only_no_subagent_spawned",
        "does_not_modify_A3_selection_or_manifests": True,
        "outputs": [
            "table_non_a3_bridge_status.csv",
            "table_non_a3_bridge_initial_results.csv",
            "NON_A3_EXPERIMENT_BRIDGE_CLOSEOUT.md",
        ],
    }
    (out_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    update_manifest(out_dir)


if __name__ == "__main__":
    main()
