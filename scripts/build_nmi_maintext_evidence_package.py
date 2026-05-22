#!/usr/bin/env python3
"""Build a main-text evidence package from completed non-A3 artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
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


def source(path: str) -> tuple[str, str]:
    p = Path(path)
    return path, sha256_file(p)


def build_headline_hierarchy() -> pd.DataFrame:
    audit_path, audit_sha = source(
        "outputs/milestones/audit_budget_release_frontier_headline/table_audit_budget_transition_primary.csv"
    )
    p0_path, p0_sha = source("outputs/milestones/nmi_reviewer_p0_hardening/table_p0_reviewer_gap_action_matrix.csv")
    ci_path, ci_sha = source("outputs/milestones/nmi_reviewer_p0_hardening/table_human_audit_uncertainty_intervals.csv")
    baseline_path, baseline_sha = source(
        "outputs/milestones/nmi_reviewer_p0_hardening/table_baseline_frontier_maintext_map.csv"
    )
    refusal_path, refusal_sha = source(
        "outputs/milestones/nmi_reviewer_p0_hardening/table_refusal_feasibility_attribution.csv"
    )
    assumption_path, assumption_sha = source(
        "outputs/milestones/nmi_reviewer_p0_hardening/table_assumption_diagnostics_maintext_map.csv"
    )
    rows = [
        {
            "evidence_block": "active_audit_ctc_strict_transition",
            "allowed_manuscript_role": "primary_headline",
            "status": "completed_evidence",
            "exact_manuscript_sentence": (
                "In CTC, top-score auditing of only 0.5% of calibration candidates converted refusal into strict "
                "seed-stable certified release at alpha=0.10 for K=100 and K=300, whereas random audit required "
                "full calibration-set inspection in the frozen grid."
            ),
            "source_artifact": audit_path,
            "source_sha256": audit_sha,
            "claim_boundary": "simulated audit over existing held-out labels; no new labels; no A3 evidence",
        },
        {
            "evidence_block": "materials_audit_budget_boundary",
            "allowed_manuscript_role": "secondary_boundary",
            "status": "completed_boundary_evidence",
            "exact_manuscript_sentence": (
                "Materials ALIGNN rows showed a mean-operating audit-budget transition at 0.5%, but seed-level "
                "alpha-violation rates of 0.45 for K=300 and 0.15 for K=500 make these boundary rows rather than "
                "strict headline releases."
            ),
            "source_artifact": audit_path,
            "source_sha256": audit_sha,
            "claim_boundary": "not a strict materials headline; not prospective materials discovery",
        },
        {
            "evidence_block": "materials_prospective_gap",
            "allowed_manuscript_role": "explicit_limitation_or_no_go",
            "status": "not_completed_positive_evidence",
            "exact_manuscript_sentence": (
                "We do not claim prospective materials discovery: external and temporal materials validations remain "
                "diagnostic or no-go unless a future frozen DFT gate is completed."
            ),
            "source_artifact": p0_path,
            "source_sha256": p0_sha,
            "claim_boundary": "forbidden as positive evidence",
        },
        {
            "evidence_block": "human_audit_uncertainty",
            "allowed_manuscript_role": "audited_boundary_support",
            "status": "completed_human_audit_interval",
            "exact_manuscript_sentence": (
                "The zero-false iWildCam and SpaceNet audit outcomes are reported with interval uncertainty, "
                "including Clopper-Pearson upper bounds of 0.0178 and 0.0202."
            ),
            "source_artifact": ci_path,
            "source_sha256": ci_sha,
            "claim_boundary": "zero observed false is not universal zero-risk evidence",
        },
        {
            "evidence_block": "baseline_target_object_frontier",
            "allowed_manuscript_role": "main_or_extended_data_support",
            "status": "completed_baseline_map",
            "exact_manuscript_sentence": (
                "The baseline frontier is reported as a target-object-aware comparison: raw prefixes and plug-in "
                "baselines can be deployable empirical filters, but they do not supply PARC's null-superset, "
                "compatibility, and SCS release certificate."
            ),
            "source_artifact": baseline_path,
            "source_sha256": baseline_sha,
            "claim_boundary": "do not imply different-target baselines solve the same release certificate object",
        },
        {
            "evidence_block": "refusal_feasibility_attribution",
            "allowed_manuscript_role": "main_or_extended_data_support",
            "status": "completed_refusal_diagnostic",
            "exact_manuscript_sentence": (
                "Refusal rows are attributed to evidence-mass or finite-resolution gates rather than to an unexamined "
                "greedy-selector miss; where public graphs are unavailable, we do not fabricate selector optimality."
            ),
            "source_artifact": refusal_path,
            "source_sha256": refusal_sha,
            "claim_boundary": "refusal attribution diagnostic, not a new positive release result",
        },
        {
            "evidence_block": "assumption_diagnostics_panel",
            "allowed_manuscript_role": "assumption_figure_support",
            "status": "completed_diagnostic_aggregation",
            "exact_manuscript_sentence": (
                "Assumption diagnostics are centralized across stability definitions, block choices, gamma sensitivity, "
                "block-size heterogeneity, positive-contamination stress, and refusal attribution."
            ),
            "source_artifact": assumption_path,
            "source_sha256": assumption_sha,
            "claim_boundary": "diagnostic aggregation; contamination rows are assumption-violation diagnostics",
        },
    ]
    return pd.DataFrame(rows)


def build_audit_figure_source() -> pd.DataFrame:
    primary = pd.read_csv(
        "outputs/milestones/audit_budget_release_frontier_headline/table_audit_budget_transition_primary.csv"
    )
    rows = []
    for _, row in primary.iterrows():
        if row["manuscript_role"] == "strict_seed_stable_headline_candidate":
            rows.append(
                {
                    "panel": "audit_budget_transition",
                    "target_row": row["target_row"],
                    "domain": row["domain"],
                    "role": "strict_headline",
                    "top_score_budget": row["top_score_first_strict_budget"],
                    "random_budget": row["random_first_strict_budget"],
                    "efficiency_gain": row["top_score_vs_random_efficiency_gain"],
                    "mean_release": row["top_score_mean_release_at_transition"],
                    "actual_FTR": row["top_score_actual_FTR_at_transition"],
                    "alpha_violation_rate": row["top_score_alpha_violation_rate_at_transition"],
                    "label": "strict seed-stable transition",
                }
            )
        elif row["manuscript_role"] == "mean_operating_boundary_secondary":
            rows.append(
                {
                    "panel": "audit_budget_transition",
                    "target_row": row["target_row"],
                    "domain": row["domain"],
                    "role": "boundary_secondary",
                    "top_score_budget": row["top_score_first_mean_operating_budget"],
                    "random_budget": row["random_first_mean_operating_budget"],
                    "efficiency_gain": row["top_score_vs_random_mean_operating_gain"],
                    "mean_release": row["top_score_mean_release_at_mean_operating"],
                    "actual_FTR": row["top_score_actual_FTR_at_mean_operating"],
                    "alpha_violation_rate": row["top_score_alpha_violation_rate_at_mean_operating"],
                    "label": "mean-operating transition only",
                }
            )
    return pd.DataFrame(rows)


def build_reviewer_support_source() -> pd.DataFrame:
    p0 = pd.read_csv("outputs/milestones/nmi_reviewer_p0_hardening/table_p0_reviewer_gap_action_matrix.csv")
    audit = pd.read_csv("outputs/milestones/nmi_reviewer_p0_hardening/table_human_audit_uncertainty_intervals.csv")
    refusal = pd.read_csv("outputs/milestones/nmi_reviewer_p0_hardening/table_refusal_feasibility_attribution.csv")
    rows = []
    for _, row in p0.iterrows():
        rows.append(
            {
                "panel": "p0_gap_action",
                "item": row["p0_item"],
                "status": row["current_status"],
                "numeric_value": "",
                "label": row["reviewer_need"],
                "claim_boundary": row["manuscript_action"],
            }
        )
    for _, row in audit.iterrows():
        rows.append(
            {
                "panel": "audit_uncertainty",
                "item": f"{row['domain']}:{row['sample']}",
                "status": "completed_interval",
                "numeric_value": row["clopper_pearson_upper95"],
                "label": "CP upper95",
                "claim_boundary": row["claim_boundary"],
            }
        )
    for _, row in refusal.iterrows():
        rows.append(
            {
                "panel": "refusal_attribution",
                "item": row["row_id"],
                "status": row["failure_mode"],
                "numeric_value": row["evidence_mass_phi"],
                "label": "evidence_mass_phi",
                "claim_boundary": row["paper_interpretation"],
            }
        )
    return pd.DataFrame(rows)


def write_closeout(out_dir: Path, hierarchy: pd.DataFrame) -> None:
    primary = hierarchy[hierarchy["allowed_manuscript_role"].eq("primary_headline")]
    forbidden = hierarchy[hierarchy["status"].astype(str).str.contains("not_completed")]
    text = (
        "# NMI Maintext Evidence Package\n\n"
        "Status: completed paper-facing package.\n\n"
        "This package converts completed non-A3 artifacts into exact manuscript sentences, figure source rows, "
        "and source SHA256 mappings. It does not edit the manuscript and does not create new evidence.\n\n"
        "## Headline Discipline\n\n"
        f"- Primary headline rows: {len(primary)}\n"
        f"- Explicit not-positive rows: {len(forbidden)}\n"
        "- The only primary headline in this package is the CTC active-audit strict transition.\n"
        "- Materials audit-budget rows remain boundary/secondary, and materials prospective discovery remains forbidden.\n"
    )
    (out_dir / "NMI_MAINTEXT_EVIDENCE_PACKAGE.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/nmi_maintext_evidence_package")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    hierarchy = build_headline_hierarchy()
    audit_figure = build_audit_figure_source()
    reviewer_support = build_reviewer_support_source()
    figures = pd.DataFrame(
        [
            {
                "figure_or_table": "main_audit_budget_frontier",
                "source_file": "figure_audit_budget_maintext_source.csv",
                "paper_role": "primary active-audit transition figure",
                "claim_boundary": "CTC strict headline; materials boundary secondary",
            },
            {
                "figure_or_table": "reviewer_p0_support_panel",
                "source_file": "figure_reviewer_p0_support_source.csv",
                "paper_role": "extended data / reviewer-facing support figure",
                "claim_boundary": "diagnostic and uncertainty rows remain scoped",
            },
            {
                "figure_or_table": "claim_sentence_table",
                "source_file": "table_maintext_claim_sentences.csv",
                "paper_role": "claim-to-artifact guardrail",
                "claim_boundary": "exact sentences must preserve allowed manuscript role",
            },
        ]
    )
    hierarchy.to_csv(out_dir / "table_headline_evidence_hierarchy.csv", index=False)
    hierarchy[
        [
            "evidence_block",
            "allowed_manuscript_role",
            "status",
            "exact_manuscript_sentence",
            "source_artifact",
            "source_sha256",
            "claim_boundary",
        ]
    ].to_csv(out_dir / "table_maintext_claim_sentences.csv", index=False)
    audit_figure.to_csv(out_dir / "figure_audit_budget_maintext_source.csv", index=False)
    reviewer_support.to_csv(out_dir / "figure_reviewer_p0_support_source.csv", index=False)
    figures.to_csv(out_dir / "table_figures_to_artifacts.csv", index=False)
    write_closeout(out_dir, hierarchy)
    provenance = {
        "status": "completed",
        "evidence_status": "paper_facing_postprocess_only",
        "claim_boundary": "does not edit manuscript; does not create prospective materials evidence",
        "outputs": [
            "table_headline_evidence_hierarchy.csv",
            "table_maintext_claim_sentences.csv",
            "figure_audit_budget_maintext_source.csv",
            "figure_reviewer_p0_support_source.csv",
            "table_figures_to_artifacts.csv",
            "NMI_MAINTEXT_EVIDENCE_PACKAGE.md",
        ],
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(out_dir)
    print(json.dumps(provenance, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
