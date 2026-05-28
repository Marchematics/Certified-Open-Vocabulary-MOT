#!/usr/bin/env python3
"""Build NCS Phase50/51 materials paperization artifacts.

Phase50 turns the current-MP t0/t1 hull-shift audit into paper-facing
tables/figure inputs. Phase51 builds a candidate-level explanation table for
the same frozen K=300/500 WBM queues. The Phase51 output is intentionally
honest about model availability: WBM queue candidates have ALIGNN-FF, CGCNN,
and MEGNet prediction files in the local Matbench cache, but no public-safe
candidate-level CHGNet or MACE-MP structure scores for the 1,191-candidate
queue. Therefore Phase51 is a candidate-level explanation/model-zoo diagnostic,
not an MLIP consensus validation claim.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHASE49 = ROOT / "outputs/milestones/materials_t0_t1_snapshot_acquisition"
QUEUE = ROOT / "outputs/milestones/materials_queue_source_uncertainty_overlay/table_materials_queue_overlay_candidate_rows.csv"
OUT50 = ROOT / "outputs/milestones/ncs_phase50_materials_version_shift_paperization"
OUT51 = ROOT / "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation"

PRED_SOURCES = {
    "alignn_ff": Path("/home/waas/paper_experiments/data/matbench_discovery/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz"),
    "cgcnn_ens10": Path("/home/waas/paper_experiments/data/matbench_discovery/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz"),
    "megnet": Path("/home/waas/paper_experiments/data/matbench_discovery/2022-11-18-megnet-wbm-IS2RE.csv.gz"),
}
PUBLIC_SOURCE_IDS = {
    "alignn_ff": "local_private_matbench_discovery_cache/2023-07-11-alignn-ff-wbm-IS2RE.csv.gz",
    "cgcnn_ens10": "local_private_matbench_discovery_cache/2023-01-26-cgcnn-ens10-wbm-IS2RE.csv.gz",
    "megnet": "local_private_matbench_discovery_cache/2022-11-18-megnet-wbm-IS2RE.csv.gz",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_phase50() -> None:
    OUT50.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(PHASE49 / "table_t1_hull_ftr_summary.csv")
    delta = pd.read_csv(PHASE49 / "table_t1_hull_ftr_delta.csv")
    gates = pd.read_csv(PHASE49 / "table_t0_t1_gate_assessment.csv")
    joined = pd.read_csv(PHASE49 / "table_t0_t1_label_join.csv")

    summary_rows = summary.merge(
        delta[
            [
                "K",
                "raw_minus_PARC_FTR_t1",
                "drift_rate_delta_PARC_minus_raw",
            ]
        ],
        on="K",
        how="left",
    )
    summary_rows["alpha_reference_line"] = 0.10
    summary_rows["paper_interpretation"] = (
        "current_MP_version_shift_utility_audit_not_strict_alpha_certificate"
    )
    summary_rows["selection_frozen_before_t1"] = True
    summary_rows["t1_used_for_calibration_or_release_selection"] = False
    summary_rows.to_csv(OUT50 / "table_materials_t1_hull_shift_summary.csv", index=False)

    fig_rows: list[dict[str, object]] = []
    for row in summary.to_dict("records"):
        for metric, label in [
            ("FTR_t1_current_mp", "conservative_t1_false_release_fraction"),
            ("stable_to_unstable_rate", "stable_to_unstable_drift_rate"),
        ]:
            fig_rows.append(
                {
                    "panel": "current_MP_t1_hull_shift",
                    "K": row["K"],
                    "arm": row["arm"],
                    "metric": label,
                    "value": row[metric],
                    "alpha_reference_line": 0.10,
                    "n_unique_candidates": row["n_unique_candidates"],
                    "unresolved_counted_as_false": row["unresolved_counted_as_false"],
                    "paper_interpretation": "version_shift_utility_not_t1_certificate",
                }
            )
    pd.DataFrame(fig_rows).to_csv(OUT50 / "figure_materials_version_shift_inputs.csv", index=False)

    drift_rows: list[dict[str, object]] = []
    for k in [300, 500]:
        for arm, col in [
            ("PARC_release", f"K{k}_PARC_release_seed_count"),
            ("raw_topK", f"K{k}_raw_topK_requested_budget_seed_count"),
        ]:
            subset = joined[joined[col] > 0]
            denom = len(subset)
            counts = subset["drift_class"].value_counts().to_dict()
            for drift_class in [
                "stable_to_stable",
                "stable_to_unstable",
                "stable_to_unresolved",
                "unstable_to_stable",
                "unstable_to_unstable",
                "unstable_to_unresolved",
            ]:
                count = int(counts.get(drift_class, 0))
                drift_rows.append(
                    {
                        "K": k,
                        "arm": arm,
                        "drift_class": drift_class,
                        "n": count,
                        "rate": count / denom if denom else 0.0,
                        "denominator": denom,
                    }
                )
    pd.DataFrame(drift_rows).to_csv(OUT50 / "table_materials_drift_matrix.csv", index=False)

    evidence_rows = gates.copy()
    evidence_rows["manuscript_role"] = evidence_rows["gate"].map(
        {
            "t0_t1_current_MP_snapshot_acquired": "supporting_evidence",
            "PARC_release_lower_t1_FTR_than_raw_topK": "materials_flagship_utility_audit",
            "stable_to_unstable_drift_not_concentrated_in_PARC": "materials_flagship_utility_audit",
            "strict_alpha010_t1_hull_certificate": "claim_boundary",
            "unresolved_current_MP_hull_labels_tracked_conservatively": "audit_hygiene",
            "overall_t0_t1_hull_shift_audit": "claim_scope",
        }
    )
    evidence_rows["allowed_manuscript_sentence"] = evidence_rows["gate"].map(
        {
            "PARC_release_lower_t1_FTR_than_raw_topK": (
                "Under a current Materials Project hull update, the frozen PARC "
                "queues retain lower conservative current-label FTR than the "
                "corresponding raw top-K queues."
            ),
            "stable_to_unstable_drift_not_concentrated_in_PARC": (
                "Stable-to-unstable version drift is not more concentrated in "
                "the PARC release than in the raw top-K queue."
            ),
            "strict_alpha010_t1_hull_certificate": (
                "The current-MP audit is not a strict alpha=0.10 temporal "
                "certificate because PARC FTR remains above alpha under t1."
            ),
            "overall_t0_t1_hull_shift_audit": (
                "This is a completed version-shift utility diagnostic, not a "
                "prospective materials-discovery claim."
            ),
        }
    ).fillna("")
    evidence_rows.to_csv(OUT50 / "table_materials_evidence_status.csv", index=False)

    display_items = [
        {
            "display_item": "Figure 1",
            "role": "method",
            "title": "PARC release certificate for finite computational-science queues",
            "source_artifact": "manual_schematic",
            "claim_boundary": "theorem intuition and release/refuse interface",
        },
        {
            "display_item": "Figure 2",
            "role": "materials_t0",
            "title": "WBM t0 certified stopping and high-volume refusal",
            "source_artifact": "outputs/milestones/materials_fixed_budget_scientific_utility/",
            "claim_boundary": "t0 public-label certificate/utility, not synthesis",
        },
        {
            "display_item": "Figure 3",
            "role": "materials_t1",
            "title": "Current-MP hull-shift utility audit",
            "source_artifact": rel(OUT50 / "figure_materials_version_shift_inputs.csv"),
            "claim_boundary": "version-shift utility diagnostic, not strict t1 certificate",
        },
        {
            "display_item": "Figure 4",
            "role": "materials_explanation",
            "title": "Candidate-level explanation of current-label failures",
            "source_artifact": "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation/",
            "claim_boundary": "boundary/model-zoo diagnostic, not MLIP consensus validation",
        },
        {
            "display_item": "Figure 5",
            "role": "ctc_strict",
            "title": "CTC strict one-sided release under scarce positives",
            "source_artifact": "outputs/milestones/ctc_decision_utility_main_evidence/",
            "claim_boundary": "strict second-domain validation, not tracker leaderboard claim",
        },
        {
            "display_item": "Figure 6",
            "role": "operating_envelope",
            "title": "Release/refusal envelope and diagnostics",
            "source_artifact": "outputs/milestones/submission_scope_lock_phase37/",
            "claim_boundary": "operating envelope; no broad all-domain success claim",
        },
    ]
    write_csv(
        OUT50 / "table_ncs_display_item_plan.csv",
        display_items,
        ["display_item", "role", "title", "source_artifact", "claim_boundary"],
    )

    abstract = (
        "Scientific computing pipelines increasingly generate ranked candidate "
        "objects faster than they can be exhaustively verified. We introduce "
        "PARC, a post hoc release-certification method for frozen candidate "
        "queues under one-sided partial verification. PARC removes only verified "
        "positives from calibration blocks, keeps all other candidates in a "
        "conservative null superset, constructs block-maximum e-values and "
        "releases a compatible set only when a self-consistency rule controls "
        "the expected false-release fraction; otherwise it returns a certified "
        "refusal. In WBM materials screening, PARC converts public model "
        "rankings into shorter certified follow-up queues and refuses unsupported "
        "high-volume release. Under a 2022-to-2025 Materials Project hull update, "
        "the same releases retain lower current-label FTR than raw top-K queues "
        "without concentrating stable-to-unstable drift. In CTC cell tracking, "
        "scarce score-targeted positive verification certifies high-confidence "
        "lineage links with no observed false releases. PARC provides a versioned "
        "release layer for computational-science workflows under scarce verification."
    )
    (OUT50 / "ncs_abstract_materials_first_draft.md").write_text(abstract + "\n", encoding="utf-8")

    closeout = f"""# NCS Phase50 Materials Version-Shift Paperization

Status: `completed_paper_facing_current_MP_hull_shift_utility_diagnostic`

This milestone paperizes Phase49 as an NCS-facing materials result. It uses the
same frozen K=300/500 WBM candidates and evaluates them under the current
Materials Project `2025.09.25` hull without using t1 labels for calibration or
release selection.

Allowed main-text claim:

> Under a current Materials Project hull update, frozen PARC materials queues
> retain lower conservative current-label FTR than raw top-K queues, and
> stable-to-unstable version drift is not more concentrated in the PARC release.

Forbidden claim:

> PARC controls t1 FTR at alpha=0.10 or proves prospective materials discovery.

Reason: `table_materials_evidence_status.csv` records that the utility and
drift gates pass, while the strict alpha=0.10 t1 certificate gate fails.

NCS format note: the display-item plan is constrained to six items and the
abstract draft is intended to stay within the Nature Computational Science
Article limit.
"""
    (OUT50 / "NCS_PHASE50_MATERIALS_VERSION_SHIFT_PAPERIZATION.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase50_materials_version_shift_paperization",
        "source_phase49": rel(PHASE49),
        "source_phase49_manifest_sha256": sha256_file(PHASE49 / "MANIFEST_SHA256.txt"),
        "evidence_status": "completed_paper_facing_current_MP_hull_shift_utility_diagnostic",
        "claim_boundary": [
            "not_strict_alpha010_t1_certificate",
            "not_prospective_materials_discovery",
            "t1_not_used_for_calibration_or_selection",
        ],
    }
    (OUT50 / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(OUT50)


def load_model_predictions(target_ids: set[str]) -> pd.DataFrame:
    base = pd.DataFrame({"material_id": sorted(target_ids)})
    alignn = pd.read_csv(PRED_SOURCES["alignn_ff"])
    alignn = alignn[alignn["material_id"].isin(target_ids)].copy()
    alignn = alignn.rename(columns={"e_form_per_atom_alignn_ff": "alignn_ff_pred_e_form"})
    base = base.merge(alignn[["material_id", "alignn_ff_pred_e_form"]], on="material_id", how="left")

    cgcnn = pd.read_csv(PRED_SOURCES["cgcnn_ens10"])
    cgcnn = cgcnn[cgcnn["material_id"].isin(target_ids)].copy()
    cgcnn = cgcnn.rename(columns={"e_form_per_atom_mp2020_corrected_pred_ens": "cgcnn_ens10_pred_e_form"})
    base = base.merge(cgcnn[["material_id", "cgcnn_ens10_pred_e_form"]], on="material_id", how="left")

    megnet = pd.read_csv(PRED_SOURCES["megnet"])
    megnet = megnet[megnet["material_id"].isin(target_ids)].copy()
    megnet = megnet.rename(columns={"e_form_per_atom_megnet": "megnet_pred_e_form"})
    base = base.merge(megnet[["material_id", "megnet_pred_e_form"]], on="material_id", how="left")
    return base


def aggregate_queue_rows() -> pd.DataFrame:
    queue = pd.read_csv(QUEUE)
    queue = queue[queue["K"].isin([300, 500])].copy()
    agg = (
        queue.groupby(["material_id", "K"], as_index=False)
        .agg(
            formula=("formula", "first"),
            chemical_system=("chemical_system", "first"),
            composition_family_pair=("composition_family_pair", "first"),
            parc_seed_count=("arm", lambda s: int((s == "PARC_release").sum())),
            raw_topK_seed_count=("arm", lambda s: int((s == "raw_topK_requested_budget").sum())),
            raw_topR_seed_count=("arm", lambda s: int((s == "raw_topR_matched_release_size").sum())),
            raw_only_tail_seed_count=("arm", lambda s: int((s == "raw_only_rejected_tail").sum())),
            alignn_score=("alignn_score", "first"),
            alignn_predicted_e_above_hull=("alignn_predicted_e_above_hull", "first"),
            raw_rank=("raw_rank_within_test", "min"),
            parc_e_value=("_evalue", "max"),
            required_e=("required_e", "max"),
            best_mass_ratio=("best_mass_ratio", "max"),
            self_consistency_margin=("self_consistency_margin", "max"),
            source_uncertain_or_boundary_exact=("source_uncertain_or_boundary_exact", "max"),
            source_discordant_exact=("source_discordant_exact", "max"),
            either_source_near_hull_25meV_exact=("either_source_near_hull_25meV_exact", "max"),
            included_in_alex_exact_metrics=("included_in_alex_exact_metrics", "max"),
        )
    )
    return agg


def classify_false_explanation(row: pd.Series) -> str:
    if row["t1_label_status"] != "labelable_current_MP_hull":
        return "unresolved_current_MP_hull_reference"
    if not bool(row["t1_false_conservative"]):
        return "t1_stable_or_true_release"
    if bool(row["near_hull_25mev_t0_or_t1"]):
        return "near_hull_25meV_boundary"
    if bool(row["near_hull_50mev_t0_or_t1"]):
        return "near_hull_50meV_boundary"
    if bool(row["alignn_disagrees_with_t1"]):
        return "ALIGNN_FF_disagrees_with_current_MP_label"
    if bool(row["source_uncertain_or_boundary_exact"]):
        return "alex_MP_source_uncertainty_or_boundary_tag"
    return "far_from_hull_no_available_model_explanation"


def build_phase51() -> None:
    OUT51.mkdir(parents=True, exist_ok=True)
    t1 = pd.read_csv(PHASE49 / "table_t0_t1_label_join.csv")
    queue = aggregate_queue_rows()
    preds = load_model_predictions(set(t1["material_id"]))
    rows = queue.merge(t1, on=["material_id", "formula", "chemical_system"], how="left").merge(
        preds, on="material_id", how="left"
    )
    rows["primary_queue_status"] = "outside_raw_topK"
    rows.loc[rows["raw_topK_seed_count"] > 0, "primary_queue_status"] = "raw_topK_requested_budget"
    rows.loc[
        (rows["raw_topK_seed_count"] > 0) & (rows["parc_seed_count"] == 0),
        "primary_queue_status",
    ] = "raw_only_requested_budget"
    rows.loc[rows["parc_seed_count"] > 0, "primary_queue_status"] = "PARC_release"
    rows["raw_topR_member"] = rows["raw_topR_seed_count"] > 0
    rows["t1_false_conservative"] = ~rows["stable_exact_t1_current_mp"].astype(bool)
    rows["near_hull_25mev_t0"] = rows["e_above_hull_t0"].abs() <= 0.025
    rows["near_hull_25mev_t1"] = rows["e_above_hull_t1_current_mp"].abs() <= 0.025
    rows["near_hull_25mev_t0_or_t1"] = rows["near_hull_25mev_t0"] | rows["near_hull_25mev_t1"]
    rows["near_hull_50mev_t0"] = rows["e_above_hull_t0"].abs() <= 0.050
    rows["near_hull_50mev_t1"] = rows["e_above_hull_t1_current_mp"].abs() <= 0.050
    rows["near_hull_50mev_t0_or_t1"] = rows["near_hull_50mev_t0"] | rows["near_hull_50mev_t1"]
    rows["alignn_predicted_stable"] = rows["alignn_predicted_e_above_hull"] <= 0
    rows["alignn_disagrees_with_t1"] = rows["alignn_predicted_stable"] != rows["stable_exact_t1_current_mp"]
    rows["available_model_score_count"] = rows[
        ["alignn_predicted_e_above_hull", "cgcnn_ens10_pred_e_form", "megnet_pred_e_form"]
    ].notna().sum(axis=1)
    rows["mlip_consensus_status"] = "not_available_for_wbm_queue_chgnet_mace_missing"
    rows["mlip_disagreement_count"] = rows["alignn_disagrees_with_t1"].astype(int)
    rows["far_from_hull_50mev"] = ~rows["near_hull_50mev_t0_or_t1"]
    rows["far_from_hull_alignn_negative_parc_release"] = (
        rows["primary_queue_status"].eq("PARC_release")
        & rows["t1_false_conservative"]
        & rows["far_from_hull_50mev"]
        & (~rows["alignn_predicted_stable"])
    )
    rows["t1_false_explanation_class"] = rows.apply(classify_false_explanation, axis=1)
    rows["claim_boundary"] = "candidate_level_explanation_not_MLIP_consensus_validation"

    keep_cols = [
        "material_id",
        "formula",
        "chemical_system",
        "composition_family_pair",
        "K",
        "primary_queue_status",
        "parc_seed_count",
        "raw_topK_seed_count",
        "raw_topR_seed_count",
        "raw_only_tail_seed_count",
        "raw_topR_member",
        "e_above_hull_t0",
        "stable_exact_t0",
        "e_above_hull_t1_current_mp",
        "stable_exact_t1_current_mp",
        "t1_label_status",
        "drift_class",
        "t1_false_conservative",
        "near_hull_25mev_t0",
        "near_hull_25mev_t1",
        "near_hull_50mev_t0",
        "near_hull_50mev_t1",
        "alignn_score",
        "alignn_predicted_e_above_hull",
        "alignn_predicted_stable",
        "alignn_disagrees_with_t1",
        "cgcnn_ens10_pred_e_form",
        "megnet_pred_e_form",
        "available_model_score_count",
        "mlip_consensus_status",
        "mlip_disagreement_count",
        "parc_e_value",
        "required_e",
        "best_mass_ratio",
        "self_consistency_margin",
        "raw_rank",
        "source_uncertain_or_boundary_exact",
        "source_discordant_exact",
        "either_source_near_hull_25meV_exact",
        "included_in_alex_exact_metrics",
        "t1_false_explanation_class",
        "far_from_hull_alignn_negative_parc_release",
        "claim_boundary",
    ]
    rows[keep_cols].to_csv(OUT51 / "table_materials_t1_mlip_candidate_audit.csv", index=False)

    false_rows = rows[rows["t1_false_conservative"] & rows["primary_queue_status"].isin(["PARC_release", "raw_only_requested_budget"])]
    explanation = (
        false_rows.groupby(["K", "primary_queue_status", "t1_false_explanation_class"], as_index=False)
        .agg(n=("material_id", "nunique"))
    )
    denom = (
        false_rows.groupby(["K", "primary_queue_status"], as_index=False)
        .agg(false_denominator=("material_id", "nunique"))
    )
    explanation = explanation.merge(denom, on=["K", "primary_queue_status"], how="left")
    explanation["fraction_of_false"] = explanation["n"] / explanation["false_denominator"]
    explanation.to_csv(OUT51 / "table_materials_t1_false_explanation_summary.csv", index=False)
    explanation.to_csv(OUT51 / "figure_materials_t1_false_explanation_inputs.csv", index=False)

    dist = rows[rows["primary_queue_status"].isin(["PARC_release", "raw_only_requested_budget"])].copy()
    dist["t1_label"] = dist["stable_exact_t1_current_mp"].map({True: "t1_stable", False: "t1_false_or_unresolved"})
    dist_inputs = dist[
        [
            "K",
            "primary_queue_status",
            "material_id",
            "t1_label",
            "alignn_score",
            "alignn_predicted_e_above_hull",
            "cgcnn_ens10_pred_e_form",
            "megnet_pred_e_form",
            "near_hull_50mev_t0_or_t1",
            "t1_false_explanation_class",
        ]
    ]
    dist_inputs.to_csv(OUT51 / "figure_materials_mlip_t1_distribution_inputs.csv", index=False)

    chem = (
        rows[rows["primary_queue_status"].isin(["PARC_release", "raw_only_requested_budget"])]
        .groupby(["K", "primary_queue_status", "chemical_system"], as_index=False)
        .agg(
            n=("material_id", "nunique"),
            false_n=("t1_false_conservative", "sum"),
            stable_to_unstable_n=("drift_class", lambda s: int((s == "stable_to_unstable").sum())),
        )
    )
    total = chem.groupby(["K", "primary_queue_status"], as_index=False).agg(total_n=("n", "sum"))
    chem = chem.merge(total, on=["K", "primary_queue_status"], how="left")
    chem["fraction_of_arm"] = chem["n"] / chem["total_n"]
    chem["single_chemsys_dominance_flag"] = chem["fraction_of_arm"] > 0.25
    chem.to_csv(OUT51 / "table_materials_chemistry_coverage_diagnostic.csv", index=False)

    availability_rows = []
    for model, source_path in PRED_SOURCES.items():
        column = {
            "alignn_ff": "alignn_ff_pred_e_form",
            "cgcnn_ens10": "cgcnn_ens10_pred_e_form",
            "megnet": "megnet_pred_e_form",
        }[model]
        availability_rows.append(
            {
                "model": model,
                "candidate_level_scores_available": True,
                "n_scored_queue_candidates": int(preds[column].notna().sum()),
                "n_total_queue_candidates": int(len(preds)),
                "source": PUBLIC_SOURCE_IDS[model],
                "source_sha256": sha256_file(source_path),
                "claim_use": "model_zoo_score_distribution_not_ground_truth",
            }
        )
    for model in ["CHGNet", "MACE-MP"]:
        availability_rows.append(
            {
                "model": model,
                "candidate_level_scores_available": False,
                "n_scored_queue_candidates": 0,
                "n_total_queue_candidates": int(len(preds)),
                "source": "not_available_for_WBM_queue_in_public_safe_cache",
                "source_sha256": "",
                "claim_use": "must_not_claim_MLIP_consensus_for_WBM_queue",
            }
        )
    write_csv(
        OUT51 / "table_materials_mlip_availability_status.csv",
        availability_rows,
        [
            "model",
            "candidate_level_scores_available",
            "n_scored_queue_candidates",
            "n_total_queue_candidates",
            "source",
            "source_sha256",
            "claim_use",
        ],
    )

    gate_rows = []
    for k in [300, 500]:
        subset = rows[rows["K"].eq(k)]
        parc_false = subset[
            subset["primary_queue_status"].eq("PARC_release") & subset["t1_false_conservative"]
        ]
        raw_false = subset[
            subset["primary_queue_status"].eq("raw_only_requested_budget") & subset["t1_false_conservative"]
        ]
        far_bad = int(parc_false["far_from_hull_alignn_negative_parc_release"].sum())
        gate_rows.append(
            {
                "K": k,
                "gate": "far_from_hull_alignn_negative_PARC_false_low",
                "status": "PASS" if far_bad <= max(5, 0.10 * len(parc_false)) else "DIAGNOSTIC_WARN",
                "lead_metric": f"{far_bad}/{len(parc_false)} PARC false candidates",
                "claim": "few PARC t1-false cases are both far from hull and ALIGNN-negative",
            }
        )
        parc_boundary = int(parc_false["near_hull_50mev_t0_or_t1"].sum())
        raw_boundary = int(raw_false["near_hull_50mev_t0_or_t1"].sum())
        gate_rows.append(
            {
                "K": k,
                "gate": "boundary_explanation_reported",
                "status": "PASS",
                "lead_metric": f"PARC boundary false {parc_boundary}/{len(parc_false)}; raw-only boundary false {raw_boundary}/{len(raw_false)}",
                "claim": "boundary and model-disagreement classes are reported, not hidden",
            }
        )
    gate_rows.append(
        {
            "K": "all",
            "gate": "CHGNet_MACE_WBM_queue_availability",
            "status": "NO_GO_FOR_MLIP_CONSENSUS",
            "lead_metric": "candidate-level CHGNet/MACE WBM queue scores unavailable in public-safe cache",
            "claim": "Phase51 v1 is not a CHGNet/MACE consensus validation",
        }
    )
    write_csv(
        OUT51 / "table_phase51_go_no_go.csv",
        gate_rows,
        ["K", "gate", "status", "lead_metric", "claim"],
    )

    closeout = """# NCS Phase51 Materials t1 Candidate-Level Explanation

Status: `completed_candidate_level_t1_explanation_v1_no_MLIP_consensus_claim`

This milestone merges the current-MP t1 hull labels with the frozen K=300/500
materials queue rows, ALIGNN-FF release scores, local CGCNN/MEGNet model-zoo
predictions, release margins, raw ranks, source-boundary tags, and near-hull
flags. It explains current-label false candidates at candidate level.

Claim boundary:

- This is a candidate-level explanation/model-zoo diagnostic.
- It is not a CHGNet/MACE consensus validation for the WBM queue, because
  candidate-level CHGNet and MACE-MP WBM queue scores are unavailable in the
  public-safe cache.
- It is not a prospective materials-discovery claim and not a strict t1
  alpha=0.10 certificate.

Recommended use in the NCS paper:

Use the figure-source CSVs to explain whether current-label failures are
near-hull, source-boundary, unresolved-current-MP-reference, or model-disagreed
cases. Do not write that two independent MLIPs validate the WBM t1 release.
"""
    (OUT51 / "NCS_PHASE51_MATERIALS_T1_CANDIDATE_EXPLANATION.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase51_materials_t1_candidate_explanation",
        "source_phase49": rel(PHASE49),
        "source_queue_rows": rel(QUEUE),
        "evidence_status": "completed_candidate_level_t1_explanation_v1_no_MLIP_consensus_claim",
        "claim_boundary": [
            "not_CHGNet_MACE_consensus_validation",
            "not_strict_alpha010_t1_certificate",
            "not_prospective_materials_discovery",
        ],
    }
    (OUT51 / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(OUT51)


def main() -> None:
    build_phase50()
    build_phase51()
    write_root_manifest()
    print(f"wrote {rel(OUT50)} and {rel(OUT51)}")


if __name__ == "__main__":
    main()
