from __future__ import annotations

import csv
import hashlib
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones" / "materials_label_discordance_preregistration"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def manifest_for(directory: Path) -> str:
    lines: list[str] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST_SHA256.txt":
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(directory)}")
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mp_env_present = "true" if os.environ.get("MP_API_KEY") else "false"
    mp_gate_status = "credential_env_present_not_validated" if mp_env_present == "true" else "blocked_missing_MP_API_KEY_env"

    source_rows = [
        {
            "source": "Materials Project",
            "role": "candidate public DFT label source",
            "minimum_use": "primary_pair_source_A_or_B",
            "access_requirement": "MP_API_KEY environment variable; never stored in repository",
            "snapshot_requirement": "record database version, query date, API package version, row count and SHA256 of exported public-safe index",
            "current_access_status": mp_gate_status,
            "credential_present_in_environment": mp_env_present,
            "secret_policy": "do_not_commit_api_keys_or_raw_credentials",
            "go_no_go_role": "hard_gate",
        },
        {
            "source": "Alexandria",
            "role": "candidate independent DFT label source",
            "minimum_use": "primary_pair_source_A_or_B",
            "access_requirement": "public downloadable snapshot or pre-existing exact-structure join table",
            "snapshot_requirement": "record release/version URL or DOI, row count, structure id hash and label-field hash",
            "current_access_status": "available_prior_exact_match_diagnostic_exists_but_new_snapshot_not_yet_frozen",
            "credential_present_in_environment": "not_required",
            "secret_policy": "public_snapshot_only",
            "go_no_go_role": "hard_gate",
        },
        {
            "source": "OQMD",
            "role": "candidate independent DFT label source",
            "minimum_use": "secondary_pair_or_replication_source",
            "access_requirement": "public query/download path; exact-structure matches only for primary discordance",
            "snapshot_requirement": "record query date, row count, exact-match count and label-field hash",
            "current_access_status": "available_prior_low_coverage_diagnostic_exists",
            "credential_present_in_environment": "not_required_or_site_dependent",
            "secret_policy": "public_snapshot_only",
            "go_no_go_role": "replication_gate",
        },
        {
            "source": "Matbench Discovery / WBM",
            "role": "benchmark ecosystem anchor and candidate universe reference",
            "minimum_use": "required_context_source",
            "access_requirement": "public versioned WBM/Matbench artifacts or existing repository snapshot",
            "snapshot_requirement": "record DOI/version, unique prototype count, label hash and score-file hash",
            "current_access_status": "existing_repository_materials_artifacts_available; external download path still to be frozen",
            "credential_present_in_environment": "not_required",
            "secret_policy": "public_snapshot_only",
            "go_no_go_role": "hard_context_gate",
        },
        {
            "source": "GNoME / AFLOW / NOMAD",
            "role": "optional breadth or exclusion stress source",
            "minimum_use": "not_required_for_week_one_go_no_go",
            "access_requirement": "public snapshot if used",
            "snapshot_requirement": "record source-specific license and version metadata",
            "current_access_status": "optional_not_yet_checked",
            "credential_present_in_environment": "not_required_or_site_dependent",
            "secret_policy": "public_snapshot_only",
            "go_no_go_role": "optional_extension",
        },
    ]
    write_csv(OUT / "table_source_access_inventory.csv", source_rows)

    matching_rows = [
        {
            "rule_id": "T0_exact_structure_match",
            "primary_or_sensitivity": "primary",
            "match_basis": "same reduced composition plus StructureMatcher high-confidence match",
            "parameters": "ltol=0.2; stol=0.3; angle_tol=5; primitive_cell=True; scale=True; attempt_supercell=True",
            "allowed_in_primary_discordance": "true",
            "formula_only_allowed": "false",
            "failure_action": "if exact/high-confidence matched count < 200 or pair coverage < 20%, declare source pair inconclusive",
        },
        {
            "rule_id": "T1_formula_only_tag",
            "primary_or_sensitivity": "tag_only",
            "match_basis": "reduced formula / chemical system / anonymous formula",
            "parameters": "exact string normalization only",
            "allowed_in_primary_discordance": "false",
            "formula_only_allowed": "tag_only",
            "failure_action": "never use formula-only rows to estimate headline discordance",
        },
        {
            "rule_id": "T2_label_definition",
            "primary_or_sensitivity": "primary",
            "match_basis": "binary exact-stable label",
            "parameters": "stable if e_above_hull <= 0 eV/atom; missing or failed hull excluded from primary denominator and reported",
            "allowed_in_primary_discordance": "true",
            "formula_only_allowed": "false",
            "failure_action": "if hull definitions cannot be mapped to e_above_hull, use source only as inventory, not as primary pair",
        },
        {
            "rule_id": "T3_near_hull_sensitivity",
            "primary_or_sensitivity": "sensitivity",
            "match_basis": "same exact/high-confidence structure matches as T0",
            "parameters": "25 meV/atom tolerance; margin-excluded band; far-from-hull subset",
            "allowed_in_primary_discordance": "false",
            "formula_only_allowed": "false",
            "failure_action": "report as localization of discordance only after primary exact-stable endpoint is computed",
        },
    ]
    write_csv(OUT / "table_matching_rules_preregistered.csv", matching_rows)

    endpoint_rows = [
        {
            "endpoint_id": "E1_pairwise_binary_discordance",
            "question": "Do two independent public DFT sources disagree on the binary exact-stability label for exactly matched structures?",
            "inputs": "two frozen source snapshots; exact/high-confidence structure match table; stable/unstable labels",
            "metric": "mean indicator(label_A != label_B) on primary matched denominator",
            "pass_gate": "discordance >= 0.40 with matched_n >= 200 and pair_coverage >= 0.20",
            "no_go_gate": "discordance <= 0.10 or matched_n < 200 or pair_coverage < 0.20",
            "continue_if_boundary": "0.10 < discordance < 0.40 requires third-source replication before paper launch",
            "stop_action_if_fail": "stop the discordance-paper route and treat prior alex-mp observation as source-specific diagnostic",
        },
        {
            "endpoint_id": "E2_near_hull_localization",
            "question": "Is discordance concentrated near the hull or does it persist far from the decision boundary?",
            "inputs": "same primary matches plus source-specific e_above_hull values",
            "metric": "discordance by near-hull band, far-from-hull band, chemistry family and source pair",
            "pass_gate": "localization table identifies interpretable concentration or persistence pattern",
            "no_go_gate": "insufficient e_above_hull metadata for both sources",
            "continue_if_boundary": "report as descriptive only; do not use for launch decision",
            "stop_action_if_fail": "omit localization from first-week go/no-go; do not block E1/E3",
        },
        {
            "endpoint_id": "E3_model_ranking_flip",
            "question": "Does the source choice change Matbench-style model conclusions?",
            "inputs": "2-3 frozen public model prediction tables and the same matched structures under source A and B labels",
            "metric": "rank order change, Kendall tau / Spearman change, and top-model identity under each label source",
            "pass_gate": "top model changes or at least one adjacent leaderboard ordering flips with absolute metric delta >= 0.05",
            "no_go_gate": "rankings stable and all metric deltas < 0.02 across the candidate model set",
            "continue_if_boundary": "if ranking stable but discovered-count flips strongly, continue via E4",
            "stop_action_if_fail": "do not claim NMI-level downstream consequence from discordance alone",
        },
        {
            "endpoint_id": "E4_discovered_stable_count_delta",
            "question": "Does source choice change how many materials are called discovered/stable at a fixed model threshold?",
            "inputs": "same frozen predictions; exact-matched labels from two sources",
            "metric": "absolute and relative difference in stable/discovered count at the preregistered threshold",
            "pass_gate": "relative count difference >= 25% or absolute difference >= 50 structures on the matched denominator",
            "no_go_gate": "relative count difference < 10% and no ranking flip",
            "continue_if_boundary": "combine with E3 and E5 for overall downstream-consequence decision",
            "stop_action_if_fail": "downgrade to methods-note or supplemental diagnostic",
        },
        {
            "endpoint_id": "E5_release_decision_flip_probe",
            "question": "Does a release/certificate probe expose source-conditional decisions?",
            "inputs": "PARC or thresholded-release probe evaluated separately under source A and B labels",
            "metric": "release/refusal decision flip or FTR budget flip at predeclared alpha/K",
            "pass_gate": "at least one preregistered operating point flips between release-within-budget and fail/refuse",
            "no_go_gate": "no decision flip and E3/E4 also stable",
            "continue_if_boundary": "use as consequence probe only after E1 passes",
            "stop_action_if_fail": "PARC remains background probe, not paper evidence",
        },
    ]
    write_csv(OUT / "table_downstream_conclusion_flip_endpoints.csv", endpoint_rows)

    gate_rows = [
        {
            "gate": "Step0_data_access",
            "duration_target": "1-2 days",
            "minimum_pass": "two legally accessible source snapshots including Materials Project or Alexandria plus WBM/Matbench context",
            "current_status": "not_passed_until_MP_API_or_alternative_second_source_snapshot_is_validated",
            "if_pass": "freeze snapshots and run E1 on exact/high-confidence matches",
            "if_fail": "stop discordance paper and return effort to PARC methods submission",
        },
        {
            "gate": "Step1_minimal_discordance_probe",
            "duration_target": "2-3 days",
            "minimum_pass": "primary pairwise binary discordance >= 0.40 on matched_n >= 200 exact/high-confidence structures",
            "current_status": "pending",
            "if_pass": "proceed to downstream conclusion-flip probes",
            "if_fail": "treat previous 0.522 alex-mp result as source-specific artifact, not NMI nugget",
        },
        {
            "gate": "Step2_downstream_conclusion_flip",
            "duration_target": "3-5 days",
            "minimum_pass": "ranking flip, discovered-count delta, or release-decision flip under source A vs B",
            "current_status": "pending",
            "if_pass": "launch full discordance paper pipeline",
            "if_fail": "downgrade to interesting diagnostic; do not write NMI article",
        },
    ]
    write_csv(OUT / "table_go_no_go_gates.csv", gate_rows)

    protocol_yaml = """trial_name: materials_label_discordance_go_no_go
paper_role: new_independent_discordance_paper_preregistration
primary_contribution: public_DFT_stability_label_reproducibility_and_downstream_consequence
parc_role: optional_release_refuse_probe_only
secret_policy:
  api_keys: never_commit
  materials_project_key: read_from_MP_API_KEY_environment_variable_only
  raw_credentials_in_artifacts: forbidden
week_one_gates:
  step0_data_access:
    pass: legally_accessible_two_source_snapshots
    fail_action: stop_discordance_paper_route
  step1_minimal_discordance_probe:
    primary_threshold: discordance_ge_0.40
    no_go_threshold: discordance_le_0.10
    matched_n_floor: 200
    pair_coverage_floor: 0.20
  step2_downstream_conclusion_flip:
    pass_any:
      - model_ranking_flip
      - discovered_stable_count_delta
      - release_decision_flip_probe
matching:
  primary: exact_or_high_confidence_structure_match
  formula_only: tag_only_never_primary
  structure_matcher:
    ltol: 0.2
    stol: 0.3
    angle_tol: 5
    primitive_cell: true
    scale: true
    attempt_supercell: true
labels:
  primary_binary_stable: e_above_hull_le_0_eV_per_atom
  sensitivity:
    - tolerance_25_meV
    - margin_excluded
    - far_from_hull
claim_boundaries:
  forbidden:
    - PARC_as_primary_contribution
    - formula_only_discordance_headline
    - external_databases_as_interchangeable_ground_truth
    - NMI_discordance_claim_before_step0_1_2_pass
"""
    write_text(OUT / "protocol_discordance_study.yaml", protocol_yaml)

    access_md = f"""# Data Access Go/No-Go

This milestone preregisters the first week of the materials-label
discordance paper route. It does not claim a new result. It decides whether
the route is worth launching.

## Secret Handling

Materials Project credentials are read only from `MP_API_KEY` in the local
environment. No API key, token, cookie, raw credential or private response
payload may be written to this repository, to any manifest, or to a paper
artifact.

Current environment credential presence recorded by the builder:
`MP_API_KEY present = {mp_env_present}`.

Because the key has been shared in conversation, rotate it before using this
milestone for a public or collaborative run.

## Step 0: Data Access Gate

Pass requires two legally accessible public DFT label snapshots plus the
WBM/Matbench benchmark context. The minimal preferred pair is Materials
Project and Alexandria. OQMD may serve as a replication or secondary source,
but a low-coverage exact-match join is not enough by itself.

If this gate fails, the discordance paper route stops. No prose, abstract or
pipeline expansion should continue.

## Step 1: Minimal Discordance Probe

Run exact/high-confidence structure matching between two independent source
snapshots. Formula-only matches are tags only and cannot enter the primary
denominator.

Go: binary stable/unstable discordance is at least 0.40 on at least 200
matched structures with at least 20% pair coverage.

No-go: discordance is at most 0.10, the matched denominator is below 200, or
pair coverage is below 20%.

Boundary: 0.10-0.40 discordance requires a third-source replication before a
paper launch decision.

## Step 2: Downstream Consequence Gate

Discordance alone is not enough for an NMI-scale claim. At least one
downstream conclusion must change: a public-model ranking flips, a discovered
stable-material count changes materially, or a release/refuse probe changes
decision under source A versus source B.

If ranking and discovered counts are stable, the route is downgraded to a
diagnostic note even if Step 1 finds label disagreement.
"""
    write_text(OUT / "DATA_ACCESS_GO_NO_GO.md", access_md)

    prereg_md = """# Discordance Study Preregistration

## Scope

This is a preregistration for a separate materials-label discordance paper.
The target is the reproducibility and downstream consequence of public DFT
binary stability labels used in ML crystal-stability discovery benchmarks.

The primary contribution is not PARC. PARC may be used later as a
release/refuse probe after source discordance has been quantified.

## Central Hypothesis

Public DFT source choice can change binary exact-stability labels on exactly
matched crystal structures, and that label discordance can change ML
materials-discovery conclusions.

## Frozen Week-One Tests

1. Data access: verify legal, versioned snapshots for at least two public DFT
   sources plus WBM/Matbench context.
2. Minimal discordance: compute pairwise binary exact-stability discordance
   only on exact/high-confidence structure matches.
3. Downstream consequence: test whether public-model rankings, discovered
   stable counts, or release/refuse decisions flip under source A versus B.

## Stop Rules

- Stop if data access cannot be established without private or untracked
  labels.
- Stop if the clean two-source discordance is small (`<=0.10`) or the exact
  match denominator is too small.
- Stop or downgrade if discordance does not change downstream conclusions.

## Claim Boundaries

Do not claim that external materials databases are interchangeable ground
truth. Do not claim prospective materials discovery. Do not claim that PARC
solves cross-source DFT disagreement. Do not use formula-only matches for the
headline discordance number.
"""
    write_text(OUT / "DISCORDANCE_STUDY_PREREGISTRATION.md", prereg_md)

    manifest = manifest_for(OUT)
    write_text(OUT / "MANIFEST_SHA256.txt", manifest)


if __name__ == "__main__":
    main()
