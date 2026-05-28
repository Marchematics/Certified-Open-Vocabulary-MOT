#!/usr/bin/env python3
"""Build the Week 0 protocol-freeze package for the NCS/NMI resubmission track.

This package is intentionally evidence-neutral.  It freezes the protocol,
source artifacts, DFT audit arms, temporal hull definitions, MLIP audit models,
CTC audit guidelines, and go/no-go rules before any new outcome-dependent
materials claims are made.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_week0_protocol_freeze"
FROZEN_TIMESTAMP = "2026-05-28T18:43:21+08:00"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def source(path: str) -> tuple[str, str]:
    file_path = ROOT / path
    if not file_path.exists():
        raise FileNotFoundError(path)
    return path, sha256_file(file_path)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: dict[str, object]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_manifest(path: Path) -> None:
    rows: list[str] = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path).as_posix()}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def write_root_manifest() -> None:
    rows: list[str] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if ".pytest_cache" in path.parts or "tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def write_simple_pdf(path: Path, title: str, lines: list[str]) -> None:
    """Write a small, valid, text-only PDF without adding a binary dependency."""
    display_lines = [title, ""] + lines
    commands = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for line in display_lines[:52]:
        commands.append(f"({pdf_escape(line[:92])}) Tj")
        commands.append("T*")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(sum(len(c) for c in chunks))
        chunks.append(f"{i} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = sum(len(c) for c in chunks)
    xref = [b"xref\n0 6\n", b"0000000000 65535 f \n"]
    for offset in offsets[1:]:
        xref.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode("ascii")
        + b"\n%%EOF\n"
    )
    path.write_bytes(b"".join(chunks + xref + [trailer]))


def build_candidate_universe() -> None:
    rows: list[dict[str, object]] = []
    entries = [
        (
            "a3_v4_strict_public_label_free_universe",
            "outputs/milestones/mattergen_parc_prospective_dft_followup/candidate_universe_strict_public_label_free.csv",
            "formal_pre_dft_selection_universe",
            "Use only as frozen A3 candidate universe; no DFT outcome or positive claim is present.",
        ),
        (
            "a3_v4_selection_frozen",
            "outputs/milestones/mattergen_parc_prospective_dft_followup/selection_frozen_v4.csv",
            "frozen_selection_do_not_modify",
            "Selection may not be changed after DFT outcomes.",
        ),
        (
            "ctc_active_audit_primary_seed_rows",
            "outputs/milestones/audit_budget_frontier_strong_positive/table_ctc_primary_seed_rows.csv",
            "primary_strict_active_audit_candidate_rows",
            "CTC active verification is the current strict anchor.",
        ),
        (
            "t1_baseline_frontier_rows",
            "outputs/milestones/t1_clean_acceptance_package/table_t1_baseline_frontier_summary.csv",
            "completed_empirical_baseline_frontier",
            "Baseline frontier is completed evidence; no prospective materials claim.",
        ),
        (
            "materials_temporal_snapshot_inventory",
            "outputs/milestones/materials_temporal_replay_completed/table_temporal_snapshot_inventory.csv",
            "temporal_snapshot_feasibility_inventory",
            "A1 temporal validation remains no-go unless public timestamped snapshots are supplied.",
        ),
    ]
    for result_id, artifact, status, boundary in entries:
        source_artifact, source_sha = source(artifact)
        rows.append(
            {
                "frozen_object": result_id,
                "source_artifact": source_artifact,
                "source_sha256": source_sha,
                "frozen_status": status,
                "claim_boundary": boundary,
                "freeze_timestamp": FROZEN_TIMESTAMP,
            }
        )
    write_csv(
        OUT / "table_frozen_candidate_universe.csv",
        rows,
        ["frozen_object", "source_artifact", "source_sha256", "frozen_status", "claim_boundary", "freeze_timestamp"],
    )


def build_model_scores() -> None:
    entries = [
        ("CHGNet", "outputs/milestones/mattergen_parc_prospective_dft_followup/candidate_scores_chgnet.csv", "frozen_pre_dft_score"),
        ("MACE-MP", "outputs/milestones/mattergen_parc_prospective_dft_followup/candidate_scores_mace.csv", "frozen_pre_dft_score"),
        ("CHGNet_MACE_consensus", "outputs/milestones/mattergen_parc_prospective_dft_followup/candidate_scores_consensus.csv", "frozen_pre_dft_consensus_score"),
        ("ALIGNN-FF", "outputs/milestones/mattergen_alignnff_preoutcome_scoring_snapshot/candidate_scores_alignnff_strict_public_label_free_2990.csv", "frozen_pre_outcome_scorer_diagnostic"),
        ("T1_baseline_frontier_scores", "outputs/milestones/t1_clean_acceptance_package/table_t1_baseline_frontier_summary.csv", "completed_baseline_frontier_source"),
    ]
    rows: list[dict[str, object]] = []
    for model, artifact, status in entries:
        source_artifact, source_sha = source(artifact)
        rows.append(
            {
                "model_or_score_source": model,
                "source_artifact": source_artifact,
                "source_sha256": source_sha,
                "frozen_status": status,
                "post_outcome_selection_allowed": "no",
                "claim_boundary": "Scores are frozen inputs or diagnostics; they are not DFT evidence.",
            }
        )
    write_csv(
        OUT / "table_frozen_model_scores.csv",
        rows,
        ["model_or_score_source", "source_artifact", "source_sha256", "frozen_status", "post_outcome_selection_allowed", "claim_boundary"],
    )


def build_static_tables() -> None:
    write_csv(
        OUT / "table_frozen_parc_parameters.csv",
        [
            {
                "domain_or_track": "materials_A3_v4",
                "alpha_primary": 0.10,
                "alpha_secondary": 0.20,
                "rho_primary": 0.10,
                "block_definition_primary": "composition_family",
                "calibrator_rule": "frozen finite-resolution e-calibrator rule from PARC implementation",
                "selector_rule": "SCS-Greedy with denominator-aware compatibility",
                "post_hoc_tuning_allowed": "no",
            },
            {
                "domain_or_track": "materials_T1_baseline_frontier",
                "alpha_primary": 0.10,
                "alpha_secondary": 0.20,
                "rho_primary": 0.10,
                "block_definition_primary": "composition_family",
                "calibrator_rule": "same frozen PARC rule as completed T1 package",
                "selector_rule": "baseline frontier plus PARC reference rows",
                "post_hoc_tuning_allowed": "no",
            },
            {
                "domain_or_track": "ctc_active_audit",
                "alpha_primary": 0.10,
                "alpha_secondary": "",
                "rho_primary": 0.005,
                "block_definition_primary": "sequence_disjoint_or_domain_defined_blocks",
                "calibrator_rule": "same frozen PARC rule as CTC active-audit package",
                "selector_rule": "top_score_active_audit_primary; random and block-balanced policies are comparators",
                "post_hoc_tuning_allowed": "no",
            },
        ],
        [
            "domain_or_track",
            "alpha_primary",
            "alpha_secondary",
            "rho_primary",
            "block_definition_primary",
            "calibrator_rule",
            "selector_rule",
            "post_hoc_tuning_allowed",
        ],
    )
    write_csv(
        OUT / "table_k_alpha_grid.csv",
        [
            {"endpoint_id": "materials_fixed_budget_K300", "domain": "materials", "K": 300, "alpha": 0.10, "role": "primary_support", "claim_boundary": "retrospective public-label release-policy frontier"},
            {"endpoint_id": "materials_fixed_budget_K500", "domain": "materials", "K": 500, "alpha": 0.10, "role": "primary_support", "claim_boundary": "retrospective public-label release-policy frontier"},
            {"endpoint_id": "materials_high_volume_K5000", "domain": "materials", "K": 5000, "alpha": 0.10, "role": "refusal_stress", "claim_boundary": "unsafe-request refusal only"},
            {"endpoint_id": "a3_v4a_strict", "domain": "materials_A3", "K": 100, "alpha": 0.10, "role": "pre_dft_protocol_endpoint", "claim_boundary": "pending until DFT gates pass"},
            {"endpoint_id": "a3_v4b_strict_larger", "domain": "materials_A3", "K": 300, "alpha": 0.10, "role": "pre_dft_protocol_endpoint", "claim_boundary": "pending until DFT gates pass"},
            {"endpoint_id": "a3_v4c_near_hull", "domain": "materials_A3", "K": 300, "alpha": 0.10, "role": "near_hull_boundary_endpoint", "claim_boundary": "near-hull follow-up only; not exact-stability headline"},
            {"endpoint_id": "ctc_active_audit_K100", "domain": "CTC", "K": 100, "alpha": 0.10, "role": "primary_strict_anchor", "claim_boundary": "CTC active verification headline"},
            {"endpoint_id": "ctc_support_K300", "domain": "CTC", "K": 300, "alpha": 0.10, "role": "secondary_support", "claim_boundary": "supporting active-audit frontier row"},
        ],
        ["endpoint_id", "domain", "K", "alpha", "role", "claim_boundary"],
    )
    write_csv(
        OUT / "table_block_definitions.csv",
        [
            {"domain": "materials", "block_id": "composition_family", "role": "primary", "definition": "composition-family blocks from frozen PARC materials implementation", "sensitivity_status": "chemical-system and Wyckoff sensitivity are support rows only"},
            {"domain": "materials", "block_id": "chemical_system", "role": "sensitivity", "definition": "chemical-system grouping", "sensitivity_status": "not selected post hoc"},
            {"domain": "materials", "block_id": "wyckoff_family", "role": "sensitivity", "definition": "structural-family sensitivity where available", "sensitivity_status": "not selected post hoc"},
            {"domain": "CTC", "block_id": "sequence_disjoint", "role": "primary", "definition": "train/evaluation sequence separation and sequence-level blocking", "sensitivity_status": "leakage audit required"},
            {"domain": "iWildCam_SpaceNet", "block_id": "camera_or_AOI", "role": "audit_boundary", "definition": "camera-location or area-of-interest blocks where public-safe rows are available", "sensitivity_status": "not headline unless completed audit labels exist"},
        ],
        ["domain", "block_id", "role", "definition", "sensitivity_status"],
    )
    write_csv(
        OUT / "table_dft_audit_sampling_scheme.csv",
        [
            {"arm": "parc_release_full", "planned_n": 75, "source_manifest": source("outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_addendum.csv")[0], "source_sha256": source("outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_addendum.csv")[1], "construction_rule": "all frozen PARC-release candidates if compute allows", "uses_DFT_outcome": "no", "failure_policy": "failed jobs count as not-certified-stable/false for FTR"},
            {"arm": "raw_topR_matched", "planned_n": 75, "source_manifest": source("outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_addendum.csv")[0], "source_sha256": source("outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_addendum.csv")[1], "construction_rule": "same size as PARC DFT arm, using pre-DFT frozen rank/status only", "uses_DFT_outcome": "no", "failure_policy": "failed jobs count as not-certified-stable/false for FTR"},
            {"arm": "raw_top100_extra_tail", "planned_n": 25, "source_manifest": source("outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv")[0], "source_sha256": source("outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv")[1], "construction_rule": "optional raw top100 candidates not released by PARC, frozen before outcomes", "uses_DFT_outcome": "no", "failure_policy": "failed jobs count as not-certified-stable/false for FTR"},
        ],
        ["arm", "planned_n", "source_manifest", "source_sha256", "construction_rule", "uses_DFT_outcome", "failure_policy"],
    )
    write_csv(
        OUT / "table_temporal_hull_definitions.csv",
        [
            {"definition_id": "exact_stable", "positive_rule": "e_above_hull <= 0 eV/atom", "role": "primary exact-stability rule", "claim_boundary": "requires timestamped t0/t1 public snapshots for A1 positive evidence"},
            {"definition_id": "near_hull_25meV", "positive_rule": "e_above_hull <= 0.025 eV/atom", "role": "near-hull boundary sensitivity", "claim_boundary": "not exact-stability headline"},
            {"definition_id": "margin_excluded_25meV", "positive_rule": "exclude candidates within +/-25 meV/atom of hull boundary", "role": "boundary sensitivity", "claim_boundary": "boundary diagnostic only"},
            {"definition_id": "t0_visible_labels", "positive_rule": "labels publicly visible at frozen t0 only", "role": "calibration source", "claim_boundary": "if t0 provenance is absent, report no-go/diagnostic"},
            {"definition_id": "t1_future_labels", "positive_rule": "labels visible in later frozen snapshot t1", "role": "evaluation source", "claim_boundary": "t1 must not be read before release sets are frozen"},
        ],
        ["definition_id", "positive_rule", "role", "claim_boundary"],
    )
    write_csv(
        OUT / "table_mlip_audit_models.csv",
        [
            {"model": "CHGNet", "role": "required_MLIP_audit_model", "frozen_artifact": source("outputs/milestones/mattergen_parc_prospective_dft_followup/candidate_scores_chgnet.csv")[0], "source_sha256": source("outputs/milestones/mattergen_parc_prospective_dft_followup/candidate_scores_chgnet.csv")[1], "post_outcome_selection_allowed": "no"},
            {"model": "MACE-MP", "role": "required_MLIP_audit_model", "frozen_artifact": source("outputs/milestones/mattergen_parc_prospective_dft_followup/candidate_scores_mace.csv")[0], "source_sha256": source("outputs/milestones/mattergen_parc_prospective_dft_followup/candidate_scores_mace.csv")[1], "post_outcome_selection_allowed": "no"},
            {"model": "ALIGNN-FF", "role": "pre_outcome_scorer_diagnostic", "frozen_artifact": source("outputs/milestones/mattergen_alignnff_preoutcome_scoring_snapshot/candidate_scores_alignnff_strict_public_label_free_2990.csv")[0], "source_sha256": source("outputs/milestones/mattergen_alignnff_preoutcome_scoring_snapshot/candidate_scores_alignnff_strict_public_label_free_2990.csv")[1], "post_outcome_selection_allowed": "no"},
            {"model": "MatterSim_or_Orb", "role": "optional_future_model_only_if_frozen_before_outcomes", "frozen_artifact": "", "source_sha256": "", "post_outcome_selection_allowed": "no"},
        ],
        ["model", "role", "frozen_artifact", "source_sha256", "post_outcome_selection_allowed"],
    )
    write_csv(
        OUT / "table_ctc_human_audit_guidelines.csv",
        [
            {"guideline_id": "audit_protocol", "source_artifact": source("docs/audit_protocol.md")[0], "source_sha256": source("docs/audit_protocol.md")[1], "rule": "auditors are blind to model, PARC status, rank, and existing labels when external packet is used"},
            {"guideline_id": "label_decision_rules", "source_artifact": source("docs/audit_label_decision_rules.md")[0], "source_sha256": source("docs/audit_label_decision_rules.md")[1], "rule": "positive, false, and uncertain labels are separated; uncertain is conservative for release FTR"},
            {"guideline_id": "ctc_feature_provenance", "source_artifact": source("outputs/milestones/ctc_strict_anchor/ctc_feature_provenance.md")[0], "source_sha256": source("outputs/milestones/ctc_strict_anchor/ctc_feature_provenance.md")[1], "rule": "sequence leakage and GT feature provenance remain audited before CTC headline use"},
        ],
        ["guideline_id", "source_artifact", "source_sha256", "rule"],
    )
    write_csv(
        OUT / "table_go_no_go_rules.csv",
        [
            {"gate": "week0_protocol_freeze", "pass_rule": "all protocol tables, PDF, provenance, and SHA256 manifest exist before new outcome claims", "no_go_rule": "missing source hashes or fake external registration URL blocks claim use", "claim_if_pass": "protocol_freeze_only"},
            {"gate": "materials_temporal_t0_t1", "pass_rule": "PARC t1 FTR <= alpha or clearly below raw top-K; stable-to-unstable drift does not concentrate in release", "no_go_rule": "timestamped t0/t1 snapshots absent or raw top-K already trivially safe means diagnostic/no-go", "claim_if_pass": "temporal_validation_if_predeclared_inputs_exist"},
            {"gate": "MLIP_dense_audit", "pass_rule": "at least two frozen MLIP audit models support the same release/tail contrast direction and disagreements are boundary/hull-sensitive", "no_go_rule": "model disagreement reverses the conclusion or models are chosen after outcomes", "claim_if_pass": "pre_outcome_MLIP_support_not_DFT_evidence"},
            {"gate": "independent_DFT_blind_audit", "pass_rule": "PARC DFT-audited FTR <= alpha or significantly below raw top-K; matched raw top-R close is claimed only as certified stopping", "no_go_rule": "any DFT outcome seen before comparator-arm freeze prevents primary raw-vs-PARC claim", "claim_if_pass": "prospective_DFT_audit_only_if_all_gates_pass"},
            {"gate": "A3_claim_boundary", "pass_rule": "released_n >=25, selection_frozen true, DFT completed_n >=25, primary_FTR <= alpha", "no_go_rule": "otherwise A3 remains diagnostic/failed gate with no prospective materials-discovery claim", "claim_if_pass": "prospective_materials_claim_allowed_only_under_gate"},
        ],
        ["gate", "pass_rule", "no_go_rule", "claim_if_pass"],
    )
    write_csv(
        OUT / "table_external_registration_plan.csv",
        [
            {"registry": "OSF", "registration_status": "ready_for_upload_not_uploaded", "registration_url": "", "doi": "", "required_payload": "NCS_WEEK0_PROTOCOL_FREEZE.pdf plus CSV/JSON/manifest package", "no_fake_identifier": "true"},
            {"registry": "Zenodo", "registration_status": "ready_for_upload_not_uploaded", "registration_url": "", "doi": "", "required_payload": "archival snapshot after local protocol freeze and before outcome analysis", "no_fake_identifier": "true"},
        ],
        ["registry", "registration_status", "registration_url", "doi", "required_payload", "no_fake_identifier"],
    )


def build_markdown_and_pdf() -> None:
    md = f"""# NCS Week 0 Protocol Freeze

Freeze timestamp: `{FROZEN_TIMESTAMP}`

Repository commit at freeze build time: `{git_commit()}`

## Status

This milestone is a preregistration/protocol-freeze package only. It creates no
new scientific evidence, no DFT outcome, no prospective materials-discovery
claim, and no positive independent materials validation claim. OSF/Zenodo upload
is prepared but not represented as completed in this repository.

Boundary summary: no DFT outcome; no prospective materials-discovery claim; no
positive independent materials validation claim.

## Frozen Objects

- Candidate universes and release selections are frozen in
  `table_frozen_candidate_universe.csv`.
- Model scores are frozen in `table_frozen_model_scores.csv`.
- PARC parameters, K/alpha grid, and block definitions are frozen in
  `table_frozen_parc_parameters.csv`, `table_k_alpha_grid.csv`, and
  `table_block_definitions.csv`.
- DFT audit arms are frozen in `table_dft_audit_sampling_scheme.csv`; they use
  only pre-DFT score, rank, selection status, and public-label exclusion status.
- t0/t1 hull definitions and MLIP audit models are frozen before any new
  outcome-dependent interpretation.
- CTC human-audit guidelines remain blind/conservative and are tied to existing
  source artifacts by SHA256.

## Go / No-Go

The primary anti-p-hacking guardrail is that DFT comparator arms, hull
definitions, score sources, and manuscript claim boundaries are fixed before
outcomes. If any DFT outcome is observed before comparator-arm freeze, that arm
cannot support a primary raw-vs-PARC claim. If A3 gates fail, A3 remains a
diagnostic or failed-gate vignette.

## External Registration

`table_external_registration_plan.csv` records OSF and Zenodo as
ready-for-upload targets. No DOI or registration URL is fabricated here.
"""
    (OUT / "NCS_WEEK0_PROTOCOL_FREEZE.md").write_text(md, encoding="utf-8")
    write_simple_pdf(
        OUT / "NCS_WEEK0_PROTOCOL_FREEZE.pdf",
        "NCS Week 0 Protocol Freeze",
        [
            f"Freeze timestamp: {FROZEN_TIMESTAMP}",
            f"Commit: {git_commit()}",
            "Status: preregistered protocol freeze only.",
            "No new evidence, no DFT outcome, no prospective materials discovery claim.",
            "Frozen: candidate universe, scores, PARC parameters, K/alpha grid, blocks.",
            "Frozen: DFT audit sampling, t0/t1 hull definitions, MLIP audit models.",
            "Frozen: CTC human-audit guidelines and go/no-go rules.",
            "External OSF/Zenodo registration targets are ready for upload, not completed.",
        ],
    )


def build_provenance() -> None:
    write_json(
        OUT / "protocol_freeze_timestamp.json",
        {
            "freeze_timestamp": FROZEN_TIMESTAMP,
            "timezone": "Asia/Shanghai",
            "commit": git_commit(),
            "external_registration_status": "ready_for_upload_not_uploaded",
            "claim_boundary": [
                "no_new_results",
                "no_positive_materials_evidence",
                "no_A3_DFT_outcome",
                "no_prospective_materials_discovery_claim",
                "no_positive_independent_materials_validation_claim",
            ],
        },
    )
    write_json(
        OUT / "provenance.json",
        {
            "milestone": "ncs_week0_protocol_freeze",
            "built_at": FROZEN_TIMESTAMP,
            "freeze_timestamp": FROZEN_TIMESTAMP,
            "git_commit": git_commit(),
            "evidence_status": "preregistered_protocol_freeze_only",
            "external_registration_status": "ready_for_upload_not_uploaded",
            "no_outcome_claims": True,
            "no_post_hoc_endpoint_selection": True,
        },
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    build_candidate_universe()
    build_model_scores()
    build_static_tables()
    build_markdown_and_pdf()
    build_provenance()
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    main()
