#!/usr/bin/env python3
"""Build paper-facing lead tables for the audit-budget frontier."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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


def first_transition(summary: pd.DataFrame, min_safe_release_rate: float) -> pd.DataFrame:
    eligible = summary[
        (summary["safe_release_rate"].astype(float) >= min_safe_release_rate)
        & (summary["actual_FTR_mean"].astype(float) <= summary["alpha"].astype(float))
        & (summary["mean_release"].astype(float) > 0)
    ].copy()
    if eligible.empty:
        return pd.DataFrame(columns=list(summary.columns) + ["strict_transition_found"])
    eligible = eligible.sort_values(["target_row", "audit_policy", "audit_budget_fraction"])
    first = eligible.groupby(["target_row", "audit_policy"], dropna=False).head(1).copy()
    first["strict_transition_found"] = True
    return first


def first_mean_operating_transition(summary: pd.DataFrame, min_release_rate: float) -> pd.DataFrame:
    eligible = summary[
        (summary["release_rate"].astype(float) >= min_release_rate)
        & (summary["actual_FTR_mean"].astype(float) <= summary["alpha"].astype(float))
        & (summary["mean_release"].astype(float) > 0)
    ].copy()
    if eligible.empty:
        return pd.DataFrame(columns=list(summary.columns) + ["mean_operating_transition_found"])
    eligible = eligible.sort_values(["target_row", "audit_policy", "audit_budget_fraction"])
    first = eligible.groupby(["target_row", "audit_policy"], dropna=False).head(1).copy()
    first["mean_operating_transition_found"] = True
    return first


def target_role(target_row: str) -> str:
    if "cgcnn" in target_row:
        return "calibration_check_not_headline"
    if "alignn" in target_row:
        return "materials_fixed_budget_headline_candidate"
    if "ctc" in target_row:
        return "ctc_strict_anchor_headline_candidate"
    return "supporting_row"


def build_primary(default_summary: pd.DataFrame, extended_summary: pd.DataFrame, min_safe_release_rate: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    extended_first = first_transition(extended_summary, min_safe_release_rate)
    default_first = first_transition(default_summary, min_safe_release_rate)
    combined_first = pd.concat([default_first, extended_first], ignore_index=True)
    combined_first = combined_first.sort_values(["target_row", "audit_policy", "audit_budget_fraction"])
    combined_first = combined_first.drop_duplicates(["target_row", "audit_policy"], keep="first")
    combined_mean = pd.concat(
        [
            first_mean_operating_transition(default_summary, min_safe_release_rate),
            first_mean_operating_transition(extended_summary, min_safe_release_rate),
        ],
        ignore_index=True,
    )
    combined_mean = combined_mean.sort_values(["target_row", "audit_policy", "audit_budget_fraction"])
    combined_mean = combined_mean.drop_duplicates(["target_row", "audit_policy"], keep="first")
    max_random_budget = float(
        extended_summary.loc[extended_summary["audit_policy"].eq("random"), "audit_budget_fraction"].astype(float).max()
    )

    policy_rows = []
    primary_rows = []
    for target_row, group in default_summary.groupby("target_row", dropna=False):
        domain = group["domain"].iloc[0]
        alpha = float(group["alpha"].iloc[0])
        k_value = int(group["K"].iloc[0])
        role = target_role(str(target_row))
        target_first = combined_first[combined_first["target_row"].eq(target_row)].copy()
        target_mean = combined_mean[combined_mean["target_row"].eq(target_row)].copy()
        random_first = target_first[target_first["audit_policy"].eq("random")]
        top_first = target_first[target_first["audit_policy"].eq("top_score")]
        random_mean = target_mean[target_mean["audit_policy"].eq("random")]
        top_mean = target_mean[target_mean["audit_policy"].eq("top_score")]
        random_budget = float(random_first.iloc[0]["audit_budget_fraction"]) if not random_first.empty else math.nan
        top_budget = float(top_first.iloc[0]["audit_budget_fraction"]) if not top_first.empty else math.nan
        random_mean_budget = float(random_mean.iloc[0]["audit_budget_fraction"]) if not random_mean.empty else math.nan
        top_mean_budget = float(top_mean.iloc[0]["audit_budget_fraction"]) if not top_mean.empty else math.nan
        if math.isnan(random_budget) and not math.isnan(top_budget):
            gain = max_random_budget / top_budget if top_budget > 0 else math.inf
            gain_label = f">{gain:.1f}x"
            random_status = f"not reached by {max_random_budget:g}"
        elif not math.isnan(random_budget) and not math.isnan(top_budget):
            gain = random_budget / top_budget if top_budget > 0 else math.inf
            gain_label = f"{gain:.1f}x"
            random_status = "reached"
        else:
            gain = math.nan
            gain_label = "NA"
            random_status = "no top-score transition"
        if math.isnan(random_mean_budget) and not math.isnan(top_mean_budget):
            mean_gain = max_random_budget / top_mean_budget if top_mean_budget > 0 else math.inf
            mean_gain_label = f">{mean_gain:.1f}x"
            random_mean_status = f"not reached by {max_random_budget:g}"
        elif not math.isnan(random_mean_budget) and not math.isnan(top_mean_budget):
            mean_gain = random_mean_budget / top_mean_budget if top_mean_budget > 0 else math.inf
            mean_gain_label = f"{mean_gain:.1f}x"
            random_mean_status = "reached"
        else:
            mean_gain_label = "NA"
            random_mean_status = "no top-score mean transition"
        top = top_first.iloc[0].to_dict() if not top_first.empty else {}
        top_mean_row = top_mean.iloc[0].to_dict() if not top_mean.empty else {}
        if "calibration_check" in role:
            effective_role = role
        elif not math.isnan(top_budget):
            effective_role = "strict_seed_stable_headline_candidate"
        elif not math.isnan(top_mean_budget):
            effective_role = "mean_operating_boundary_secondary"
        else:
            effective_role = "no_transition_diagnostic"
        primary_rows.append(
            {
                "target_row": target_row,
                "domain": domain,
                "alpha": alpha,
                "K": k_value,
                "manuscript_role": effective_role,
                "top_score_first_strict_budget": top_budget if not math.isnan(top_budget) else "",
                "random_first_strict_budget": random_budget if not math.isnan(random_budget) else "",
                "random_baseline_status": random_status,
                "top_score_vs_random_efficiency_gain": gain_label,
                "top_score_release_rate_at_transition": top.get("release_rate", ""),
                "top_score_safe_release_rate_at_transition": top.get("safe_release_rate", ""),
                "top_score_mean_release_at_transition": top.get("mean_release", ""),
                "top_score_actual_FTR_at_transition": top.get("actual_FTR_mean", ""),
                "top_score_alpha_violation_rate_at_transition": top.get("alpha_violation_rate", ""),
                "top_score_verified_positives_found_mean": top.get("verified_positives_found_mean", ""),
                "top_score_cost_per_true_release_mean": top.get("cost_per_true_release_mean", ""),
                "top_score_first_mean_operating_budget": top_mean_budget if not math.isnan(top_mean_budget) else "",
                "random_first_mean_operating_budget": random_mean_budget if not math.isnan(random_mean_budget) else "",
                "random_mean_operating_status": random_mean_status,
                "top_score_vs_random_mean_operating_gain": mean_gain_label,
                "top_score_release_rate_at_mean_operating": top_mean_row.get("release_rate", ""),
                "top_score_safe_release_rate_at_mean_operating": top_mean_row.get("safe_release_rate", ""),
                "top_score_mean_release_at_mean_operating": top_mean_row.get("mean_release", ""),
                "top_score_actual_FTR_at_mean_operating": top_mean_row.get("actual_FTR_mean", ""),
                "top_score_alpha_violation_rate_at_mean_operating": top_mean_row.get("alpha_violation_rate", ""),
                "claim_boundary": "simulated audit frontier; not prospective materials discovery; A3 unchanged",
            }
        )
        for _, row in target_first.iterrows():
            policy_rows.append(
                {
                    "target_row": target_row,
                    "domain": domain,
                    "alpha": alpha,
                    "K": k_value,
                    "audit_policy": row["audit_policy"],
                    "first_strict_budget": row["audit_budget_fraction"],
                    "release_rate_at_transition": row["release_rate"],
                    "safe_release_rate_at_transition": row["safe_release_rate"],
                    "mean_release_at_transition": row["mean_release"],
                    "actual_FTR_at_transition": row["actual_FTR_mean"],
                    "verified_positives_found_mean": row["verified_positives_found_mean"],
                    "cost_per_true_release_mean": row["cost_per_true_release_mean"],
                    "manuscript_role": role,
                }
            )
    primary = pd.DataFrame(primary_rows)
    policy = pd.DataFrame(policy_rows)
    figure = pd.concat(
        [
            default_summary.assign(source_grid="phase40_default"),
            extended_summary.assign(source_grid="phase41_extended_random_top_score"),
        ],
        ignore_index=True,
    )
    figure = figure[
        [
            "source_grid",
            "domain",
            "target_row",
            "audit_policy",
            "audit_budget_fraction",
            "release_rate",
            "safe_release_rate",
            "mean_release",
            "actual_FTR_mean",
            "alpha",
            "audit_candidates_inspected_mean",
            "verified_positives_found_mean",
            "cost_per_true_release_mean",
        ]
    ].drop_duplicates()
    return primary, policy, figure


def write_closeout(out_dir: Path, primary: pd.DataFrame, policy: pd.DataFrame, args: argparse.Namespace) -> None:
    headline = primary[~primary["manuscript_role"].astype(str).str.contains("calibration_check")]
    lines = []
    for _, row in headline.iterrows():
        if str(row["manuscript_role"]) == "strict_seed_stable_headline_candidate":
            lines.append(
                f"- {row['target_row']}: strict seed-stable transition at top-score budget "
                f"{row['top_score_first_strict_budget']}; random baseline {row['random_baseline_status']}; "
                f"efficiency {row['top_score_vs_random_efficiency_gain']}."
            )
        elif str(row["manuscript_role"]) == "mean_operating_boundary_secondary":
            lines.append(
                f"- {row['target_row']}: mean-operating transition at top-score budget "
                f"{row['top_score_first_mean_operating_budget']} with seed-level alpha-violation rate "
                f"{row['top_score_alpha_violation_rate_at_mean_operating']}; report as boundary/secondary, not strict headline."
            )
        else:
            lines.append(f"- {row['target_row']}: no transition under the frozen paper-facing criteria.")
    (out_dir / "AUDIT_BUDGET_FRONTIER_HEADLINE_CLOSEOUT.md").write_text(
        "# Audit Budget Frontier Headline Package\n\n"
        "Status: completed paper-facing transition package.\n\n"
        "This package post-processes the completed simulated-audit frontier into lead numbers, "
        "policy-transition rows, and plot-ready source data. The headline transition criterion is "
        f"`safe_release_rate >= {args.min_safe_release_rate}` and `actual_FTR_mean <= alpha`. "
        "Rows that only meet the mean-operating criterion are explicitly secondary/boundary rows.\n\n"
        "## Lead Transitions\n\n"
        + "\n".join(lines)
        + "\n\n## Claim Boundary\n\n"
        "These are simulated audit-budget results over existing labels. They do not create new labels, "
        "do not modify A3, and do not support prospective materials-discovery wording. CGCNN K=100 is "
        "kept as a calibration/check row, not as a headline utility claim.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-summary", default="outputs/milestones/audit_budget_release_frontier/table_audit_budget_frontier_summary.csv")
    parser.add_argument("--extended-summary", default="outputs/milestones/audit_budget_release_frontier_extended/table_audit_budget_frontier_summary.csv")
    parser.add_argument("--out-dir", default="outputs/milestones/audit_budget_release_frontier_headline")
    parser.add_argument("--min-safe-release-rate", type=float, default=0.90)
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    default_summary = pd.read_csv(args.default_summary)
    extended_summary = pd.read_csv(args.extended_summary)
    primary, policy, figure = build_primary(default_summary, extended_summary, args.min_safe_release_rate)

    primary.to_csv(out_dir / "table_audit_budget_transition_primary.csv", index=False)
    policy.to_csv(out_dir / "table_audit_policy_efficiency.csv", index=False)
    figure.to_csv(out_dir / "figure_audit_budget_transition_source.csv", index=False)
    lead = primary[
        [
            "target_row",
            "manuscript_role",
            "top_score_first_strict_budget",
            "random_first_strict_budget",
            "random_baseline_status",
            "top_score_vs_random_efficiency_gain",
            "top_score_first_mean_operating_budget",
            "random_first_mean_operating_budget",
            "random_mean_operating_status",
            "top_score_vs_random_mean_operating_gain",
            "top_score_mean_release_at_transition",
            "top_score_actual_FTR_at_transition",
            "top_score_mean_release_at_mean_operating",
            "top_score_actual_FTR_at_mean_operating",
            "top_score_alpha_violation_rate_at_mean_operating",
            "claim_boundary",
        ]
    ].copy()
    lead.to_csv(out_dir / "table_audit_budget_frontier_lead_numbers.csv", index=False)
    write_closeout(out_dir, primary, policy, args)
    provenance = {
        "status": "completed",
        "evidence_status": "completed_paper_facing_postprocess",
        "min_safe_release_rate": args.min_safe_release_rate,
        "inputs": {
            "default_summary": args.default_summary,
            "default_summary_sha256": sha256_file(Path(args.default_summary)),
            "extended_summary": args.extended_summary,
            "extended_summary_sha256": sha256_file(Path(args.extended_summary)),
        },
        "claim_boundary": "simulated audit frontier; not prospective materials discovery; A3 unchanged",
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(out_dir)
    print(json.dumps(provenance, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
