#!/usr/bin/env python3
"""Build T1 clean-acceptance hardening tables.

T1 has two jobs:
1. Audit whether independent/prospective materials validation can be used as
   positive evidence.
2. If not, produce a stronger empirical baseline frontier figure from completed
   baseline artifacts without promoting diagnostics or pending rows.
"""

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


def bool_text(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def missing_hash(value: object) -> bool:
    if pd.isna(value):
        return True
    text = str(value).strip()
    return not text or text.lower() == "nan"


def method_key(method: str) -> str:
    lower = method.lower().replace("_", " ").replace("-", " ")
    if "full parc" in lower or lower == "parc" or "parc certified" in lower:
        return "PARC"
    if "raw top" in lower or "raw top m" in lower:
        if "raw top r" in lower:
            return "raw top-R"
        return "raw top-K"
    if "fixed score threshold" in lower:
        return "fixed threshold"
    if "per-generator calibrated" in lower or "calibrated score" in lower:
        return "calibrated threshold"
    if "split conformal" in lower or "bao-style selective conformal adaptation" in lower:
        return "split conformal candidate threshold"
    if "post-filter" in lower or "post filter" in lower:
        return "post-filter e-value"
    if "e-bh" in lower or "e bh" in lower:
        return "e-BH-style"
    if "nnpu" in lower or "pu plug-in" in lower or "pu classifier" in lower:
        return "nnPU classifier release"
    if "bao-style selective conformal" in lower:
        return "Bao-style selective conformal adaptation"
    if "oracle" in lower:
        return "oracle prefix"
    return method


def certificate_lookup() -> dict[str, dict[str, object]]:
    props = pd.read_csv("outputs/milestones/baseline_matrix_final/table_baseline_certificate_properties.csv")
    target = pd.read_csv("outputs/milestones/baseline_matrix_final/table_baseline_target_objects.csv")
    merged = props.merge(target, on="method", how="outer", suffixes=("", "_target"))
    lookup = {}
    for _, row in merged.iterrows():
        lookup[str(row["method"])] = {
            "certificate_type": row.get("certificate_type", row.get("claim_scope", "")),
            "uses_null_superset": bool_text(row.get("uses_null_superset", False)),
            "uses_SCS_denominator": bool_text(row.get("uses_SCS_denominator", False)),
            "respects_compatibility": bool_text(row.get("respects_compatibility", False)),
            "deployable": bool_text(row.get("deployable", row.get("deployable_under_partial_verification", False))),
            "target_object": row.get("target_object", ""),
            "claim_scope": row.get("claim_scope", ""),
        }
    return lookup


def add_cert(row: dict[str, object], lookup: dict[str, dict[str, object]], key: str) -> dict[str, object]:
    cert = lookup.get(key, {})
    row.update(
        {
            "method_family": key,
            "certificate_type": cert.get("certificate_type", ""),
            "uses_null_superset": cert.get("uses_null_superset", False),
            "uses_SCS_denominator": cert.get("uses_SCS_denominator", False),
            "respects_compatibility": cert.get("respects_compatibility", False),
            "deployable": cert.get("deployable", False),
            "target_object": cert.get("target_object", ""),
        }
    )
    return row


def build_visual_baseline_rows(lookup: dict[str, dict[str, object]]) -> pd.DataFrame:
    path = Path("outputs/milestones/reliability_fortress/paper_tables/table_baseline_comparison.csv")
    frame = pd.read_csv(path)
    rows = []
    group_cols = ["dataset", "generator", "baseline", "certified_risk_level_alpha", "M"]
    for key, group in frame.groupby(group_cols, dropna=False):
        dataset, generator, method, alpha, k_value = key
        release = group["released"].astype(float)
        ftr = group["conservative_FTR"].dropna().astype(float)
        empirical = group["empirical_audited_FTR"].dropna().astype(float)
        method_family = method_key(str(method))
        rows.append(
            add_cert(
                {
                    "panel": "visual_full_baseline_matrix",
                    "domain": "visual_scientific_audit",
                    "dataset": dataset,
                    "proposal_source": generator,
                    "alpha": float(alpha),
                    "K": int(k_value),
                    "method": method,
                    "mean_release": float(release.mean()),
                    "release_rate": float((release > 0).mean()),
                    "FTR_mean": float(ftr.mean()) if len(ftr) else math.nan,
                    "empirical_FTR_mean": float(empirical.mean()) if len(empirical) else math.nan,
                    "seeds": int(group["seed"].nunique()),
                    "source_artifact": str(path),
                    "source_sha256": sha256_file(path),
                    "evidence_status": "completed_empirical_baseline_matrix",
                    "claim_boundary": "visual empirical baseline frontier; target-object differences remain explicit",
                },
                lookup,
                method_family,
            )
        )
    return pd.DataFrame(rows)


def build_materials_baseline_rows(lookup: dict[str, dict[str, object]]) -> pd.DataFrame:
    path = Path("outputs/milestones/fixed_budget_downstream_utility/table_materials_baseline_frontier.csv")
    frame = pd.read_csv(path)
    rows = []
    for _, row in frame.iterrows():
        method_family = method_key(str(row["method"]))
        release = float(row["release_count"]) if pd.notna(row["release_count"]) else 0.0
        ftr = float(row["FTR"]) if pd.notna(row["FTR"]) else math.nan
        rows.append(
            add_cert(
                {
                    "panel": "materials_public_dft_baseline_frontier",
                    "domain": row["domain"],
                    "dataset": row["dataset"],
                    "proposal_source": row["proposal_source"],
                    "alpha": float(row["alpha"]),
                    "K": int(row["K"]),
                    "method": row["method"],
                    "mean_release": release,
                    "release_rate": 1.0 if release > 0 else 0.0,
                    "FTR_mean": ftr,
                    "empirical_FTR_mean": ftr,
                    "seeds": "",
                    "source_artifact": str(path),
                    "source_sha256": sha256_file(path),
                    "evidence_status": row["evidence_status"],
                    "claim_boundary": "retrospective public-DFT baseline frontier; not prospective discovery",
                },
                lookup,
                method_family,
            )
        )
    return pd.DataFrame(rows)


def build_materials_utility_rows(lookup: dict[str, dict[str, object]]) -> pd.DataFrame:
    path = Path("outputs/milestones/materials_fixed_budget_scientific_utility/table_materials_fixed_budget_lead_numbers.csv")
    frame = pd.read_csv(path)
    frame = frame[
        frame["proposal_source"].eq("alignn_ff_modern_learned_materials_model")
        & frame["K"].isin([300, 500])
        & frame["alpha"].eq(0.10)
    ].copy()
    rows = []
    for _, row in frame.iterrows():
        for method, release_col, ftr_col, false_col in [
            ("Raw top-K", "K", "raw_topK_FTR_mean", "raw_unstable_count_mean"),
            ("Raw top-R", "mean_release", "raw_topR_FTR_mean", "PARC_unstable_count_mean"),
            ("PARC", "mean_release", "PARC_FTR_mean", "PARC_unstable_count_mean"),
        ]:
            release = float(row[release_col])
            ftr = float(row[ftr_col])
            false_count = float(row[false_col])
            rows.append(
                add_cert(
                    {
                        "panel": "materials_ALIGNN_fixed_budget_utility",
                        "domain": "Materials discovery",
                        "dataset": "Matbench Discovery WBM unique prototypes",
                        "proposal_source": row["proposal_source"],
                        "alpha": float(row["alpha"]),
                        "K": int(row["K"]),
                        "method": method,
                        "mean_release": release,
                        "release_rate": 1.0,
                        "FTR_mean": ftr,
                        "empirical_FTR_mean": ftr,
                        "false_followups_mean": false_count,
                        "prevented_unstable_followups_mean": float(row["prevented_unstable_followups_mean"])
                        if method == "PARC"
                        else 0.0,
                        "seeds": int(row["total_seeds"]),
                        "source_artifact": str(path),
                        "source_sha256": sha256_file(path),
                        "evidence_status": "completed_public_DFT_fixed_budget_utility",
                        "claim_boundary": "fixed-budget public-DFT utility; not prospective discovery; raw top-R is diagnostic",
                    },
                    lookup,
                    method_key(method),
                )
            )
    return pd.DataFrame(rows)


def build_baseline_frontier() -> tuple[pd.DataFrame, pd.DataFrame]:
    lookup = certificate_lookup()
    visual = build_visual_baseline_rows(lookup)
    materials = build_materials_baseline_rows(lookup)
    utility = build_materials_utility_rows(lookup)
    frontier = pd.concat([visual, materials, utility], ignore_index=True, sort=False)
    frontier["is_parc_certificate"] = frontier["method_family"].eq("PARC")
    frontier["has_full_release_certificate"] = (
        frontier["uses_null_superset"].astype(bool)
        & frontier["uses_SCS_denominator"].astype(bool)
        & frontier["respects_compatibility"].astype(bool)
    )
    frontier["false_count_mean"] = frontier["mean_release"].astype(float) * frontier["FTR_mean"].astype(float)
    families = [
        "raw top-K",
        "raw top-R",
        "fixed threshold",
        "calibrated threshold",
        "split conformal candidate threshold",
        "post-filter e-value",
        "e-BH-style",
        "nnPU classifier release",
        "Bao-style selective conformal adaptation",
        "PARC",
    ]
    rows = []
    for family in families:
        hit = frontier[frontier["method_family"].eq(family)]
        rows.append(
            {
                "method_family": family,
                "empirical_rows": int(len(hit)),
                "domains": ";".join(sorted(set(hit["domain"].astype(str)))) if len(hit) else "",
                "has_empirical_row": bool(len(hit)),
                "has_full_release_certificate": bool(hit["has_full_release_certificate"].any()) if len(hit) else False,
                "deployable": bool(hit["deployable"].astype(bool).any()) if len(hit) else False,
                "claim_boundary": (
                    "PARC is the only full set-level release certificate object"
                    if family == "PARC"
                    else "baseline comparator or different target object; not a PARC-style certificate"
                ),
            }
        )
    return frontier, pd.DataFrame(rows)


def build_materials_validation_ledger() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    temporal_path = Path("outputs/milestones/materials_temporal_replay_completed/table_temporal_primary.csv")
    temporal = pd.read_csv(temporal_path).iloc[0]
    rows.append(
        {
            "validation_route": "A1 temporal public-label replay",
            "source": "versioned t0/t1 public-label snapshots",
            "completed_positive_result": bool_text(temporal["completed_positive_result"]),
            "evidence_state": temporal["evidence_state"],
            "coverage_or_n": "",
            "FTR_or_discordance": "",
            "paper_role": "blocked_or_protocol_only",
            "source_artifact": str(temporal_path),
            "source_sha256": sha256_file(temporal_path),
            "claim_boundary": "cannot support prospective/quasi-prospective materials validation without timestamped snapshots",
        }
    )
    oqmd_path = Path("outputs/milestones/materials_independent_dft_validation/table_independent_dft_primary_results.csv")
    oqmd = pd.read_csv(oqmd_path).iloc[0]
    rows.append(
        {
            "validation_route": "A2 OQMD exact-structure cross-source validation",
            "source": oqmd["external_label_source"],
            "completed_positive_result": bool_text(oqmd["completed_positive_result"]),
            "evidence_state": oqmd["evidence_status"],
            "coverage_or_n": oqmd["n_unique_exact_structure_matches"],
            "FTR_or_discordance": oqmd["independent_FTR"],
            "paper_role": "low_coverage_negative_or_diagnostic",
            "source_artifact": str(oqmd_path),
            "source_sha256": sha256_file(oqmd_path),
            "claim_boundary": "formula-only hits excluded; exact-structure coverage too low and FTR not positive",
        }
    )
    stress_path = Path("outputs/milestones/materials_source_discordance_stress_test/table_materials_external_source_stress_summary.csv")
    stress = pd.read_csv(stress_path)
    for _, row in stress.iterrows():
        rows.append(
            {
                "validation_route": f"A2 {row['external_label_source']} exact-structure stress",
                "source": row["external_label_source"],
                "completed_positive_result": False,
                "evidence_state": row["claim_status"],
                "coverage_or_n": row["exact_matched_n"],
                "FTR_or_discordance": row["PARC_matched_FTR"],
                "paper_role": row["paper_role"],
                "source_artifact": str(stress_path),
                "source_sha256": sha256_file(stress_path),
                "claim_boundary": "external source stress test only; not positive independent validation",
            }
        )
    rows.append(
        {
            "validation_route": "A3 prospective DFT / MatterGen",
            "source": "local DFT/QE outcome gate",
            "completed_positive_result": False,
            "evidence_state": "not_completed_positive_evidence",
            "coverage_or_n": "",
            "FTR_or_discordance": "",
            "paper_role": "pending_or_failed_gate_not_headline",
            "source_artifact": "outputs/milestones/nmi_maintext_evidence_package/table_headline_evidence_hierarchy.csv",
            "source_sha256": sha256_file(
                Path("outputs/milestones/nmi_maintext_evidence_package/table_headline_evidence_hierarchy.csv")
            ),
            "claim_boundary": "no prospective materials discovery claim unless DFT gates are met",
        }
    )
    return pd.DataFrame(rows)


def build_lead_numbers(frontier: pd.DataFrame, validation: pd.DataFrame) -> pd.DataFrame:
    rows = []
    alignn = frontier[
        frontier["panel"].eq("materials_ALIGNN_fixed_budget_utility")
        & frontier["method_family"].isin(["raw top-K", "raw top-R", "PARC"])
    ].copy()
    for k_value, group in alignn.groupby("K"):
        parc = group[group["method_family"].eq("PARC")].iloc[0]
        raw = group[group["method_family"].eq("raw top-K")].iloc[0]
        rawr = group[group["method_family"].eq("raw top-R")].iloc[0]
        rows.append(
            {
                "lead_id": f"materials_ALIGNN_K{k_value}_fixed_budget",
                "manuscript_role": "baseline_frontier_support",
                "lead_number": (
                    f"ALIGNN K={int(k_value)} raw top-K FTR {raw['FTR_mean']:.3f}; PARC FTR "
                    f"{parc['FTR_mean']:.3f}; raw top-R matched FTR {rawr['FTR_mean']:.3f}; "
                    f"unstable follow-ups prevented {parc.get('prevented_unstable_followups_mean', 0.0):.2f}."
                ),
                "source_artifact": parc["source_artifact"],
                "source_sha256": parc["source_sha256"],
                "claim_boundary": "fixed-budget utility; raw top-R separates smaller-queue effect from ranking improvement",
            }
        )
    cgcnn = frontier[
        frontier["panel"].eq("materials_public_dft_baseline_frontier")
        & frontier["proposal_source"].astype(str).str.contains("CGCNN")
        & frontier["K"].eq(500)
        & frontier["alpha"].eq(0.10)
    ]
    if not cgcnn.empty:
        methods = {row["method_family"]: row for _, row in cgcnn.iterrows()}
        if "PARC" in methods and "raw top-K" in methods and "post-filter e-value" in methods:
            rows.append(
                {
                    "lead_id": "materials_CGCNN_K500_baseline_frontier",
                    "manuscript_role": "empirical_baseline_frontier_figure",
                    "lead_number": (
                        f"CGCNN K=500 baseline frontier: raw top-K FTR {methods['raw top-K']['FTR_mean']:.3f}, "
                        f"post-filter e-value FTR {methods['post-filter e-value']['FTR_mean']:.3f}, "
                        f"PARC/raw top-R FTR {methods['PARC']['FTR_mean']:.3f}; e-BH releases no candidates."
                    ),
                    "source_artifact": methods["PARC"]["source_artifact"],
                    "source_sha256": methods["PARC"]["source_sha256"],
                    "claim_boundary": "retrospective public-DFT baseline frontier; not prospective discovery",
                }
            )
    families = pd.Series(frontier["method_family"].unique()).sort_values().tolist()
    rows.append(
        {
            "lead_id": "baseline_family_coverage",
            "manuscript_role": "clean_acceptance_support",
            "lead_number": f"Empirical frontier includes {len(families)} method families: {', '.join(families)}.",
            "source_artifact": "outputs/milestones/t1_clean_acceptance_package/table_t1_baseline_frontier_summary.csv",
            "source_sha256": "",
            "claim_boundary": "family coverage is empirical artifact coverage, not equality of target objects",
        }
    )
    blocked = validation[~validation["completed_positive_result"].astype(bool)]
    rows.append(
        {
            "lead_id": "materials_independent_validation_gate",
            "manuscript_role": "explicit_no_go_boundary",
            "lead_number": f"{len(blocked)}/{len(validation)} materials independent/prospective validation routes are not positive evidence.",
            "source_artifact": "outputs/milestones/t1_clean_acceptance_package/table_t1_materials_validation_go_no_go.csv",
            "source_sha256": "",
            "claim_boundary": "do not claim independent/prospective materials validation success",
        }
    )
    return pd.DataFrame(rows)


def write_closeout(out_dir: Path, leads: pd.DataFrame) -> None:
    lead_text = "\n".join(f"- {row['lead_id']}: {row['lead_number']}" for _, row in leads.iterrows())
    text = (
        "# T1 Clean Acceptance Package\n\n"
        "Status: completed empirical baseline-frontier hardening plus materials validation gate ledger.\n\n"
        "This package responds to the T1 clean-acceptance gap by strengthening the empirical baseline "
        "frontier while preserving the materials-validation boundary. It does not convert A1/A2/A3 "
        "diagnostics into positive evidence.\n\n"
        "## Lead Numbers\n\n"
        f"{lead_text}\n\n"
        "## Claim Boundary\n\n"
        "- Materials independent/prospective validation remains unavailable or negative/diagnostic.\n"
        "- The baseline frontier is empirical and target-object-aware; only PARC rows have the full null-superset + SCS release certificate.\n"
        "- Raw top-R is a matched-volume diagnostic, not an independent deployable policy.\n"
        "- A3 remains outside positive evidence unless future DFT gates are met.\n"
    )
    (out_dir / "T1_CLEAN_ACCEPTANCE_CLOSEOUT.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/t1_clean_acceptance_package")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    frontier, coverage = build_baseline_frontier()
    validation = build_materials_validation_ledger()
    leads = build_lead_numbers(frontier, validation)

    frontier.to_csv(out_dir / "table_t1_baseline_frontier_summary.csv", index=False)
    frontier.to_csv(out_dir / "figure_t1_empirical_baseline_frontier_source.csv", index=False)
    coverage.to_csv(out_dir / "table_t1_baseline_family_coverage.csv", index=False)
    validation.to_csv(out_dir / "table_t1_materials_validation_go_no_go.csv", index=False)
    leads.to_csv(out_dir / "table_t1_clean_acceptance_lead_numbers.csv", index=False)
    # Fill self hashes for the rows that point to tables generated in this package.
    lead_path = out_dir / "table_t1_clean_acceptance_lead_numbers.csv"
    leads = pd.read_csv(lead_path)
    generated_hashes = {
        "outputs/milestones/t1_clean_acceptance_package/table_t1_baseline_frontier_summary.csv": sha256_file(
            out_dir / "table_t1_baseline_frontier_summary.csv"
        ),
        "outputs/milestones/t1_clean_acceptance_package/table_t1_materials_validation_go_no_go.csv": sha256_file(
            out_dir / "table_t1_materials_validation_go_no_go.csv"
        ),
    }
    for idx, row in leads.iterrows():
        if missing_hash(row["source_sha256"]):
            leads.loc[idx, "source_sha256"] = generated_hashes.get(str(row["source_artifact"]), "")
    leads.to_csv(lead_path, index=False)

    write_closeout(out_dir, leads)
    provenance = {
        "status": "completed",
        "evidence_status": "completed_T1_clean_acceptance_hardening",
        "outputs": [
            "table_t1_baseline_frontier_summary.csv",
            "figure_t1_empirical_baseline_frontier_source.csv",
            "table_t1_baseline_family_coverage.csv",
            "table_t1_materials_validation_go_no_go.csv",
            "table_t1_clean_acceptance_lead_numbers.csv",
        ],
        "claim_boundary": "stronger empirical baseline frontier; materials validation remains no-go/diagnostic",
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(out_dir)
    print(json.dumps(provenance, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
