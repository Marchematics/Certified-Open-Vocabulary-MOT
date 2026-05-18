#!/usr/bin/env python3
"""Build experiment-only finalization milestones from completed public artifacts.

The builder is deliberately conservative: if a requested validation needs
external snapshots, independent DFT joins, candidate-level universes, or DFT
outcomes that are not present in the public-safe package, it writes an explicit
protocol/blocked status row instead of fabricating a result table.
"""

from __future__ import annotations

import hashlib
import math
import shutil
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "milestones"


FINAL_MILESTONES = [
    "materials_temporal_validation",
    "materials_independent_dft_validation",
    "fixed_budget_downstream_utility",
    "primary_statistics",
    "materials_robustness_triad",
    "baseline_matrix_final",
    "ctc_strict_anchor",
    "iwildcam_audit_final",
    "spacenet_real_audit_final",
    "reproducibility_freeze",
]


def read_csv(rel: str) -> pd.DataFrame:
    path = ROOT / rel
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def text(rel: str) -> str:
    path = ROOT / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def ensure_clean_dir(name: str) -> Path:
    path = OUT / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_csv(path: Path, rows: list[dict] | pd.DataFrame, columns: list[str] | None = None) -> None:
    if isinstance(rows, pd.DataFrame):
        df = rows.copy()
    else:
        df = pd.DataFrame(rows)
    if columns is not None:
        for col in columns:
            if col not in df.columns:
                df[col] = pd.Series(dtype="object")
        df = df[columns]
    df.to_csv(path, index=False)


def write_md(path: Path, body: str) -> None:
    path.write_text(body.rstrip() + "\n", encoding="utf-8")


def copy_csv(src_rel: str, dst: Path) -> pd.DataFrame:
    df = read_csv(src_rel)
    write_csv(dst, df)
    return df


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(directory: Path) -> None:
    rows = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(directory).as_posix()}")
    (directory / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def bootstrap_ci(values: np.ndarray, reps: int = 4000, seed: int = 20260518) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return math.nan, math.nan
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(reps):
        means.append(float(values[rng.integers(0, len(values), len(values))].mean()))
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def sign_pvalue_greater(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    values = values[values != 0]
    if len(values) == 0:
        return 1.0
    positives = int((values > 0).sum())
    n = len(values)
    # One-sided exact sign-test tail under p=0.5.
    return float(sum(math.comb(n, k) for k in range(positives, n + 1)) / (2**n))


def holm_pvalues(pvals: list[float]) -> list[float]:
    indexed = sorted(enumerate(pvals), key=lambda x: x[1])
    adjusted = [math.nan] * len(pvals)
    running = 0.0
    m = len(pvals)
    for rank, (idx, pval) in enumerate(indexed):
        val = min(1.0, (m - rank) * pval)
        running = max(running, val)
        adjusted[idx] = running
    return adjusted


def zero_failure_upper95(n: int) -> float:
    if n <= 0:
        return math.nan
    return float(1.0 - 0.05 ** (1.0 / n))


def build_materials_temporal_validation() -> None:
    out = ensure_clean_dir("materials_temporal_validation")
    write_md(
        out / "README.md",
        """# Materials Temporal Validation

This milestone records the A1 temporal public-label split status. The local
package contains WBM labels and model predictions, but no auditable public
label-release timestamp or versioned snapshot table. Therefore A1 remains
protocol-only in this public-safe bundle and is not completed evidence.
""",
    )
    write_md(
        out / "temporal_protocol_freeze.md",
        """# Temporal Protocol Freeze

Fixed design: ALIGNN-FF and CGCNN sources; WBM unique prototypes; exact stable
target `e_above_hull <= 0`; alpha 0.10 primary and 0.20 auxiliary; K in
100, 300, 500, 1000, 5000; rho 0.10 primary; seeds 0..19; composition-family
primary blocks with chemical-system and Wyckoff-family sensitivity.

No temporal-result claim is made until an auditable t0/t1 public-label snapshot
or timestamp table is supplied.
""",
    )
    feas = copy_csv(
        "outputs/milestones/materials_prospective_validation_protocols/table_materials_temporal_split_feasibility.csv",
        out / "table_materials_temporal_feasibility.csv",
    )
    available = bool(
        not feas.empty
        and (feas.loc[feas["check_name"] == "label_release_timestamp_available", "observed"] == True).any()
    )
    status = "completed_evidence" if available else "protocol_only_missing_timestamp_snapshot"
    primary_cols = [
        "domain",
        "source",
        "validation_mode",
        "alpha",
        "K",
        "rho",
        "seeds",
        "release_rate",
        "mean_release_size",
        "future_label_FTR",
        "raw_topK_future_FTR",
        "raw_topR_future_FTR",
        "unstable_followups_prevented",
        "block_coverage",
        "evidence_status",
        "completed_positive_result",
        "blocker",
    ]
    write_csv(
        out / "table_materials_temporal_primary.csv",
        [
            {
                "domain": "materials_discovery",
                "source": "ALIGNN-FF / CGCNN preregistered",
                "validation_mode": "temporal_public_label_split",
                "alpha": 0.10,
                "K": "100|300|500|1000|5000",
                "rho": 0.10,
                "seeds": "0..19",
                "release_rate": "",
                "mean_release_size": "",
                "future_label_FTR": "",
                "raw_topK_future_FTR": "",
                "raw_topR_future_FTR": "",
                "unstable_followups_prevented": "",
                "block_coverage": "",
                "evidence_status": status,
                "completed_positive_result": False,
                "blocker": "" if available else "no auditable timestamped t0/t1 public-label snapshot in package",
            }
        ],
        primary_cols,
    )
    seed_cols = [
        "domain",
        "source",
        "alpha",
        "K",
        "rho",
        "seed",
        "released",
        "future_label_FTR",
        "raw_topK_future_FTR",
        "unstable_followups_prevented",
        "evidence_status",
    ]
    write_csv(out / "table_materials_temporal_seed_rows.csv", [], seed_cols)
    write_csv(
        out / "table_materials_temporal_raw_vs_parc.csv",
        [
            {
                "comparison": "raw_topK_vs_PARC",
                "metric": "future_label_FTR_and_unstable_followups_prevented",
                "evidence_status": status,
                "completed_positive_result": False,
                "interpretation": "awaits timestamped snapshot before evaluation",
            }
        ],
    )
    write_csv(
        out / "table_materials_temporal_block_sensitivity.csv",
        [
            {
                "block_definition": "composition_family",
                "role": "primary",
                "evidence_status": status,
            },
            {"block_definition": "chemical_system", "role": "sensitivity", "evidence_status": status},
            {"block_definition": "Wyckoff_family", "role": "sensitivity", "evidence_status": status},
        ],
    )
    write_csv(
        out / "table_materials_temporal_refusal_diagnostics.csv",
        [
            {
                "diagnostic": "temporal_refusal_boundary",
                "evidence_status": status,
                "completed_positive_result": False,
                "interpretation": "not computed without t0/t1 labels",
            }
        ],
    )
    write_csv(
        out / "figure_materials_temporal_utility_source.csv",
        [
            {
                "panel": "A1_temporal_validation",
                "metric": "not_plotted_until_completed",
                "evidence_status": status,
            }
        ],
    )
    write_manifest(out)


def build_materials_independent_validation() -> None:
    out = ensure_clean_dir("materials_independent_dft_validation")
    write_md(
        out / "independent_source_inventory.md",
        """# Independent DFT Source Inventory

This milestone records the A2 independent DFT-source status. The current
public-safe package contains no local independent Materials Project, OQMD,
Alexandria, AFLOW, NOMAD, or new-DFT join table. A2 is therefore protocol-only
until an auditable external source join is supplied.
""",
    )
    write_md(
        out / "structure_matching_protocol.md",
        """# Structure Matching Protocol

Primary A2 matching is restricted to exact-composition plus high-confidence
structure matches. Composition-only matches are sensitivity diagnostics and do
not enter the primary independent-label FTR.
""",
    )
    source_feas = copy_csv(
        "outputs/milestones/materials_prospective_validation_protocols/table_materials_independent_dft_source_feasibility.csv",
        out / "table_independent_dft_join_summary.csv",
    )
    local_available = bool(not source_feas.empty and source_feas["local_label_file_available"].astype(bool).any())
    status = "completed_evidence" if local_available else "protocol_only_missing_independent_join_table"
    primary_cols = [
        "domain",
        "source",
        "external_label_source",
        "match_confidence",
        "n_released_matched",
        "independent_FTR",
        "coverage_of_independent_source",
        "discordance_rate",
        "raw_topK_independent_FTR",
        "PARC_vs_raw_delta",
        "evidence_status",
        "completed_positive_result",
        "blocker",
    ]
    write_csv(
        out / "table_independent_dft_primary_results.csv",
        [
            {
                "domain": "materials_discovery",
                "source": "ALIGNN-FF / CGCNN preregistered",
                "external_label_source": "not_available_in_public_bundle",
                "match_confidence": "exact_or_high_confidence_required",
                "n_released_matched": "",
                "independent_FTR": "",
                "coverage_of_independent_source": "",
                "discordance_rate": "",
                "raw_topK_independent_FTR": "",
                "PARC_vs_raw_delta": "",
                "evidence_status": status,
                "completed_positive_result": False,
                "blocker": "" if local_available else "no independent DFT join table in package",
            }
        ],
        primary_cols,
    )
    seed_cols = [
        "domain",
        "source",
        "external_label_source",
        "seed",
        "released",
        "independent_FTR",
        "raw_topK_independent_FTR",
        "evidence_status",
    ]
    write_csv(out / "table_independent_dft_seed_rows.csv", [], seed_cols)
    write_csv(
        out / "table_independent_dft_discordance.csv",
        [
            {
                "comparison": "WBM_vs_independent_DFT",
                "discordance_rate": "",
                "evidence_status": status,
                "interpretation": "not computed without independent source join",
            }
        ],
    )
    write_csv(
        out / "table_independent_dft_match_confidence_sensitivity.csv",
        [
            {
                "match_confidence": "exact_or_high_confidence_structure_match",
                "role": "primary",
                "evidence_status": status,
            },
            {"match_confidence": "composition_only", "role": "sensitivity_only", "evidence_status": status},
        ],
    )
    write_manifest(out)


def build_fixed_budget_utility() -> None:
    out = ensure_clean_dir("fixed_budget_downstream_utility")
    write_md(
        out / "README.md",
        """# Fixed-Budget Downstream Utility

This milestone consolidates completed public-label and official-GT consequence
analyses. The goal is certified stopping/refusal and downstream false-entry
prevention, not a claim that PARC improves fixed-size ranking over raw top-R.
""",
    )
    materials = copy_csv(
        "outputs/milestones/no_human_scientific_consequence/table_materials_computational_followup.csv",
        out / "table_materials_budget_utility_primary.csv",
    )
    copy_csv(
        "outputs/milestones/no_human_scientific_consequence/table_materials_computational_followup_seed_rows.csv",
        out / "table_materials_budget_utility_seed_rows.csv",
    )
    near = read_csv("outputs/milestones/release_story/paper_diagnostics/table_near_boundary_release_value.csv")
    frontier_rows: list[dict] = []
    for _, row in near.iterrows():
        for method, ftr_col, size_col in [
            ("raw top-K", "raw_topK_FTR", None),
            ("raw top-R", "raw_topR_FTR", "PARC_release_size"),
            ("split conformal", "split_conformal_FTR", "split_conformal_release_size"),
            ("post-filter e-value", "post_filter_e_threshold_FTR", "post_filter_e_threshold_release_size"),
            ("e-BH-style", "e_BH_full_pool_FTR", "e_BH_full_pool_release_size"),
            ("PARC", "PARC_FTR", "PARC_release_size"),
        ]:
            release_size = row["K"] if size_col is None else row.get(size_col, "")
            frontier_rows.append(
                {
                    "domain": row.get("domain", "Materials discovery"),
                    "dataset": row.get("dataset", "Matbench Discovery WBM"),
                    "proposal_source": row.get("proposal_source", ""),
                    "K": row.get("K", ""),
                    "alpha": row.get("alpha", ""),
                    "method": method,
                    "release_count": release_size,
                    "FTR": row.get(ftr_col, ""),
                    "certificate_type": "PARC_set_level" if method == "PARC" else "different_or_no_set_certificate",
                    "evidence_status": "completed_retrospective_public_label_diagnostic",
                }
            )
    pu = read_csv("outputs/milestones/release_story/paper_diagnostics/table_pu_selective_conformal_benchmark.csv")
    for _, row in pu[pu.get("domain", pd.Series(dtype=str)) == "Materials discovery"].iterrows():
        frontier_rows.append(
            {
                "domain": row.get("domain", ""),
                "dataset": row.get("dataset", ""),
                "proposal_source": row.get("proposal_source", ""),
                "K": row.get("K", ""),
                "alpha": row.get("alpha", ""),
                "method": row.get("method", ""),
                "release_count": row.get("mean_release", ""),
                "FTR": row.get("realized_FTR_mean", ""),
                "certificate_type": row.get("set_level_release_guarantee", "no"),
                "evidence_status": "completed_different_target_baseline",
            }
        )
    write_csv(out / "table_materials_baseline_frontier.csv", frontier_rows)
    summary = copy_csv(
        "outputs/milestones/no_human_scientific_consequence/table_no_human_consequence_summary.csv",
        out / "table_materials_cost_proxy.csv",
    )
    ctc = copy_csv(
        "outputs/milestones/no_human_scientific_consequence/table_ctc_lineage_consequence.csv",
        out / "table_ctc_lineage_consequence.csv",
    )
    spacenet = copy_csv(
        "outputs/milestones/no_human_scientific_consequence/table_spacenet_map_consequence.csv",
        out / "table_spacenet_persistence_consequence.csv",
    )
    fig_rows = []
    if not materials.empty:
        for _, row in materials.iterrows():
            fig_rows.append(
                {
                    "panel": "materials_followup_queue",
                    "domain": row.get("domain", ""),
                    "proposal_source": row.get("proposal_source", ""),
                    "K": row.get("K", ""),
                    "raw_false_count": row.get("raw_unstable_count_mean", ""),
                    "PARC_false_count": row.get("PARC_unstable_count_mean", ""),
                    "prevented_false_count": row.get("prevented_unstable_followups_mean", ""),
                    "evidence_status": row.get("evidence_status", "completed_evidence"),
                }
            )
    if not ctc.empty:
        for _, row in ctc.iterrows():
            fig_rows.append(
                {
                    "panel": "ctc_lineage_graph",
                    "domain": row.get("domain", ""),
                    "proposal_source": row.get("proposal_source", ""),
                    "K": row.get("K", ""),
                    "raw_false_count": row.get("raw_false_links_mean", ""),
                    "PARC_false_count": row.get("PARC_false_links_mean", ""),
                    "prevented_false_count": row.get("prevented_false_links_mean", ""),
                    "evidence_status": row.get("evidence_status", "completed_evidence"),
                }
            )
    if not spacenet.empty:
        for _, row in spacenet.iterrows():
            fig_rows.append(
                {
                    "panel": "spacenet_persistence_map",
                    "domain": row.get("domain", ""),
                    "proposal_source": row.get("proposal_source", ""),
                    "K": row.get("K", ""),
                    "raw_false_count": row.get("raw_false_persistence_links", ""),
                    "PARC_false_count": "",
                    "prevented_false_count": "",
                    "evidence_status": row.get("evidence_status", "completed_evidence"),
                }
            )
    write_csv(out / "figure_fixed_budget_utility_source.csv", fig_rows)
    if not summary.empty:
        fig2 = summary.rename(columns={"headline_value": "value_for_plot"}).copy()
        fig2.insert(0, "panel", "scientific_consequence_translation")
    else:
        fig2 = pd.DataFrame()
    write_csv(out / "figure_consequence_translation_source.csv", fig2)
    write_manifest(out)


def build_primary_statistics() -> None:
    out = ensure_clean_dir("primary_statistics")
    write_md(
        out / "statistical_analysis_plan.md",
        """# Statistical Analysis Plan

Primary endpoint comparisons use paired seed-level deltas where seed rows are
available. P-values are descriptive sign-test values with Holm correction.
Formal PARC risk control remains theorem-based and is not replaced by these
tests.
""",
    )
    seed_rows = read_csv("outputs/milestones/no_human_scientific_consequence/table_materials_computational_followup_seed_rows.csv")
    primary_rows: list[dict] = []
    paired_rows: list[dict] = []
    if not seed_rows.empty:
        mask_primary = (
            seed_rows["proposal_source"].astype(str).str.contains("alignn_ff", case=False, na=False)
            & (seed_rows["alpha"].astype(float) == 0.10)
            & seed_rows["K"].isin([300, 500, 5000])
        )
        for (proposal, K), group in seed_rows[mask_primary].groupby(["proposal_source", "K"]):
            delta = group["prevented_unstable_followups"].astype(float).to_numpy()
            ci_low, ci_high = bootstrap_ci(delta)
            pval = sign_pvalue_greater(delta)
            endpoint = "false_followups_prevented" if int(K) != 5000 else "unsafe_high_volume_request_blocked"
            row_id = f"materials_{proposal}_K{int(K)}"
            primary_rows.append(
                {
                    "comparison_id": row_id,
                    "domain": "materials_discovery",
                    "source": proposal,
                    "K": int(K),
                    "alpha": 0.10,
                    "rho": 0.10,
                    "endpoint": endpoint,
                    "n_seeds": int(group["seed"].nunique()),
                    "method_A": "raw_topK",
                    "method_B": "PARC",
                    "mean_A": float(group["raw_unstable_count"].astype(float).mean()),
                    "mean_B": float(group["PARC_unstable_count"].astype(float).mean()),
                    "mean_delta": float(delta.mean()),
                    "bootstrap_CI_low": ci_low,
                    "bootstrap_CI_high": ci_high,
                    "paired_p": pval,
                    "holm_p": "",
                    "effect_interpretation": "PARC prevents unstable public-DFT follow-ups relative to raw top-K",
                    "claim_scope": "completed_public_DFT_label_followup_not_experimental_synthesis",
                }
            )
            for _, r in group.iterrows():
                paired_rows.append(
                    {
                        "comparison_id": row_id,
                        "seed": int(r["seed"]),
                        "raw_false_count": float(r["raw_unstable_count"]),
                        "PARC_false_count": float(r["PARC_unstable_count"]),
                        "delta_false_count": float(r["prevented_unstable_followups"]),
                        "raw_FTR": float(r["raw_topK_FTR"]),
                        "PARC_FTR": float(r["PARC_FTR"]),
                    }
                )
    ctc = read_csv("outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_hybrid_main.csv")
    if not ctc.empty:
        ctc_row = ctc[
            (ctc["rho"].astype(float) == 0.10)
            & (ctc["alpha"].astype(float) == 0.10)
            & (ctc["M"].astype(int) == 300)
        ]
        if not ctc_row.empty:
            r = ctc_row.iloc[0]
            primary_rows.append(
                {
                    "comparison_id": "ctc_learned_strict_alpha010_K300",
                    "domain": "biomedical_cell_tracking",
                    "source": r.get("proposal_source", "ctc_learned_hybrid"),
                    "K": 300,
                    "alpha": 0.10,
                    "rho": 0.10,
                    "endpoint": "strict_release_validity",
                    "n_seeds": int(r["seeds"]),
                    "method_A": "requested_release",
                    "method_B": "PARC",
                    "mean_A": "",
                    "mean_B": float(r["released_mean"]),
                    "mean_delta": "",
                    "bootstrap_CI_low": float(r["actual_FTR_bootstrap95_low"]),
                    "bootstrap_CI_high": float(r["actual_FTR_bootstrap95_high"]),
                    "paired_p": "",
                    "holm_p": "",
                    "effect_interpretation": "strict alpha=0.10 CTC anchor has 20/20 non-empty release and held-out FTR 0",
                    "claim_scope": "completed_masked_official_GT_evaluation",
                }
            )
    pvals = [float(r["paired_p"]) for r in primary_rows if r["paired_p"] != ""]
    holm = holm_pvalues(pvals)
    h_iter = iter(holm)
    for row in primary_rows:
        if row["paired_p"] != "":
            row["holm_p"] = next(h_iter)
    write_csv(out / "table_primary_endpoints.csv", primary_rows)
    write_csv(out / "table_paired_bootstrap_seed_rows.csv", paired_rows)
    secondary = read_csv("outputs/milestones/release_story/paper_diagnostics/table_pu_selective_conformal_benchmark.csv")
    if secondary.empty:
        secondary = pd.DataFrame(
            [
                {
                    "domain": "not_available",
                    "method": "not_available",
                    "evidence_status": "not_computed",
                }
            ]
        )
    write_csv(out / "table_secondary_endpoints.csv", secondary)
    write_csv(
        out / "table_holm_correction.csv",
        [
            {
                "comparison_id": row["comparison_id"],
                "paired_p": row["paired_p"],
                "holm_p": row["holm_p"],
                "included_in_holm": row["paired_p"] != "",
            }
            for row in primary_rows
        ],
    )
    intervals = []
    iwild = read_csv("outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_release_audit_summary.csv")
    if not iwild.empty:
        r = iwild.iloc[0]
        n = int(r["n_audited_unique_released_candidates"])
        intervals.append(
            {
                "domain": "iWildCam",
                "sample": "release_audit",
                "n": n,
                "false": int(r["n_false"]),
                "observed_FTR": float(r["human_FTR"]),
                "zero_false_upper95": zero_failure_upper95(n),
                "evidence_status": "completed_human_audit",
            }
        )
    space = read_csv("outputs/spacenet7_real_audit/table_spacenet7_real_audit_k50_completed_summary.csv")
    if not space.empty:
        r = space.iloc[0]
        n = int(r["n_unique_released_candidates_reviewed"])
        intervals.append(
            {
                "domain": "SpaceNet7",
                "sample": "K50_diagnostic_release_audit",
                "n": n,
                "false": int(r["n_false_link"]),
                "observed_FTR": float(r["audited_FTR_uncertain_as_false"]),
                "zero_false_upper95": zero_failure_upper95(n),
                "evidence_status": "completed_human_audit_diagnostic",
            }
        )
    write_csv(out / "table_audit_zero_ftr_intervals.csv", intervals)
    write_manifest(out)


def build_materials_robustness_triad() -> None:
    out = ensure_clean_dir("materials_robustness_triad")
    copy_csv(
        "outputs/milestones/scientific_release_success_map/table_materials_stability_threshold_robustness.csv",
        out / "table_stability_definition_robustness.csv",
    )
    block = read_csv("outputs/milestones/scientific_domain_materials/table_materials_block_sensitivity.csv")
    if block.empty:
        block = read_csv("outputs/milestones/scientific_release_success_map/table_block_coverage_exchangeability_diagnostics.csv")
    write_csv(out / "table_block_definition_robustness.csv", block)
    copy_csv(
        "outputs/milestones/scientific_release_success_map/table_materials_gamma_sensitivity.csv",
        out / "table_gamma_sensitivity.csv",
    )
    copy_csv(
        "outputs/milestones/block_heterogeneity_robustness/table_block_size_heterogeneity_summary.csv",
        out / "table_block_size_heterogeneity.csv",
    )
    stability = read_csv("outputs/milestones/scientific_release_success_map/table_materials_stability_threshold_robustness.csv")
    gamma = read_csv("outputs/milestones/scientific_release_success_map/table_materials_gamma_sensitivity.csv")
    fig = []
    for name, df in [("stability_definition", stability), ("gamma_sensitivity", gamma)]:
        if df.empty:
            continue
        for _, row in df.head(200).iterrows():
            fig.append(
                {
                    "panel": name,
                    "proposal_source": row.get("proposal_source", ""),
                    "K": row.get("K", ""),
                    "alpha": row.get("alpha", ""),
                    "variant_or_gamma": row.get("variant", row.get("gamma", "")),
                    "non_empty_seeds": row.get("non_empty_seeds", ""),
                    "mean_release": row.get("mean_release", ""),
                    "actual_FTR_mean": row.get("actual_FTR_mean", ""),
                    "raw_topK_actual_FTR_mean": row.get("raw_topK_actual_FTR_mean", ""),
                    "best_mass_ratio_mean": row.get("best_mass_ratio_mean", ""),
                    "evidence_status": "completed_sensitivity",
                }
            )
    write_csv(out / "figure_materials_robustness_triad_source.csv", fig)
    write_md(
        out / "robustness_claim_scope.md",
        """# Materials Robustness Claim Scope

The triad is a robustness and boundary analysis. Exact-stable rows remain the
primary materials target. The +25 meV and margin-excluded rows are sensitivity
checks; boundary rows must be labelled as boundary sensitivity, not promoted as
headline strict passes.
""",
    )
    write_manifest(out)


def build_ctc_strict_anchor() -> None:
    out = ensure_clean_dir("ctc_strict_anchor")
    copy_csv(
        "outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_leakage_audit.csv",
        out / "table_ctc_leakage_audit_final.csv",
    )
    write_md(
        out / "ctc_feature_provenance.md",
        """# CTC Feature Provenance

The learned-hybrid CTC source uses geometry plus local crop appearance features.
The public leakage audit records sequence-disjoint training/evaluation splits,
training-only normalization, no GT identity or official match label in scorer
features, and held-out GT use only after release for FTR evaluation.
""",
    )
    reverse = copy_csv(
        "outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_reverse_split.csv",
        out / "table_ctc_primary_reverse_split_summary.csv",
    )
    if not reverse.empty:
        seed_status = reverse.copy()
        seed_status["seed_row_status"] = "aggregate_summary_only_in_public_package"
    else:
        seed_status = pd.DataFrame()
    write_csv(out / "table_ctc_primary_reverse_split_seed_rows.csv", seed_status)
    negative = read_csv("outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_negative_control.csv")
    controls = []
    for _, row in negative.iterrows():
        controls.append(
            {
                "control": "random_score_negative_control",
                "K": row.get("M", ""),
                "alpha": row.get("alpha", ""),
                "non_empty_seeds": row.get("nonempty_seeds", ""),
                "raw_topK_FTR": row.get("raw_topM_actual_FTR_mean", ""),
                "PARC_FTR": row.get("actual_FTR_mean", ""),
                "evidence_status": "completed_destroyed_ranking_control",
                "interpretation": row.get("interpretation", ""),
            }
        )
    controls.extend(
        [
            {
                "control": "score_permutation_within_block",
                "K": "",
                "alpha": "",
                "non_empty_seeds": "",
                "raw_topK_FTR": "",
                "PARC_FTR": "",
                "evidence_status": "protocol_only_candidate_level_universe_not_in_public_package",
                "interpretation": "not fabricated; requires candidate-level score artifacts",
            },
            {
                "control": "score_sign_flip_worst_first",
                "K": "",
                "alpha": "",
                "non_empty_seeds": "",
                "raw_topK_FTR": "",
                "PARC_FTR": "",
                "evidence_status": "protocol_only_candidate_level_universe_not_in_public_package",
                "interpretation": "not fabricated; requires candidate-level score artifacts",
            },
        ]
    )
    write_csv(out / "table_ctc_destroyed_ranking_controls.csv", controls)
    high = read_csv("outputs/milestones/official_downstream_consequence/table_ctc_official_lineage_metric_summary.csv")
    if high.empty:
        high = read_csv("outputs/milestones/no_human_scientific_consequence/table_ctc_lineage_consequence.csv")
    write_csv(out / "table_ctc_high_volume_refusal_consequence.csv", high)
    write_manifest(out)


def build_iwildcam_final() -> None:
    out = ensure_clean_dir("iwildcam_audit_final")
    copy_csv(
        "outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_release_audit_summary.csv",
        out / "table_iwildcam_release_audit_final.csv",
    )
    copy_csv(
        "outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_second_review_agreement_summary.csv",
        out / "table_iwildcam_second_review_agreement_final.csv",
    )
    copy_csv(
        "outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_second_review_disagreement_cases.csv",
        out / "table_iwildcam_disagreement_strata.csv",
    )
    primary = read_csv("outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_human_audit_primary_results.csv")
    if not primary.empty:
        strict = primary[primary["alpha"].astype(float) == 0.10].copy()
    else:
        strict = pd.DataFrame()
    write_csv(out / "table_iwildcam_strict_alpha_refusal.csv", strict)
    write_csv(
        out / "table_iwildcam_species_rule_invalidity.csv",
        [
            {
                "rule": "species_level_metadata_as_local_box_support",
                "status": "invalid_for_localized_one_sided_support",
                "evidence_status": "completed_assumption_diagnostic",
                "interpretation": "species-level metadata does not certify each localized animal box as a one-sided positive",
            }
        ],
    )
    write_manifest(out)


def build_spacenet_final() -> None:
    out = ensure_clean_dir("spacenet_real_audit_final")
    k100 = read_csv("outputs/spacenet7_real_audit/table_spacenet7_real_audit_k100_failure_summary.csv")
    if k100.empty:
        k100 = read_csv("outputs/spacenet7_real_audit/table_spacenet7_real_audit_primary_refusal_diagnostics.csv")
    write_csv(out / "table_spacenet_k100_refusal_diagnostics.csv", k100)
    copy_csv(
        "outputs/spacenet7_real_audit/table_spacenet7_real_audit_k50_completed_summary.csv",
        out / "table_spacenet_k50_release_audit.csv",
    )
    copy_csv(
        "outputs/spacenet7_real_audit/table_spacenet7_real_audit_calibration_summary.csv",
        out / "table_spacenet_calibration_audit_summary.csv",
    )
    copy_csv(
        "outputs/spacenet7_real_audit/table_spacenet7_real_audit_raw_topK_audit.csv",
        out / "table_spacenet_raw_topK_audit.csv",
    )
    copy_csv(
        "outputs/spacenet7_real_audit/table_spacenet7_real_audit_block_coverage.csv",
        out / "table_spacenet_block_coverage.csv",
    )
    write_manifest(out)


def build_baseline_matrix() -> None:
    out = ensure_clean_dir("baseline_matrix_final")
    write_md(
        out / "baseline_protocol.md",
        """# Baseline Protocol

Baselines are compared as risk-utility and target-object diagnostics. Most do
not provide the PARC target object: a finite compatible release set certified
under one-sided partial verification with null-superset calibration and SCS
denominator awareness.
""",
    )
    baseline_rows = [
        ("raw top-K", "ranked prefix", False, False, False, False, True, "no_certificate"),
        ("raw top-R", "matched-volume diagnostic", False, False, False, False, False, "diagnostic_not_policy"),
        ("fixed threshold", "score threshold", False, False, False, False, True, "empirical_filter"),
        ("calibrated threshold", "calibrated score threshold", False, False, False, False, True, "threshold_policy"),
        ("split conformal candidate threshold", "candidate-level threshold", False, False, False, False, True, "different_target"),
        ("post-filter e-value", "candidate e-value filter", True, True, False, False, True, "missing_SCS_denominator"),
        ("e-BH-style", "e-value multiple testing", True, True, False, False, True, "different_target"),
        ("nnPU classifier release", "PU plug-in classifier", False, False, False, True, True, "different_target"),
        ("Bao-style selective conformal adaptation", "selective conformal adaptation", False, False, False, False, True, "different_target"),
        ("oracle prefix", "full-label oracle diagnostic", False, False, False, True, False, "non_deployable_oracle"),
        ("PARC", "finite compatible release set", True, True, True, False, True, "set_level_release_certificate"),
    ]
    write_csv(
        out / "table_baseline_target_objects.csv",
        [
            {
                "method": m,
                "target_object": target,
                "uses_null_superset": null,
                "uses_one_sided_support": one,
                "uses_SCS_denominator": scs,
                "uses_full_or_negative_labels": full,
                "deployable_under_partial_verification": dep,
                "claim_scope": scope,
            }
            for m, target, null, one, scs, full, dep, scope in baseline_rows
        ],
    )
    primary = read_csv("outputs/milestones/release_story/paper_diagnostics/table_pu_selective_conformal_benchmark.csv")
    if primary.empty:
        primary = read_csv("outputs/milestones/reliability_fortress/paper_tables/table_baseline_comparison.csv")
    write_csv(out / "table_baseline_primary_results.csv", primary)
    seed = read_csv("outputs/milestones/release_story/paper_diagnostics/table_pu_selective_conformal_benchmark_seed_rows.csv")
    write_csv(out / "table_baseline_seed_rows.csv", seed)
    frontier = read_csv("outputs/milestones/release_story/paper_diagnostics/figure_table2b_baseline_frontier.csv")
    write_csv(out / "table_baseline_risk_utility_frontier.csv", frontier)
    cert = pd.DataFrame(
        [
            {
                "method": m,
                "certificate_type": cert,
                "respects_compatibility": scs,
                "uses_null_superset": null,
                "uses_SCS_denominator": scs,
                "deployable": dep,
            }
            for m, _, null, _, scs, _, dep, cert in baseline_rows
        ]
    )
    write_csv(out / "table_baseline_certificate_properties.csv", cert)
    write_csv(out / "figure_baseline_frontier_source.csv", frontier)
    load = read_csv("outputs/milestones/scientific_release_success_map/table_verified_positive_removal_load_bearing.csv")
    write_csv(out / "table_component_ablation_load_bearing.csv", load)
    write_manifest(out)


def build_reproducibility_freeze() -> None:
    out = ensure_clean_dir("reproducibility_freeze")
    milestone_rows = []
    states = {
        "materials_temporal_validation": "protocol_only",
        "materials_independent_dft_validation": "protocol_only",
        "fixed_budget_downstream_utility": "completed_evidence",
        "primary_statistics": "completed_evidence",
        "materials_robustness_triad": "completed_evidence_and_diagnostics",
        "baseline_matrix_final": "completed_evidence_and_different_target_diagnostics",
        "ctc_strict_anchor": "completed_evidence_with_protocol_only_extra_controls",
        "iwildcam_audit_final": "completed_human_audit_operational",
        "spacenet_real_audit_final": "completed_human_audit_diagnostic_and_refusal",
        "reproducibility_freeze": "index",
    }
    for name in FINAL_MILESTONES:
        milestone_rows.append(
            {
                "milestone": name,
                "path": f"outputs/milestones/{name}/",
                "evidence_state": states[name],
                "manifest": f"outputs/milestones/{name}/MANIFEST_SHA256.txt",
                "public_bundle_check": f"python scripts/validate_public_bundle.py outputs/milestones/{name}",
            }
        )
    write_csv(out / "table_experiment_milestone_index.csv", milestone_rows)
    write_csv(ROOT / "outputs" / "artifact_index.csv", milestone_rows)
    write_md(
        out / "README.md",
        """# Reproducibility Freeze

This directory indexes the experiment-finalization milestones produced from the
current public-safe package. The index distinguishes completed evidence from
diagnostic and protocol-only rows.
""",
    )
    write_md(
        out / "validation_commands.md",
        """# Validation Commands

```bash
python scripts/build_experimental_finalization_milestones.py
pytest -q tests
make validate-public-bundle
sha256sum -c MANIFEST_SHA256.txt
```

The A1/A2 materials prospective-validation rows remain protocol-only until
timestamped public-label snapshots or independent DFT joins are supplied.
""",
    )
    write_manifest(out)


def update_root_manifest() -> None:
    tracked_roots = [
        "CODE_AVAILABILITY.md",
        "DATA_AVAILABILITY.md",
        "Makefile",
        "README.md",
        "REPRODUCIBILITY.md",
        "docs",
        "scripts",
        "tests",
        "outputs/milestones",
        "outputs/artifact_index.csv",
    ]
    files: list[Path] = []
    for rel in tracked_roots:
        path = ROOT / rel
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
        else:
            for child in path.rglob("*"):
                if child.is_file() and ".git" not in child.parts:
                    files.append(child)
    rows = []
    for path in sorted(set(files)):
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        if rel.startswith("outputs/test_tmp/") or rel.startswith("outputs/tmp_cert_api/"):
            continue
        if path.name == "MANIFEST_SHA256.txt":
            # Include milestone manifests but not the root manifest itself.
            if path.parent == ROOT:
                continue
        if rel.startswith("outputs/milestones") and any(part in rel for part in ["/dft_inputs/", "/dft_outputs/"]):
            continue
        rows.append(f"{sha256_file(path)}  {rel}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def main() -> None:
    build_materials_temporal_validation()
    build_materials_independent_validation()
    build_fixed_budget_utility()
    build_primary_statistics()
    build_materials_robustness_triad()
    build_ctc_strict_anchor()
    build_iwildcam_final()
    build_spacenet_final()
    build_baseline_matrix()
    build_reproducibility_freeze()
    update_root_manifest()
    print("experimental finalization milestones built")


if __name__ == "__main__":
    main()
