#!/usr/bin/env python3
"""Build phase30 non-A3 main-evidence hard-upgrade milestones.

Phase29 made A1/A2 a completed negative/discordant diagnostic rather than a
materials-positive rescue path. This script pivots the completed evidence map to
non-A3 decision-level evidence while preserving claim scope:

* CTC strict release + refusal controls become decision-utility evidence.
* iWildCam/SpaceNet human-audit rows become cross-domain release/refusal
  governance evidence.
* OQMD/alex-mp materials joins become source-discordance stress diagnostics.
* A3 remains a high-risk bonus track unless a nonempty frozen selection and DFT
  outcome manifest exist.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONES = ROOT / "outputs" / "milestones"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(path: Path) -> None:
    rows = []
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(file_path)}  {file_path.relative_to(path)}")
    (path / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def f(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def i(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value):
            return default
        return int(round(float(value)))
    except Exception:
        return default


def write_root_manifest() -> None:
    rows = []
    for rel in sorted(
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and path.name != "MANIFEST_SHA256.txt"
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
        and not any(part == "outputs" and idx + 1 < len(path.parts) and path.parts[idx + 1] == "test_tmp" for idx, part in enumerate(path.parts))
    ):
        rows.append(f"{sha256_file(rel)}  {rel.relative_to(ROOT)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def build_materials_source_discordance() -> pd.DataFrame:
    out = MILESTONES / "materials_source_discordance_stress_test"
    out.mkdir(parents=True, exist_ok=True)

    oqmd = pd.read_csv(MILESTONES / "materials_independent_dft_validation" / "table_independent_dft_primary_results.csv")
    alex = pd.read_csv(MILESTONES / "materials_alex_mp_a1_a2_validation" / "table_alex_mp_a2_primary_results.csv")

    rows = []
    for source_name, df in [("OQMD public API", oqmd), ("alex-mp v20 local public snapshot", alex)]:
        row = df.iloc[0]
        claim_status = "completed_negative_diagnostic"
        if bool(row.get("completed_positive_result", False)):
            claim_status = "completed_positive_candidate_requires_review"
        rows.append(
            {
                "source": source_name,
                "external_label_source": row["external_label_source"],
                "K": i(row["K"]),
                "alpha": f(row["alpha"]),
                "match_confidence": row["match_confidence"],
                "exact_matched_n": i(row["n_unique_exact_structure_matches"]),
                "unique_candidate_n": i(row["n_unique_raw_topK_candidates"]),
                "coverage_released": f(row["coverage_of_independent_source"]),
                "coverage_raw_topK": f(row["raw_topK_coverage_of_independent_source"]),
                "PARC_matched_FTR": f(row["independent_FTR"], math.nan),
                "raw_matched_FTR": f(row["raw_topK_independent_FTR"], math.nan),
                "PARC_minus_raw_FTR": f(row["independent_FTR"], math.nan) - f(row["raw_topK_independent_FTR"], math.nan),
                "WBM_external_discordance": f(row["discordance_rate"], math.nan),
                "formula_only_excluded": True,
                "claim_status": claim_status,
                "paper_role": "source_discordance_stress_test",
                "main_text_role": "extended_data_stress_test",
                "not_primary_positive_validation": True,
                "interpretation": "external source does not support a positive independent-validation claim",
            }
        )

    summary = pd.DataFrame(rows)
    summary.to_csv(out / "table_materials_external_source_stress_summary.csv", index=False)
    (out / "MATERIALS_SOURCE_DISCORDANCE_STRESS_TEST.md").write_text(
        "# Materials Source-Discordance Stress Test\n\n"
        "Phase29 completed a stronger alex-mp exact-structure external-snapshot join. "
        "Coverage improved relative to OQMD, but the alex-mp labels were highly discordant "
        "with WBM and did not support a positive independent-validation claim. This milestone "
        "therefore merges OQMD and alex-mp as completed negative/discordant diagnostics.\n\n"
        "Formula-only matches are excluded from FTR. These rows must not be promoted to "
        "primary materials evidence.\n",
        encoding="utf-8",
    )
    write_manifest(out)
    return summary


def build_ctc_decision_utility() -> tuple[pd.DataFrame, pd.DataFrame]:
    out = MILESTONES / "ctc_decision_utility_main_evidence"
    out.mkdir(parents=True, exist_ok=True)

    strict = pd.read_csv(MILESTONES / "ctc_strict_anchor" / "table_ctc_primary_reverse_split_summary.csv")
    controls = pd.read_csv(MILESTONES / "ctc_strict_anchor" / "table_ctc_destroyed_ranking_controls.csv")
    consequence = pd.read_csv(MILESTONES / "ctc_strict_anchor" / "table_ctc_high_volume_refusal_consequence.csv")

    primary_rows = []
    for _, row in strict[(strict["alpha"].astype(float) == 0.10) & (strict["M"].astype(int).isin([100, 300]))].iterrows():
        primary_rows.append(
            {
                "evidence_type": "strict_release",
                "alpha": f(row["alpha"]),
                "K": i(row["M"]),
                "proposal_source": row["proposal_source"],
                "non_empty_seeds": i(row["nonempty_seeds"]),
                "total_seeds": i(row["seeds"]),
                "released_n_mean": f(row["released_mean"]),
                "verified_true_n_mean": f(row["released_mean"]) * (1.0 - f(row["actual_FTR_mean"])),
                "false_release_n_mean": f(row["released_mean"]) * f(row["actual_FTR_mean"]),
                "heldout_FTR": f(row["actual_FTR_mean"]),
                "raw_topK_FTR": f(row["raw_topM_actual_FTR_mean"]),
                "false_links_avoided_mean": 0.0,
                "manual_review_saved_proxy": 0.0,
                "lineage_damage_raw": 0.0,
                "lineage_damage_parc": 0.0,
                "certified_refusal": False,
                "raw_topK_comparator_present": True,
                "result_status": "primary_main_evidence",
                "interpretation": "strict alpha=0.10 release with zero held-out FTR; raw learned prefix is also clean at this budget",
            }
        )

    # Add high-damage refusal controls as decision-utility rows.
    for source, budget in [
        ("ctc_noisy_geometric_linker", 5000),
        ("ctc_random_score_negative_control", 5000),
        ("ctc_random_score_negative_control", 300),
    ]:
        match = consequence[(consequence["proposal_source"].eq(source)) & (consequence["K"].astype(int) == budget)]
        if match.empty:
            continue
        row = match.iloc[0]
        primary_rows.append(
            {
                "evidence_type": "certified_refusal_control",
                "alpha": f(row["alpha"]),
                "K": i(row["K"]),
                "proposal_source": row["proposal_source"],
                "non_empty_seeds": i(row["non_empty_seeds"]),
                "total_seeds": i(row["seeds"]),
                "released_n_mean": f(row["PARC_released_mean"]),
                "verified_true_n_mean": 0.0,
                "false_release_n_mean": f(row["PARC_false_lineage_edges_mean"]),
                "heldout_FTR": f(row["PARC_false_edge_fraction_mean"]),
                "raw_topK_FTR": f(row["raw_false_edge_fraction_mean"]),
                "false_links_avoided_mean": f(row["prevented_false_lineage_edges_mean"]),
                "manual_review_saved_proxy": f(row["raw_selected_links_mean"]) - f(row["PARC_released_mean"]),
                "lineage_damage_raw": f(row["raw_aogm_edge_edit_burden_proxy_mean"]),
                "lineage_damage_parc": f(row["PARC_aogm_edge_edit_burden_proxy_mean"]),
                "certified_refusal": i(row["non_empty_seeds"]) == 0,
                "raw_topK_comparator_present": True,
                "result_status": "secondary_main_evidence",
                "interpretation": "PARC refusal prevents false lineage edges from entering the downstream graph",
            }
        )

    utility = pd.DataFrame(primary_rows)
    utility.to_csv(out / "table_ctc_release_utility_primary.csv", index=False)

    damage_cols = [
        "proposal_source",
        "alpha",
        "K",
        "non_empty_seeds",
        "PARC_released_mean",
        "raw_selected_links_mean",
        "raw_false_lineage_edges_mean",
        "PARC_false_lineage_edges_mean",
        "prevented_false_lineage_edges_mean",
        "raw_corrupted_lineage_components_mean",
        "PARC_corrupted_lineage_components_mean",
        "prevented_corrupted_lineage_components_mean",
        "raw_aogm_edge_edit_burden_proxy_mean",
        "PARC_aogm_edge_edit_burden_proxy_mean",
        "prevented_aogm_edge_edit_burden_proxy_mean",
        "best_mass_ratio_mean",
        "interpretation",
    ]
    damage = consequence[damage_cols].copy()
    damage.to_csv(out / "table_ctc_raw_vs_parc_downstream_damage.csv", index=False)

    seed_rows = pd.read_csv(MILESTONES / "ctc_strict_anchor" / "table_ctc_primary_reverse_split_seed_rows.csv")
    seed_rows.to_csv(out / "table_ctc_seed_level_decision_utility.csv", index=False)
    controls.to_csv(out / "table_ctc_refusal_value_controls.csv", index=False)

    (out / "CTC_DECISION_UTILITY_MAIN_EVIDENCE.md").write_text(
        "# CTC Decision-Utility Main Evidence\n\n"
        "This milestone reframes the completed strict CTC evidence as release-time decision utility. "
        "The learned-hybrid source releases under strict `alpha=0.10` with zero held-out FTR, while "
        "destroyed-ranking and noisy/high-volume controls are refused before false lineage edges enter "
        "the downstream graph. The learned raw prefix is clean at the strict budgets, so the positive "
        "claim is release certification rather than fixed-size reranking improvement.\n",
        encoding="utf-8",
    )
    write_manifest(out)
    return utility, damage


def build_cross_domain_blind_audit() -> pd.DataFrame:
    out = MILESTONES / "cross_domain_blind_audit_main_evidence"
    out.mkdir(parents=True, exist_ok=True)

    iw_release = pd.read_csv(MILESTONES / "iwildcam_audit_final" / "table_iwildcam_release_audit_final.csv").iloc[0]
    iw_raw = pd.read_csv(MILESTONES / "scientific_domain_iwildcam_human_audit" / "table_iwildcam_raw_topk_audit_summary.csv").iloc[0]
    iw_agree = pd.read_csv(MILESTONES / "iwildcam_audit_final" / "table_iwildcam_second_review_agreement_final.csv")
    iw_primary = pd.read_csv(MILESTONES / "scientific_domain_iwildcam_human_audit" / "table_iwildcam_human_audit_primary_results.csv")
    iw_row = iw_primary[(iw_primary["alpha"].astype(float) == 0.20) & (iw_primary["K"].astype(int) == 50)].iloc[0]

    sp_release = pd.read_csv(MILESTONES / "spacenet_real_audit_final" / "table_spacenet_k50_release_audit.csv").iloc[0]
    sp_raw = pd.read_csv(MILESTONES / "spacenet_real_audit_final" / "table_spacenet_raw_topK_audit.csv").iloc[0]
    sp_refusal = pd.read_csv(MILESTONES / "spacenet_real_audit_final" / "table_spacenet_k100_refusal_diagnostics.csv").iloc[0]

    primary_rows = [
        {
            "domain": "ecological_camera_traps",
            "dataset": "iWildCam",
            "candidate_unit": "animal-present detection box",
            "alpha": f(iw_release["endpoint_alpha"]),
            "K": i(iw_release["endpoint_K"]),
            "decision": "release",
            "audited_released_n": i(iw_release["n_audited_unique_released_candidates"]),
            "released_true_n": i(iw_release["n_animal"]),
            "released_false_n": i(iw_release["n_false"]),
            "released_uncertain_n": i(iw_release["n_uncertain"]),
            "audited_FTR": f(iw_release["human_FTR"]),
            "conservative_audited_FTR": f(iw_release["conservative_human_FTR"]),
            "raw_topK_audited_n": i(iw_raw["n_audited"]),
            "raw_topK_FTR": f(iw_raw["human_FTR"]),
            "raw_topK_conservative_FTR": f(iw_raw["conservative_human_FTR"]),
            "non_empty_seeds": i(iw_row["non_empty_seeds"]),
            "total_seeds": 20,
            "blind_audit_labels_present": True,
            "second_review_present": True,
            "main_text_role": "primary_main_evidence",
            "claim_strength": "operational_human_audited_release",
            "scope": "operational alpha=0.20 ecology release; strict alpha=0.10 refused",
        },
        {
            "domain": "earth_observation",
            "dataset": "SpaceNet7",
            "candidate_unit": "same-building temporal link",
            "alpha": f(sp_release["alpha"]),
            "K": i(sp_release["K"]),
            "decision": "diagnostic_release",
            "audited_released_n": i(sp_release["n_unique_released_candidates_reviewed"]),
            "released_true_n": i(sp_release["n_true_same_building"]),
            "released_false_n": i(sp_release["n_false_link"]),
            "released_uncertain_n": i(sp_release["n_uncertain"]),
            "audited_FTR": f(sp_release["audited_FTR_uncertain_as_false"]),
            "conservative_audited_FTR": f(sp_release["audited_FTR_uncertain_as_false"]),
            "raw_topK_audited_n": i(sp_raw["n_audited"]),
            "raw_topK_FTR": f(sp_raw["audited_FTR_uncertain_as_false"]),
            "raw_topK_conservative_FTR": f(sp_raw["audited_FTR_uncertain_as_false"]),
            "non_empty_seeds": i(sp_release["non_empty_seeds"]),
            "total_seeds": i(sp_release["total_seeds"]),
            "blind_audit_labels_present": True,
            "second_review_present": False,
            "main_text_role": "secondary_main_evidence",
            "claim_strength": "human_audited_diagnostic_release_plus_primary_refusal",
            "scope": "K=50 diagnostic release; K=100 primary request refused",
        },
        {
            "domain": "earth_observation",
            "dataset": "SpaceNet7",
            "candidate_unit": "same-building temporal link",
            "alpha": f(sp_refusal["alpha"]),
            "K": i(sp_refusal["K"]),
            "decision": "certified_refusal",
            "audited_released_n": 0,
            "released_true_n": 0,
            "released_false_n": 0,
            "released_uncertain_n": 0,
            "audited_FTR": 0.0,
            "conservative_audited_FTR": 0.0,
            "raw_topK_audited_n": i(sp_raw["n_audited"]),
            "raw_topK_FTR": f(sp_raw["audited_FTR_uncertain_as_false"]),
            "raw_topK_conservative_FTR": f(sp_raw["audited_FTR_uncertain_as_false"]),
            "non_empty_seeds": i(sp_refusal["non_empty_seeds"]),
            "total_seeds": i(sp_refusal["total_seeds"]),
            "blind_audit_labels_present": True,
            "second_review_present": False,
            "main_text_role": "secondary_main_evidence",
            "claim_strength": "human_audited_refusal_boundary",
            "scope": "primary K=100 real-audit request refused because evidence mass is below one",
        },
    ]
    primary = pd.DataFrame(primary_rows)
    primary.to_csv(out / "table_cross_domain_audit_primary.csv", index=False)

    raw_vs = primary[
        [
            "domain",
            "dataset",
            "candidate_unit",
            "alpha",
            "K",
            "decision",
            "audited_released_n",
            "audited_FTR",
            "conservative_audited_FTR",
            "raw_topK_audited_n",
            "raw_topK_FTR",
            "raw_topK_conservative_FTR",
            "main_text_role",
            "scope",
        ]
    ].copy()
    raw_vs.to_csv(out / "table_cross_domain_raw_vs_parc.csv", index=False)

    agreement_rows = []
    all_rows = iw_agree[iw_agree["scope"].eq("all_rows")].iloc[0]
    agreement_rows.append(
        {
            "domain": "ecological_camera_traps",
            "dataset": "iWildCam",
            "agreement_scope": all_rows["scope"],
            "n_rows": i(all_rows["n_rows"]),
            "n_disagreements": i(all_rows["n_disagreements"]),
            "label_agreement": f(all_rows["label_agreement"]),
            "cohen_kappa": f(all_rows["cohen_kappa"], math.nan),
            "cohen_kappa_bootstrap95_low": f(all_rows["cohen_kappa_bootstrap95_low"], math.nan),
            "cohen_kappa_bootstrap95_high": f(all_rows["cohen_kappa_bootstrap95_high"], math.nan),
            "reportable_status": all_rows["reportable_status"],
        }
    )
    agreement_rows.append(
        {
            "domain": "earth_observation",
            "dataset": "SpaceNet7",
            "agreement_scope": "release_audit_human_confirmed",
            "n_rows": i(sp_release["n_unique_released_candidates_reviewed"]),
            "n_disagreements": 0,
            "label_agreement": 1.0,
            "cohen_kappa": math.nan,
            "cohen_kappa_bootstrap95_low": math.nan,
            "cohen_kappa_bootstrap95_high": math.nan,
            "reportable_status": "human_confirmed_release_audit_no_second_reviewer_kappa",
        }
    )
    pd.DataFrame(agreement_rows).to_csv(out / "table_cross_domain_agreement.csv", index=False)

    (out / "CROSS_DOMAIN_BLIND_AUDIT_MAIN_EVIDENCE.md").write_text(
        "# Cross-Domain Blind Audit Main Evidence\n\n"
        "This milestone aggregates completed human-audit evidence without adding new labels. "
        "iWildCam is the primary operational human-audited release row. SpaceNet contributes a "
        "human-confirmed low-volume diagnostic release and a primary K=100 certified refusal. "
        "Rows without completed blind labels or release audits are not promoted.\n",
        encoding="utf-8",
    )
    write_manifest(out)
    return primary


def build_main_decision_matrix(
    materials: pd.DataFrame, ctc: pd.DataFrame, audit: pd.DataFrame
) -> pd.DataFrame:
    out = MILESTONES / "main_evidence_hard_upgrade_phase30"
    out.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    ctc_primary = ctc[ctc["evidence_type"].eq("strict_release") & ctc["K"].eq(300)].iloc[0]
    rows.append(
        {
            "evidence_block": "CTC decision utility strict release",
            "domain": "biomedical_cell_tracking",
            "candidate_source": "learned_hybrid_appearance_linker",
            "verification_source": "official CTC GT / masked positives",
            "alpha": ctc_primary["alpha"],
            "K": ctc_primary["K"],
            "completed_status": "completed",
            "positive_or_negative": "positive",
            "claim_strength": "strict_alpha010_release",
            "main_text_role": "primary_main_evidence",
            "failure_mode": "",
            "next_action": "use as non-A3 primary decision-level evidence",
        }
    )
    ctc_refusal = ctc[ctc["proposal_source"].eq("ctc_random_score_negative_control") & ctc["K"].eq(300)].iloc[0]
    rows.append(
        {
            "evidence_block": "CTC destroyed-ranking refusal control",
            "domain": "biomedical_cell_tracking",
            "candidate_source": "random_score_negative_control",
            "verification_source": "official CTC GT",
            "alpha": ctc_refusal["alpha"],
            "K": ctc_refusal["K"],
            "completed_status": "completed",
            "positive_or_negative": "negative_control_refusal",
            "claim_strength": "refusal_boundary",
            "main_text_role": "secondary_main_evidence",
            "failure_mode": "score_corruption_high_raw_FTR",
            "next_action": "report as release/refusal governance evidence",
        }
    )
    for _, row in audit.iterrows():
        rows.append(
            {
                "evidence_block": f"{row['dataset']} human-audit release/refusal",
                "domain": row["domain"],
                "candidate_source": row["candidate_unit"],
                "verification_source": "blind/human visual audit",
                "alpha": row["alpha"],
                "K": row["K"],
                "completed_status": "completed",
                "positive_or_negative": row["decision"],
                "claim_strength": row["claim_strength"],
                "main_text_role": row["main_text_role"],
                "failure_mode": "" if row["decision"] != "certified_refusal" else "evidence_mass_below_one",
                "next_action": "use as completed real partial-verification envelope",
            }
        )
    for _, row in materials.iterrows():
        rows.append(
            {
                "evidence_block": f"Materials external-source stress: {row['source']}",
                "domain": "materials_discovery",
                "candidate_source": "ALIGNN-FF WBM released/raw candidates",
                "verification_source": row["external_label_source"],
                "alpha": row["alpha"],
                "K": row["K"],
                "completed_status": "completed",
                "positive_or_negative": "negative_diagnostic",
                "claim_strength": row["claim_status"],
                "main_text_role": "extended_data_stress_test",
                "failure_mode": "source_discordance_or_low_coverage",
                "next_action": "do not promote to primary positive validation",
            }
        )
    rows.append(
        {
            "evidence_block": "A3 MatterGen prospective DFT pilot",
            "domain": "materials_discovery",
            "candidate_source": "MatterGen + CHGNet/MACE consensus",
            "verification_source": "future DFT if nonempty selection exists",
            "alpha": 0.10,
            "K": 100,
            "completed_status": "running_or_pending",
            "positive_or_negative": "not_yet_evidence",
            "claim_strength": "high_risk_bonus_track",
            "main_text_role": "supplementary_diagnostic",
            "failure_mode": "DFT_not_completed_or_selection_not_frozen",
            "next_action": "background only; not critical path",
        }
    )
    matrix = pd.DataFrame(rows)
    matrix.to_csv(out / "table_main_evidence_decision_matrix.csv", index=False)
    (out / "MAIN_EVIDENCE_HARD_UPGRADE_PHASE30.md").write_text(
        "# Phase30 Main Evidence Hard Upgrade\n\n"
        "Phase30 pivots the main-evidence upgrade away from A1/A2/A3 dependency. "
        "A1/A2 alex-mp and OQMD joins are completed negative/discordant diagnostics. "
        "The completed non-A3 main evidence is now CTC decision utility plus cross-domain "
        "human-audit release/refusal behavior, with materials external-source discordance "
        "reported as an Extended Data stress test.\n",
        encoding="utf-8",
    )
    write_manifest(out)
    return matrix


def update_artifact_index() -> None:
    path = ROOT / "outputs" / "artifact_index.csv"
    df = pd.read_csv(path)
    new_rows = [
        {
            "milestone": "main_evidence_hard_upgrade_phase30",
            "path": "outputs/milestones/main_evidence_hard_upgrade_phase30/",
            "evidence_state": "completed_decision_matrix_non_A3_pivot",
            "manifest": "outputs/milestones/main_evidence_hard_upgrade_phase30/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/main_evidence_hard_upgrade_phase30",
        },
        {
            "milestone": "materials_source_discordance_stress_test",
            "path": "outputs/milestones/materials_source_discordance_stress_test/",
            "evidence_state": "completed_negative_external_source_stress_test",
            "manifest": "outputs/milestones/materials_source_discordance_stress_test/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/materials_source_discordance_stress_test",
        },
        {
            "milestone": "ctc_decision_utility_main_evidence",
            "path": "outputs/milestones/ctc_decision_utility_main_evidence/",
            "evidence_state": "completed_primary_decision_utility_evidence",
            "manifest": "outputs/milestones/ctc_decision_utility_main_evidence/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ctc_decision_utility_main_evidence",
        },
        {
            "milestone": "cross_domain_blind_audit_main_evidence",
            "path": "outputs/milestones/cross_domain_blind_audit_main_evidence/",
            "evidence_state": "completed_real_audit_release_refusal_envelope",
            "manifest": "outputs/milestones/cross_domain_blind_audit_main_evidence/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/cross_domain_blind_audit_main_evidence",
        },
    ]
    df = df[~df["milestone"].isin([row["milestone"] for row in new_rows])]
    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    df.to_csv(path, index=False)


def main() -> None:
    materials = build_materials_source_discordance()
    ctc, _ = build_ctc_decision_utility()
    audit = build_cross_domain_blind_audit()
    build_main_decision_matrix(materials, ctc, audit)
    update_artifact_index()


if __name__ == "__main__":
    main()
