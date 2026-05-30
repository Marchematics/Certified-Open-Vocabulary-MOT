#!/usr/bin/env python3
"""Freeze Phase85 external AI-materials claim-decay audit pilot.

Phase85 is the B-line pilot for a public external-claim audit.  It does not
fetch current database labels and does not report decay evidence.  It freezes
the source list, claim ontology, metrics, GO/NO-GO gates, ambiguity review
schema and publication boundary before any current-reference verdicts are
available.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/b_phase85_external_ai_materials_claim_decay_pilot"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "b_line_external_ai_materials_claim_decay_pilot;"
    "protocol_frozen;"
    "current_reference_verdicts_pending;"
    "not_completed_positive_evidence;"
    "not_A_paper_main_evidence;"
    "not_prospective_discovery;"
    "not_new_DFT_evidence"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_source_registry() -> pd.DataFrame:
    rows = [
        {
            "source_id": "matbench_discovery_wbm",
            "role": "primary_claim_surface",
            "claim_unit": "structure_or_unique_prototype_stability_claim",
            "minimum_pilot_claims": 150,
            "access_mode": "public_download_or_python_api",
            "license_boundary": "verify_at_ingest_before_redistribution",
            "redistribution_policy": "publish_hashes_ids_verdicts_and_rebuild_recipe_not_bulk_raw_structures_by_default",
            "pilot_priority": "high",
            "status": "frozen_source_pending_ingest",
            "evidence_scope": SCOPE,
        },
        {
            "source_id": "gnome_public_stable_materials",
            "role": "primary_claim_surface",
            "claim_unit": "public_ai_stable_structure_claim",
            "minimum_pilot_claims": 150,
            "access_mode": "public_repository_or_materials_project_explorer_with_terms",
            "license_boundary": "noncommercial_or_restricted_terms_must_be_respected",
            "redistribution_policy": "publish_derivative_audit_registry_and_hashes_not_repackaged_raw_data_without_permission",
            "pilot_priority": "high",
            "status": "frozen_source_pending_ingest",
            "evidence_scope": SCOPE,
        },
        {
            "source_id": "alexandria_hull_or_claim_surface",
            "role": "third_claim_or_reference_source",
            "claim_unit": "open_hull_or_structure_level_stability_record",
            "minimum_pilot_claims": 150,
            "access_mode": "public_download_or_optimade",
            "license_boundary": "verify_cc_by_terms_and_required_attribution",
            "redistribution_policy": "publish_derivative_verdicts_and_rebuild_recipe",
            "pilot_priority": "high",
            "status": "frozen_source_pending_ingest",
            "evidence_scope": SCOPE,
        },
        {
            "source_id": "materials_project_current",
            "role": "current_reference",
            "claim_unit": "current_version_summary_or_thermo_reference",
            "minimum_pilot_claims": 0,
            "access_mode": "api_key_required",
            "license_boundary": "record_database_version_and_api_terms",
            "redistribution_policy": "publish_query_manifest_version_hashes_and_derived_verdicts",
            "pilot_priority": "reference",
            "status": "frozen_reference_pending_query",
            "evidence_scope": SCOPE,
        },
        {
            "source_id": "oqmd_current",
            "role": "independent_current_reference",
            "claim_unit": "current_entry_or_phase_diagram_reference",
            "minimum_pilot_claims": 0,
            "access_mode": "public_api_or_optimade",
            "license_boundary": "verify_terms_and_required_attribution",
            "redistribution_policy": "publish_query_manifest_version_hashes_and_derived_verdicts",
            "pilot_priority": "reference",
            "status": "frozen_reference_pending_query",
            "evidence_scope": SCOPE,
        },
    ]
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "table_phase85_source_registry.csv", index=False)

    yaml_lines = ["# Phase85 source registry", f"evidence_scope: {SCOPE}", "sources:"]
    for row in rows:
        yaml_lines.append(f"  - source_id: {row['source_id']}")
        for key in [
            "role",
            "claim_unit",
            "minimum_pilot_claims",
            "access_mode",
            "license_boundary",
            "redistribution_policy",
            "pilot_priority",
            "status",
        ]:
            yaml_lines.append(f"    {key}: {row[key]}")
    (OUT / "source_registry.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")
    return df


def write_claim_ontology() -> None:
    rows = [
        {
            "field": "claim_uid",
            "required": True,
            "definition": "stable deterministic identifier for the public claim row",
            "freeze_stage": "before_current_reference_query",
            "evidence_scope": SCOPE,
        },
        {
            "field": "source_family",
            "required": True,
            "definition": "Matbench Discovery, GNoME, Alexandria, or other frozen source family",
            "freeze_stage": "before_current_reference_query",
            "evidence_scope": SCOPE,
        },
        {
            "field": "original_structure_hash",
            "required": True,
            "definition": "canonicalized hash from the public structure or prototype record",
            "freeze_stage": "before_current_reference_query",
            "evidence_scope": SCOPE,
        },
        {
            "field": "original_claim_text",
            "required": True,
            "definition": "verbatim or normalized public stable/below-hull/novel-stable claim label",
            "freeze_stage": "before_current_reference_query",
            "evidence_scope": SCOPE,
        },
        {
            "field": "original_rank_or_priority",
            "required": False,
            "definition": "public rank, leaderboard priority, top-K membership or confidence bin if available",
            "freeze_stage": "before_current_reference_query",
            "evidence_scope": SCOPE,
        },
        {
            "field": "source_snapshot_date",
            "required": True,
            "definition": "date or version at which the public claim source was captured",
            "freeze_stage": "before_current_reference_query",
            "evidence_scope": SCOPE,
        },
        {
            "field": "current_reference_version",
            "required": True,
            "definition": "MP/OQMD/Alexandria version or query manifest used for the current-reference audit",
            "freeze_stage": "at_current_reference_query",
            "evidence_scope": SCOPE,
        },
    ]
    pd.DataFrame(rows).to_csv(OUT / "table_phase85_claim_ontology.csv", index=False)


def write_metrics_and_gates() -> None:
    metrics = [
        {
            "metric": "SCDR",
            "name": "stable_claim_decay_rate",
            "definition": "fraction of frozen public stable claims that are unstable under current reference",
            "headline_role": "primary",
            "strong_gate": "point_estimate_gt_0.20_and_95ci_low_gt_0.10",
            "weak_gate": "point_estimate_between_0.10_and_0.20",
            "no_go_gate": "95ci_high_lt_0.10",
            "confidence_method": "Clopper-Pearson_or_Jeffreys_per_source;stratified_bootstrap_for_pooled",
            "evidence_scope": SCOPE,
        },
        {
            "metric": "TDB@100",
            "name": "top_decay_burden_at_100",
            "definition": "unstable current-reference fraction among top-100 public claims",
            "headline_role": "primary",
            "strong_gate": "more_than_20_per_100_with_ci_low_gt_10_per_100",
            "weak_gate": "10_to_20_per_100",
            "no_go_gate": "ci_high_lt_10_per_100",
            "confidence_method": "binomial_exact_or_rank_stratified_bootstrap",
            "evidence_scope": SCOPE,
        },
        {
            "metric": "EDMB",
            "name": "excess_decay_over_matched_background",
            "definition": "claim decay rate minus same-source/year/chemical-system/rank-bin matched background drift",
            "headline_role": "primary",
            "strong_gate": "point_estimate_gt_0.10_and_95ci_low_gt_0.03",
            "weak_gate": "point_estimate_0.05_to_0.10_or_ci_low_le_0",
            "no_go_gate": "ci_low_le_0_after_matching",
            "confidence_method": "paired_or_stratified_bootstrap",
            "evidence_scope": SCOPE,
        },
        {
            "metric": "SFR_25meV",
            "name": "severe_flip_rate_25mev",
            "definition": "fraction of frozen stable claims now above hull by more than 25 meV/atom",
            "headline_role": "robustness",
            "strong_gate": "point_estimate_gt_0.15_and_ci_low_gt_0.05",
            "weak_gate": "0.05_to_0.15",
            "no_go_gate": "ci_high_lt_0.05",
            "confidence_method": "binomial_exact_with_10_25_50mev_sensitivity",
            "evidence_scope": SCOPE,
        },
        {
            "metric": "CAR",
            "name": "current_reference_ambiguity_rate",
            "definition": "fraction unresolved after matching/current-reference adjudication",
            "headline_role": "evidence_quality_gate",
            "strong_gate": "lt_0.10_to_0.15",
            "weak_gate": "0.10_to_0.20",
            "no_go_gate": "gt_0.20",
            "confidence_method": "binomial_interval_and_adjudication_sensitivity",
            "evidence_scope": SCOPE,
        },
    ]
    pd.DataFrame(metrics).to_csv(OUT / "table_phase85_metric_definitions.csv", index=False)

    gates = [
        {
            "gate": "source_freeze_before_current_reference",
            "threshold": "source_registry_and_claim_ontology_frozen_before_current_verdicts",
            "current_status": "frozen_protocol_pending_ingest",
            "required_for_strong_claim": True,
            "evidence_scope": SCOPE,
        },
        {
            "gate": "minimum_pilot_size",
            "threshold": "at_least_150_claims_per_primary_source_and_450_total_claims_plus_matched_backgrounds",
            "current_status": "pending_ingest",
            "required_for_strong_claim": True,
            "evidence_scope": SCOPE,
        },
        {
            "gate": "strong_decay_signal",
            "threshold": "SCDR_ci_low_gt_0.10_and_EDMB_ci_low_gt_0.03",
            "current_status": "not_run_pending_current_reference",
            "required_for_strong_claim": True,
            "evidence_scope": SCOPE,
        },
        {
            "gate": "cross_source_replication",
            "threshold": "at_least_two_primary_sources_pass_positive_decay_signal",
            "current_status": "not_run_pending_current_reference",
            "required_for_strong_claim": True,
            "evidence_scope": SCOPE,
        },
        {
            "gate": "ambiguity_control",
            "threshold": "CAR_lt_0.15_for_strong_claim_and_CAR_le_0.20_for_any_headline",
            "current_status": "not_run_pending_adjudication",
            "required_for_strong_claim": True,
            "evidence_scope": SCOPE,
        },
    ]
    pd.DataFrame(gates).to_csv(OUT / "table_phase85_go_no_go_gates.csv", index=False)


def write_sampling_and_schemas() -> None:
    sampling = [
        {
            "stratum": "source_family",
            "rule": "sample_all_primary_sources_with_minimum_150_claims_each_if_available",
            "purpose": "cross_source_replication",
            "status": "frozen_pending_ingest",
            "evidence_scope": SCOPE,
        },
        {
            "stratum": "release_window_or_year",
            "rule": "preserve_public_release_time_bins_when_available",
            "purpose": "avoid_single_snapshot_bias",
            "status": "frozen_pending_ingest",
            "evidence_scope": SCOPE,
        },
        {
            "stratum": "rank_or_confidence_bin",
            "rule": "include_top_100_and_rank_bins_for_background_matching",
            "purpose": "estimate_TDB_and_headline_exposure",
            "status": "frozen_pending_ingest",
            "evidence_scope": SCOPE,
        },
        {
            "stratum": "chemical_system",
            "rule": "match_backgrounds_by_chemical_system_when_possible_else_report_unmatched",
            "purpose": "estimate_excess_decay_over_background",
            "status": "frozen_pending_ingest",
            "evidence_scope": SCOPE,
        },
    ]
    pd.DataFrame(sampling).to_csv(OUT / "table_phase85_sampling_plan.csv", index=False)

    adjudication_columns = [
        "claim_uid",
        "masked_source_id",
        "rank_bin",
        "reduced_formula",
        "original_structure_hash",
        "candidate_structure_preview",
        "matched_current_entry_ids_masked",
        "match_decision",
        "reason_code",
        "confidence",
        "reviewer_notes",
    ]
    adjudication = pd.DataFrame(columns=adjudication_columns)
    adjudication.to_csv(OUT / "phase85_ambiguity_adjudication_template.csv", index=False)

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Phase85 ambiguous match adjudication schema",
        "type": "object",
        "required": ["claim_uid", "match_decision", "reason_code", "confidence"],
        "properties": {
            "claim_uid": {"type": "string"},
            "match_decision": {
                "type": "string",
                "enum": ["same", "distorted_same", "not_same", "uncertain"],
            },
            "reason_code": {
                "type": "string",
                "enum": [
                    "exact_structure_match",
                    "relaxed_or_distorted_match",
                    "composition_only_match",
                    "polymorph_conflict",
                    "missing_current_reference",
                    "insufficient_metadata",
                    "other",
                ],
            },
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "reviewer_notes": {"type": "string"},
        },
        "additionalProperties": True,
    }
    (OUT / "ambiguous_match_adjudication_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")


def write_policy_docs() -> None:
    protocol = f"""# Phase85 External AI-Materials Claim-Decay Audit Pilot

Status: `protocol_frozen_current_reference_verdicts_pending`.

Objective:

Audit whether public AI/materials stability claims remain stable under a
frozen current-reference check, without running new DFT and without changing
the A-paper PARC claim hierarchy.

Primary pilot sources:

- Matbench Discovery / WBM public claim surface;
- GNoME public stable-materials claim surface;
- Alexandria as a third open hull/claim source when available.

Current-reference sources:

- Materials Project current version;
- OQMD current reference.

Primary metrics:

- SCDR: stable-claim decay rate;
- TDB@100: top-100 decay burden;
- EDMB: excess decay over matched background.

Strong pilot gate:

```text
SCDR 95% lower bound > 10%
EDMB 95% lower bound > 3 percentage points
at least two primary sources reproduce a positive decay signal
CAR < 15%
```

No-go gate:

```text
SCDR 95% upper bound < 10%
or leave-one-source-out removes the effect
or CAR > 20%
or structure-level claims cannot be mapped reproducibly
```

Current allowed claim:

Phase85 freezes a B-line external claim-decay audit pilot protocol.  No
current-reference verdicts have been produced.

Forbidden current claims:

- public AI materials claims decay at any particular rate;
- GNoME, Matbench Discovery or Alexandria claims fail current references;
- prospective discovery;
- new DFT evidence;
- independent validation of PARC;
- an A-paper main result.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "PHASE85_EXTERNAL_AI_MATERIALS_CLAIM_DECAY_PROTOCOL.md").write_text(protocol, encoding="utf-8")

    publication = f"""# Phase85 License and Publication Boundary

Phase85 is designed as a derivative audit packet, not a raw-data
redistribution bundle.

Default public release:

- source registry and query manifests;
- public source identifiers or DOI references;
- structure hashes and canonical formulas;
- rank bins, verdicts, ambiguity labels and confidence intervals;
- scripts and environment files;
- rebuild instructions for users with lawful access.

Do not publish by default:

- repackaged raw structure files from sources with non-commercial or restricted
  terms;
- third-party proprietary structures;
- data that requires accepting source-specific terms unless those terms allow
  redistribution.

This artifact does not determine source-specific legal rights.  Ingest scripts
must record license checks before any raw data are redistributed.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "LICENSE_AND_PUBLICATION_BOUNDARY.md").write_text(publication, encoding="utf-8")

    readme = f"""# Phase85 External AI-Materials Claim-Decay Audit Pilot

Status: `protocol_frozen_current_reference_verdicts_pending`.

Phase85 freezes the B-line pilot for auditing public AI/materials stability
claims against frozen current references.  It is not completed evidence, not a
claim-decay result and not part of the A-paper main evidence chain.

Primary sources frozen for the pilot:

- Matbench Discovery / WBM;
- GNoME public stable-materials release;
- Alexandria as third open hull/claim source when available.

Reference sources:

- Materials Project current reference;
- OQMD current reference.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")


def write_timeline_and_claim_gate() -> None:
    timeline = [
        {
            "day_range": "1-3",
            "task": "freeze_source_registry_and_claim_registry",
            "output": "source_registry.yaml; table_phase85_claim_ontology.csv",
            "status": "protocol_frozen",
            "evidence_scope": SCOPE,
        },
        {
            "day_range": "4-7",
            "task": "canonicalization_and_deduplication",
            "output": "future_claim_registry_with_structure_hashes",
            "status": "pending_ingest",
            "evidence_scope": SCOPE,
        },
        {
            "day_range": "8-11",
            "task": "current_reference_query_and_matched_backgrounds",
            "output": "future_current_reference_verdicts",
            "status": "pending_current_reference",
            "evidence_scope": SCOPE,
        },
        {
            "day_range": "12-14",
            "task": "ambiguity_adjudication_and_gate_decision",
            "output": "future_gate_decision",
            "status": "pending_adjudication",
            "evidence_scope": SCOPE,
        },
    ]
    pd.DataFrame(timeline).to_csv(OUT / "table_phase85_pilot_timeline.csv", index=False)

    claim_gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase85_external_ai_materials_claim_decay_pilot",
                "status": "protocol_frozen_current_reference_verdicts_pending",
                "positive_evidence": "no",
                "allowed_current_claim": "Phase85 freezes a B-line external AI-materials claim-decay audit pilot protocol and gates.",
                "forbidden_current_claim": "Do not claim any decay rate, source failure, prospective discovery, new DFT evidence, PARC validation, or A-paper main evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    claim_gate.to_csv(OUT / "table_phase85_claim_gate.csv", index=False)


def upsert_artifact_index() -> None:
    row = {
        "milestone": "b_phase85_external_ai_materials_claim_decay_pilot",
        "path": rel(OUT) + "/",
        "evidence_state": "protocol_frozen_current_reference_verdicts_pending_not_positive_evidence",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/b_phase85_external_ai_materials_claim_decay_pilot",
    }
    index = pd.read_csv(ARTIFACT_INDEX)
    index = index[index["milestone"] != row["milestone"]]
    index = pd.concat([index, pd.DataFrame([row])[index.columns]], ignore_index=True)
    index.to_csv(ARTIFACT_INDEX, index=False)


def upsert_ledger() -> None:
    row = {
        "claim_id": "B-PHASE85-CLAIM-DECAY-PILOT-001",
        "claim_text": "Phase85 freezes a B-line external AI-materials claim-decay audit pilot protocol before current-reference verdicts are produced.",
        "evidence_type": "external_claim_audit_protocol",
        "positive_evidence": "no",
        "scope": "current_reference_verdicts_pending;not_A_paper_main_evidence",
        "artifact_path": rel(OUT / "table_phase85_claim_gate.csv"),
        "hash": sha256_file(OUT / "table_phase85_claim_gate.csv"),
        "validation_command": "make reproduce-b-phase85-external-ai-materials-claim-decay-pilot",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_decay_rate_source_failure_prospective_discovery_new_DFT_PARC_validation_or_A_paper_main_evidence",
    }
    ledger = pd.read_csv(LEDGER)
    ledger = ledger[ledger["claim_id"] != row["claim_id"]]
    ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
    ledger.to_csv(LEDGER, index=False)


def upsert_claim_table() -> None:
    section = """\n## Phase85 External AI-Materials Claim-Decay Audit Pilot\n\nStatus: `protocol_frozen_current_reference_verdicts_pending`.\n\nPhase85 freezes a B-line pilot protocol for auditing whether public AI/materials\nstability claims remain stable under frozen current-reference checks.  Current\nstatus is protocol only: no current-reference verdicts have been produced, no\nsource-specific decay rate is claimed, and this is not A-paper main evidence.\nThe pilot is designed to decide whether B should expand into an independent\nclaim-decay paper or stop without delaying A.\n"""
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    marker = "## Phase85 External AI-Materials Claim-Decay Audit Pilot"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_source_registry()
    write_claim_ontology()
    write_metrics_and_gates()
    write_sampling_and_schemas()
    write_policy_docs()
    write_timeline_and_claim_gate()
    write_manifest(OUT)
    upsert_artifact_index()
    upsert_ledger()
    upsert_claim_table()
    write_root_manifest()
    print(f"[phase85] wrote {OUT.relative_to(ROOT)}")
    print("[phase85] status=protocol_frozen_current_reference_verdicts_pending")


if __name__ == "__main__":
    main()
