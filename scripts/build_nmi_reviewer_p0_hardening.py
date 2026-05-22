#!/usr/bin/env python3
"""Aggregate P0 reviewer-risk hardening tables for the NMI package."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd
from scipy.stats import beta


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


def wilson_upper(x: int, n: int, z: float = 1.959963984540054) -> float:
    if n <= 0:
        return math.nan
    p = x / n
    denom = 1 + z * z / n
    center = p + z * z / (2 * n)
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return min(1.0, (center + half) / denom)


def jeffreys_upper(x: int, n: int, confidence: float = 0.95) -> float:
    if n <= 0:
        return math.nan
    return float(beta.ppf((1 + confidence) / 2, x + 0.5, n - x + 0.5))


def clopper_pearson_upper(x: int, n: int, confidence: float = 0.95) -> float:
    if n <= 0:
        return math.nan
    if x >= n:
        return 1.0
    return float(beta.ppf(confidence, x + 1, n - x))


def audit_uncertainty() -> pd.DataFrame:
    interval_path = Path("outputs/milestones/primary_statistics/table_audit_zero_ftr_intervals.csv")
    base = pd.read_csv(interval_path)
    rows = []
    for _, row in base.iterrows():
        n = int(row["n"])
        false = int(row["false"])
        rows.append(
            {
                "domain": row["domain"],
                "sample": row["sample"],
                "n_audited": n,
                "false_or_uncertain_as_false": false,
                "observed_FTR": float(row["observed_FTR"]),
                "clopper_pearson_upper95": clopper_pearson_upper(false, n),
                "wilson_upper95": wilson_upper(false, n),
                "jeffreys_upper95": jeffreys_upper(false, n),
                "source_artifact": str(interval_path),
                "source_sha256": sha256_file(interval_path),
                "claim_boundary": "zero observed false is reported with interval uncertainty; not universal zero-risk evidence",
            }
        )
    return pd.DataFrame(rows)


def baseline_frontier() -> pd.DataFrame:
    risk_path = Path("outputs/milestones/baseline_matrix_final/table_baseline_risk_utility_frontier.csv")
    props_path = Path("outputs/milestones/baseline_matrix_final/table_baseline_certificate_properties.csv")
    risk = pd.read_csv(risk_path)
    props = pd.read_csv(props_path)
    prop_rows = []
    for _, row in props.iterrows():
        prop_rows.append(
            {
                "method_key": str(row["method"]).lower(),
                "certificate_type": row["certificate_type"],
                "respects_compatibility": row["respects_compatibility"],
                "uses_null_superset": row["uses_null_superset"],
                "uses_SCS_denominator": row["uses_SCS_denominator"],
                "deployable": row["deployable"],
            }
        )
    prop = pd.DataFrame(prop_rows)

    def map_method(method: str) -> dict:
        lower = method.lower()
        if "parc" in lower:
            key = "parc"
        elif "raw top-k" in lower:
            key = "raw top-k"
        elif "nnpu" in lower:
            key = "nnpu classifier release"
        elif "bao" in lower:
            key = "bao-style selective conformal adaptation"
        else:
            key = lower
        hit = prop[prop["method_key"].eq(key)]
        return hit.iloc[0].to_dict() if not hit.empty else {}

    out = []
    for _, row in risk.iterrows():
        mapped = map_method(str(row["method"]))
        if "PARC" in str(row["method"]):
            role = "primary_method_set_level_certificate"
        elif "Raw top-K" in str(row["method"]):
            role = "same_budget_empirical_baseline_no_certificate"
        elif "oracle" in str(row["method"]).lower():
            role = "non_deployable_diagnostic"
        elif "nnPU" in str(row["method"]) or "Bao" in str(row["method"]):
            role = "different_target_baseline"
        else:
            role = "supporting_baseline"
        out.append(
            {
                "domain": row["domain"],
                "dataset": row["dataset"],
                "method": row["method"],
                "alpha": row["alpha"],
                "K": row["K"],
                "mean_release": row["mean_release"],
                "realized_FTR_mean": row["realized_FTR_mean"],
                "set_level_release_guarantee_reported": row["set_level_release_guarantee"],
                "certificate_type": mapped.get("certificate_type", ""),
                "respects_compatibility": mapped.get("respects_compatibility", ""),
                "uses_null_superset": mapped.get("uses_null_superset", ""),
                "uses_SCS_denominator": mapped.get("uses_SCS_denominator", ""),
                "deployable": mapped.get("deployable", ""),
                "main_text_comparison_role": role,
                "source_artifact": str(risk_path),
                "source_sha256": sha256_file(risk_path),
                "claim_boundary": "risk-utility comparator; target-object differences must be stated for non-PARC baselines",
            }
        )
    return pd.DataFrame(out)


def assumption_diagnostics() -> pd.DataFrame:
    specs = [
        (
            "materials_stability_definition",
            Path("outputs/milestones/materials_robustness_triad/table_stability_definition_robustness.csv"),
            "stability threshold sensitivity",
            "exact-stable remains primary; +25meV/margin rows are sensitivity",
        ),
        (
            "materials_block_definition",
            Path("outputs/milestones/materials_robustness_triad/table_block_definition_robustness.csv"),
            "block exchangeability / block definition sensitivity",
            "composition-family is primary; other block definitions are sensitivity",
        ),
        (
            "materials_gamma_sensitivity",
            Path("outputs/milestones/materials_robustness_triad/table_gamma_sensitivity.csv"),
            "calibrator gamma power frontier",
            "fixed gamma grid is power sensitivity, not validity tuning",
        ),
        (
            "block_size_superuniformity",
            Path("outputs/milestones/block_heterogeneity_robustness/table_block_size_heterogeneity_summary.csv"),
            "block-size heterogeneity and super-uniformity diagnostic",
            "assumption diagnostic, not a new positive release result",
        ),
        (
            "verified_positive_contamination",
            Path("outputs/milestones/verification_assumption_sensitivity/table_verified_positive_contamination_sensitivity_summary.csv"),
            "one-sided positive contamination sensitivity",
            "nonzero contamination rows are assumption-violation diagnostics, not formal guarantees",
        ),
        (
            "selector_optimality",
            Path("outputs/milestones/selector_optimality_diagnostics/table_mass_vs_graph_failure.csv"),
            "refusal failure attribution / ILP rescue check",
            "refusal rows must be attributed to evidence mass or finite resolution, not greedy miss",
        ),
    ]
    rows = []
    for diagnostic, path, concern, boundary in specs:
        frame = pd.read_csv(path)
        rows.append(
            {
                "diagnostic": diagnostic,
                "reviewer_concern": concern,
                "rows": len(frame),
                "source_artifact": str(path),
                "source_sha256": sha256_file(path),
                "main_text_role": "assumption_diagnostics_figure_candidate",
                "claim_boundary": boundary,
            }
        )
    return pd.DataFrame(rows)


def refusal_attribution() -> pd.DataFrame:
    mass_path = Path("outputs/milestones/selector_optimality_diagnostics/table_mass_vs_graph_failure.csv")
    mass = pd.read_csv(mass_path)
    rows = []
    for _, row in mass.iterrows():
        rows.append(
            {
                "row_id": row["row_id"],
                "domain": row["domain"],
                "K": row["K"],
                "alpha": row["alpha"],
                "release_status": row["release_status"],
                "required_e": row["required_e"],
                "max_e": row["max_e"],
                "evidence_mass_phi": row["evidence_mass_phi"],
                "ilp_feasible": row["ilp_feasible"],
                "failure_mode": row["failure_mode"],
                "mass_failure": row["mass_failure"],
                "finite_resolution_failure": row["finite_resolution_failure"],
                "selector_power_limitation": row["selector_power_limitation"],
                "paper_interpretation": "ILP/MIS cannot rescue this refusal before evidence-mass/finite-resolution gates",
                "source_artifact": str(mass_path),
                "source_sha256": sha256_file(mass_path),
            }
        )
    space_path = Path("outputs/milestones/spacenet_real_audit_final/table_spacenet_k100_refusal_diagnostics.csv")
    if space_path.exists():
        sp = pd.read_csv(space_path).iloc[0]
        rows.append(
            {
                "row_id": "spacenet_k100_alpha020_refusal",
                "domain": "earth_observation",
                "K": sp["K"],
                "alpha": sp["alpha"],
                "release_status": "certified_refusal",
                "required_e": sp["mean_required_e"],
                "max_e": sp["mean_max_observed_e"],
                "evidence_mass_phi": sp["mean_best_mass_ratio"],
                "ilp_feasible": False,
                "failure_mode": sp["dominant_failure_mode"],
                "mass_failure": True,
                "finite_resolution_failure": False,
                "selector_power_limitation": False,
                "paper_interpretation": sp["interpretation"],
                "source_artifact": str(space_path),
                "source_sha256": sha256_file(space_path),
            }
        )
    return pd.DataFrame(rows)


def p0_gap_matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "p0_item": "P0-1",
                "reviewer_need": "prospective / independent materials validation",
                "current_status": "not_completed_positive_evidence",
                "source_artifact": "outputs/milestones/materials_selection_conditional_discordance/table_selection_conditional_go_no_go.csv",
                "manuscript_action": "do not claim prospective materials discovery; keep A1/A2/A3 as diagnostic/no-go unless new DFT gates pass",
            },
            {
                "p0_item": "P0-2",
                "reviewer_need": "external or temporal materials labels",
                "current_status": "completed_negative_or_diagnostic_only",
                "source_artifact": "outputs/milestones/materials_source_discordance_stress_test/table_materials_external_source_stress_summary.csv",
                "manuscript_action": "use source-discordance as stress test, not validation success",
            },
            {
                "p0_item": "P0-3",
                "reviewer_need": "full baseline risk-utility frontier",
                "current_status": "completed_but_needs_main_text_centering",
                "source_artifact": "outputs/milestones/baseline_matrix_final/table_baseline_risk_utility_frontier.csv",
                "manuscript_action": "move target-object-aware frontier to main/extended data; do not imply non-PARC baselines solve same certificate object",
            },
            {
                "p0_item": "P0-4",
                "reviewer_need": "assumption diagnostics",
                "current_status": "completed_across_existing_artifacts",
                "source_artifact": "outputs/milestones/materials_robustness_triad/",
                "manuscript_action": "promote as one assumption-diagnostics figure; contamination remains assumption-violation diagnostic",
            },
            {
                "p0_item": "P0-5",
                "reviewer_need": "human audit uncertainty intervals",
                "current_status": "completed",
                "source_artifact": "outputs/milestones/primary_statistics/table_audit_zero_ftr_intervals.csv",
                "manuscript_action": "report zero-false audits with CP/Wilson/Jeffreys upper bounds, not just FTR=0",
            },
            {
                "p0_item": "P0-6",
                "reviewer_need": "refusal feasibility / greedy-vs-ILP attribution",
                "current_status": "completed_diagnostic",
                "source_artifact": "outputs/milestones/selector_optimality_diagnostics/table_mass_vs_graph_failure.csv",
                "manuscript_action": "attribute refusal to evidence-mass or finite-resolution gates; do not state greedy optimality where graph is unavailable",
            },
        ]
    )


def write_closeout(out_dir: Path, p0: pd.DataFrame, audit: pd.DataFrame, baseline: pd.DataFrame, refusal: pd.DataFrame) -> None:
    unresolved = p0[p0["current_status"].astype(str).str.contains("not_completed|diagnostic_only|negative", regex=True)]
    text = (
        "# NMI Reviewer P0 Hardening Closeout\n\n"
        "Status: completed aggregation package.\n\n"
        "This milestone does not create new prospective materials evidence. It converts existing completed "
        "baseline, audit, robustness, and selector diagnostics into reviewer-facing tables with explicit claim boundaries.\n\n"
        "## Key Boundaries\n\n"
        "- P0-1/P0-2 remain not completed positive materials evidence.\n"
        "- Baseline rows are target-object-aware risk-utility comparisons, not all direct replacements for PARC.\n"
        "- Zero-false human audit rows are reported with interval uncertainty.\n"
        "- Refusal rows are attributed to evidence-mass/finite-resolution failure where supported; greedy optimality is not fabricated.\n\n"
        "## Counts\n\n"
        f"- P0 matrix rows: {len(p0)}\n"
        f"- Audit uncertainty rows: {len(audit)}\n"
        f"- Baseline frontier rows: {len(baseline)}\n"
        f"- Refusal attribution rows: {len(refusal)}\n"
        f"- Unresolved positive-evidence gaps: {len(unresolved)}\n"
    )
    (out_dir / "NMI_REVIEWER_P0_HARDENING_CLOSEOUT.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/nmi_reviewer_p0_hardening")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    p0 = p0_gap_matrix()
    audit = audit_uncertainty()
    baseline = baseline_frontier()
    assumption = assumption_diagnostics()
    refusal = refusal_attribution()

    p0.to_csv(out_dir / "table_p0_reviewer_gap_action_matrix.csv", index=False)
    audit.to_csv(out_dir / "table_human_audit_uncertainty_intervals.csv", index=False)
    baseline.to_csv(out_dir / "table_baseline_frontier_maintext_map.csv", index=False)
    assumption.to_csv(out_dir / "table_assumption_diagnostics_maintext_map.csv", index=False)
    refusal.to_csv(out_dir / "table_refusal_feasibility_attribution.csv", index=False)

    write_closeout(out_dir, p0, audit, baseline, refusal)
    provenance = {
        "status": "completed",
        "evidence_status": "aggregation_from_completed_artifacts",
        "claim_boundary": "does not create prospective materials evidence; diagnostic rows remain scoped",
        "outputs": [
            "table_p0_reviewer_gap_action_matrix.csv",
            "table_human_audit_uncertainty_intervals.csv",
            "table_baseline_frontier_maintext_map.csv",
            "table_assumption_diagnostics_maintext_map.csv",
            "table_refusal_feasibility_attribution.csv",
            "NMI_REVIEWER_P0_HARDENING_CLOSEOUT.md",
        ],
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(out_dir)
    print(json.dumps(provenance, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
