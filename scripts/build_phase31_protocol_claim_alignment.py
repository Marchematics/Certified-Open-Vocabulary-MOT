#!/usr/bin/env python3
"""Build phase31 protocol/claim alignment artifacts.

Phase31 is a guardrail layer: it maps candidate headline results to their
predeclared protocol family, completed artifact, source hash, and allowed
manuscript role. It also creates paper-facing utility/consequence source tables
without promoting diagnostic, pending, or protocol-only rows.
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


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def ensure_clean_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    for child in path.iterdir():
        if child.is_file():
            child.unlink()


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
        if ".pytest_cache" in path.parts or "tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        if "outputs/test_tmp" in path.as_posix():
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def f(value: Any, default: float = math.nan) -> float:
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


def completed_source(path: Path) -> tuple[str, str, bool]:
    return rel(path), sha256_file(path), path.exists()


def build_materials_fixed_budget_utility() -> pd.DataFrame:
    out = MILESTONES / "materials_fixed_budget_scientific_utility"
    ensure_clean_dir(out)

    primary_path = MILESTONES / "fixed_budget_downstream_utility" / "table_materials_budget_utility_primary.csv"
    prevented_path = (
        MILESTONES / "fixed_budget_scientific_utility_trial" / "table_false_followups_prevented.csv"
    )
    cost_path = MILESTONES / "fixed_budget_scientific_utility_trial" / "table_cost_per_true_candidate.csv"

    primary = read_csv(primary_path)
    prevented = read_csv(prevented_path)
    cost = read_csv(cost_path)

    source_path, source_sha, _ = completed_source(primary_path)
    lead_rows: list[dict[str, Any]] = []
    for _, row in primary.iterrows():
        source = str(row["proposal_source"])
        k = i(row["K"])
        alpha = f(row["alpha"])
        is_lead = source == "alignn_ff_modern_learned_materials_model" and alpha == 0.10 and k in {300, 500}
        is_cgcnn_calibration = source == "cgcnn_ensemble_learned_materials_model" and alpha == 0.10 and k == 100
        role = "primary_headline" if is_lead else "secondary_support"
        if is_cgcnn_calibration:
            role = "calibration_check"
        lead_rows.append(
            {
                "result_id": f"materials_{source}_alpha{alpha:g}_K{k}",
                "proposal_source": source,
                "model_family": row.get("model_family", ""),
                "alpha": alpha,
                "rho": f(row.get("rho", 0.10)),
                "K": k,
                "non_empty_seeds": i(row.get("non_empty_seeds")),
                "total_seeds": i(row.get("seeds")),
                "mean_release": f(row.get("mean_release")),
                "PARC_FTR_mean": f(row.get("PARC_FTR_mean")),
                "raw_topK_FTR_mean": f(row.get("raw_topK_FTR_mean")),
                "raw_topR_FTR_mean": f(row.get("raw_topR_FTR_mean")),
                "raw_only_tail_FTR_mean": f(row.get("raw_only_tail_FTR_mean")),
                "raw_unstable_count_mean": f(row.get("raw_unstable_count_mean")),
                "PARC_unstable_count_mean": f(row.get("PARC_unstable_count_mean")),
                "prevented_unstable_followups_mean": f(row.get("prevented_unstable_followups_mean")),
                "DFT_efficiency_mean": f(row.get("DFT_efficiency_mean")),
                "raw_DFT_efficiency_mean": f(row.get("raw_DFT_efficiency_mean")),
                "best_mass_ratio_mean": f(row.get("best_mass_ratio_mean")),
                "release_status": row.get("release_status", ""),
                "manuscript_role": role,
                "protocol_family": "materials_frozen_alpha_rho_K_public_label_followup",
                "protocol_family_member": True,
                "source_table": source_path,
                "source_sha256": source_sha,
                "claim_scope": (
                    "fixed-budget public-DFT utility; certified stopping/refusal, not prospective discovery"
                ),
            }
        )

    lead = pd.DataFrame(lead_rows)
    lead.to_csv(out / "table_materials_fixed_budget_lead_numbers.csv", index=False)

    cost = cost.copy()
    cost["source_table"] = rel(cost_path)
    cost["source_sha256"] = sha256_file(cost_path)
    cost.to_csv(out / "table_materials_cost_per_true_candidate.csv", index=False)

    prevented = prevented.copy()
    prevented["source_table"] = rel(prevented_path)
    prevented["source_sha256"] = sha256_file(prevented_path)
    prevented.to_csv(out / "table_materials_unstable_followups_avoided.csv", index=False)

    (out / "MATERIALS_FIXED_BUDGET_SCIENTIFIC_UTILITY.md").write_text(
        "# Materials Fixed-Budget Scientific Utility\n\n"
        "This milestone extracts lead fixed-budget utility numbers from completed public-DFT "
        "follow-up tables. ALIGNN-FF alpha=0.10 K=300/500 rows are documented members of the "
        "frozen alpha-rho-K protocol family and may support the fixed-budget utility headline. "
        "CGCNN K=100 is retained as a calibration/validity check unless separately declared as "
        "the paper-facing utility primary. The claim is certified stopping/refusal under public "
        "labels, not prospective materials discovery.\n",
        encoding="utf-8",
    )
    write_manifest(out)
    return lead


def build_ctc_artifact_consequence() -> pd.DataFrame:
    out = MILESTONES / "ctc_scientific_artifact_consequence"
    ensure_clean_dir(out)

    damage_path = MILESTONES / "ctc_decision_utility_main_evidence" / "table_ctc_raw_vs_parc_downstream_damage.csv"
    official_path = (
        MILESTONES / "official_downstream_consequence" / "table_ctc_official_lineage_metric_summary.csv"
    )
    damage = read_csv(damage_path)
    official = read_csv(official_path)

    source_table, source_sha, _ = completed_source(damage_path)
    false_edges = damage[
        [
            "proposal_source",
            "alpha",
            "K",
            "non_empty_seeds",
            "PARC_released_mean",
            "raw_selected_links_mean",
            "raw_false_lineage_edges_mean",
            "PARC_false_lineage_edges_mean",
            "prevented_false_lineage_edges_mean",
            "raw_aogm_edge_edit_burden_proxy_mean",
            "PARC_aogm_edge_edit_burden_proxy_mean",
            "prevented_aogm_edge_edit_burden_proxy_mean",
            "interpretation",
        ]
    ].copy()
    false_edges["source_table"] = source_table
    false_edges["source_sha256"] = source_sha
    false_edges.to_csv(out / "table_ctc_false_lineage_edges_avoided.csv", index=False)

    official_source, official_sha, _ = completed_source(official_path)
    graph_damage = official[
        [
            "proposal_source",
            "source_scope",
            "alpha",
            "K",
            "non_empty_seeds",
            "raw_successor_conflicts_mean",
            "raw_predecessor_conflicts_mean",
            "raw_corrupted_lineage_components_mean",
            "PARC_corrupted_lineage_components_mean",
            "prevented_corrupted_lineage_components_mean",
            "raw_tra_edge_quality_proxy_mean",
            "PARC_tra_edge_quality_proxy_mean",
            "claim_scope",
        ]
    ].copy()
    graph_damage["source_table"] = official_source
    graph_damage["source_sha256"] = official_sha
    graph_damage.to_csv(out / "table_ctc_lineage_graph_damage.csv", index=False)

    (out / "CTC_SCIENTIFIC_ARTIFACT_CONSEQUENCE.md").write_text(
        "# CTC Scientific Artifact Consequence\n\n"
        "This milestone maps CTC release/refusal decisions to downstream lineage-graph artifacts. "
        "The strict learned rows certify clean links at alpha=0.10; high-risk or corrupted-score "
        "requests quantify false lineage edges and graph-edit burden avoided by refusal. These are "
        "official-GT consequence proxies, not official Cell Tracking Challenge leaderboard scores.\n",
        encoding="utf-8",
    )
    write_manifest(out)
    return false_edges


def build_protocol_claim_alignment(materials_lead: pd.DataFrame) -> pd.DataFrame:
    out = MILESTONES / "protocol_claim_alignment"
    ensure_clean_dir(out)

    rows: list[dict[str, Any]] = []
    family_rows: list[dict[str, Any]] = []
    claim_rows: list[dict[str, Any]] = []

    def add_endpoint(
        *,
        result_id: str,
        candidate_result: str,
        protocol_family: str,
        alpha: float | str,
        K: int | str,
        manuscript_role: str,
        evidence_state: str,
        artifact: Path,
        exact_sentence: str = "",
        completed: bool = True,
        predeclared: bool = True,
        protocol_family_member: bool = True,
        claim_boundary: str = "",
    ) -> None:
        source_table, source_sha, exists = completed_source(artifact)
        role_allowed = manuscript_role in {
            "primary_headline",
            "secondary_support",
            "validity_check",
            "calibration_check",
            "stress_test",
            "diagnostic_only",
            "failed_gate",
            "pending",
        }
        rows.append(
            {
                "result_id": result_id,
                "candidate_result": candidate_result,
                "protocol_family": protocol_family,
                "alpha": alpha,
                "K": K,
                "predeclared": predeclared,
                "protocol_family_member": protocol_family_member,
                "completed_artifact": source_table,
                "artifact_exists": exists,
                "source_sha256": source_sha if exists else "",
                "evidence_completed": completed,
                "evidence_state": evidence_state,
                "allowed_manuscript_role": manuscript_role,
                "role_allowed": role_allowed,
                "exact_manuscript_sentence": exact_sentence,
                "claim_boundary": claim_boundary,
            }
        )
        family_rows.append(
            {
                "result_id": result_id,
                "protocol_family": protocol_family,
                "alpha": alpha,
                "K": K,
                "protocol_family_member": protocol_family_member,
                "predeclared": predeclared,
                "source_artifact": source_table,
                "source_sha256": source_sha if exists else "",
                "membership_note": claim_boundary,
            }
        )
        claim_rows.append(
            {
                "claim_id": result_id,
                "exact_manuscript_sentence": exact_sentence,
                "manuscript_role": manuscript_role,
                "evidence_state": evidence_state,
                "completed_artifact": source_table,
                "source_sha256": source_sha if exists else "",
                "evidence_completed": completed,
                "claim_boundary": claim_boundary,
            }
        )

    fixed_artifact = (
        MILESTONES / "materials_fixed_budget_scientific_utility" / "table_materials_fixed_budget_lead_numbers.csv"
    )
    for _, row in materials_lead.iterrows():
        source = str(row["proposal_source"])
        k = i(row["K"])
        alpha = f(row["alpha"])
        role = str(row["manuscript_role"])
        if source == "cgcnn_ensemble_learned_materials_model" and k == 100 and alpha == 0.10:
            role = "calibration_check"
        if source == "alignn_ff_modern_learned_materials_model" and k in {300, 500} and alpha == 0.10:
            role = "primary_headline"
        sentence = ""
        if role == "primary_headline":
            sentence = (
                f"In materials fixed-budget public-label replay, the ALIGNN-FF K={k} request "
                f"prevented {f(row['prevented_unstable_followups_mean']):.2f} unstable follow-ups "
                f"on average while keeping the PARC FTR at {f(row['PARC_FTR_mean']):.3f}."
            )
        add_endpoint(
            result_id=str(row["result_id"]),
            candidate_result=f"materials fixed-budget {source} K={k}",
            protocol_family="materials_frozen_alpha_rho_K_public_label_followup",
            alpha=alpha,
            K=k,
            manuscript_role=role,
            evidence_state="completed_public_label_utility_evidence",
            artifact=fixed_artifact,
            exact_sentence=sentence,
            completed=True,
            predeclared=True,
            protocol_family_member=True,
            claim_boundary="utility under public labels; not prospective discovery",
        )

    add_endpoint(
        result_id="materials_release_error_reduction_ALIGNN_K300_K500",
        candidate_result="materials release-error reduction rows",
        protocol_family="materials_frozen_alpha_rho_K_public_label_followup",
        alpha="0.10",
        K="300/500",
        manuscript_role="primary_headline",
        evidence_state="completed_public_label_utility_evidence",
        artifact=fixed_artifact,
        exact_sentence=(
            "At the ALIGNN-FF K=300 and K=500 budgets, PARC reduced released unstable "
            "materials relative to the raw top-K follow-up queue while returning a smaller certified queue."
        ),
        completed=True,
        predeclared=True,
        protocol_family_member=True,
        claim_boundary="release-error reduction is certified stopping/refusal, not fixed-size reranking",
    )

    stress_artifact = (
        MILESTONES
        / "materials_source_discordance_stress_test"
        / "table_materials_external_source_stress_summary.csv"
    )
    add_endpoint(
        result_id="materials_external_OQMD",
        candidate_result="OQMD external-source diagnostic",
        protocol_family="materials_external_source_stress",
        alpha="0.10",
        K="500",
        manuscript_role="diagnostic_only",
        evidence_state="completed_negative_diagnostic",
        artifact=stress_artifact,
        completed=True,
        predeclared=False,
        protocol_family_member=True,
        claim_boundary="must not support primary positive validation",
    )
    add_endpoint(
        result_id="materials_external_alex_mp",
        candidate_result="alex-mp external-source diagnostic",
        protocol_family="materials_external_source_stress",
        alpha="0.10",
        K="500",
        manuscript_role="stress_test",
        evidence_state="completed_negative_diagnostic",
        artifact=stress_artifact,
        completed=True,
        predeclared=False,
        protocol_family_member=True,
        claim_boundary="must not support primary positive validation",
    )

    ctc_artifact = MILESTONES / "ctc_scientific_artifact_consequence" / "table_ctc_false_lineage_edges_avoided.csv"
    add_endpoint(
        result_id="ctc_strict_anchor_alpha010_K300",
        candidate_result="CTC strict anchor",
        protocol_family="ctc_strict_sequence_disjoint_release",
        alpha=0.10,
        K=300,
        manuscript_role="primary_headline",
        evidence_state="completed_strict_release",
        artifact=ctc_artifact,
        exact_sentence=(
            "In CTC, PARC released sequence-disjoint learned cell-link candidates at alpha=0.10 "
            "with 20/20 non-empty seeds and zero held-out false-link fraction."
        ),
        completed=True,
        predeclared=True,
        protocol_family_member=True,
        claim_boundary="release certification, not an end-to-end tracker claim",
    )

    audit_artifact = (
        MILESTONES / "cross_domain_blind_audit_main_evidence" / "table_cross_domain_audit_primary.csv"
    )
    add_endpoint(
        result_id="iwildcam_human_audit_alpha020_K50",
        candidate_result="iWildCam animal-present human audit",
        protocol_family="real_human_partial_verification_release_refusal",
        alpha=0.20,
        K=50,
        manuscript_role="secondary_support",
        evidence_state="completed_human_audit_operational",
        artifact=audit_artifact,
        completed=True,
        predeclared=True,
        protocol_family_member=True,
        claim_boundary="operational alpha=0.20; strict alpha=0.10 refused",
    )
    add_endpoint(
        result_id="spacenet_real_audit_K50_K100",
        candidate_result="SpaceNet audit/refusal",
        protocol_family="real_human_partial_verification_release_refusal",
        alpha=0.20,
        K="50/100",
        manuscript_role="secondary_support",
        evidence_state="completed_human_audit_diagnostic_and_refusal",
        artifact=audit_artifact,
        completed=True,
        predeclared=True,
        protocol_family_member=True,
        claim_boundary="K=50 diagnostic release; K=100 primary request refused",
    )

    a3_artifact = MILESTONES / "mattergen_parc_prospective_dft_followup" / "table_v4_freeze_status.csv"
    add_endpoint(
        result_id="A3_MatterGen_5k_pending",
        candidate_result="A3 MatterGen 5k pending",
        protocol_family="prospective_in_silico_DFT_bonus_track",
        alpha=0.10,
        K=100,
        manuscript_role="pending",
        evidence_state="pending",
        artifact=a3_artifact,
        completed=False,
        predeclared=True,
        protocol_family_member=True,
        claim_boundary="no prospective materials discovery unless released_n>=25, frozen selection, DFT n>=25, and FTR<=alpha",
    )

    audit = pd.DataFrame(rows)
    audit.to_csv(out / "table_predeclared_endpoint_audit.csv", index=False)
    pd.DataFrame(family_rows).to_csv(out / "table_protocol_family_membership.csv", index=False)
    pd.DataFrame(claim_rows).to_csv(out / "table_claim_to_evidence_alignment.csv", index=False)

    (out / "PROTOCOL_CLAIM_ALIGNMENT.md").write_text(
        "# Protocol Claim Alignment\n\n"
        "Phase31 assigns every candidate headline result to one allowed manuscript role. "
        "Primary headlines must map to completed artifacts, source SHA256 hashes, and exact "
        "paper-facing sentences. OQMD/alex-mp external-source rows are diagnostic/stress rows "
        "only. A3 MatterGen rows remain pending unless the DFT gates are met. CGCNN K=100 is "
        "kept as a calibration/validity check rather than a utility headline.\n",
        encoding="utf-8",
    )
    write_manifest(out)
    return audit


def write_abstract_claim_scope() -> None:
    path = ROOT / "docs" / "abstract_claim_scope.md"
    path.write_text(
        "# Abstract Claim Scope\n\n"
        "This file defines allowed and disallowed abstract-level language for the public "
        "artifact package.\n\n"
        "## Allowed Broadness Language\n\n"
        "- PARC converts frozen ranked candidate lists into auditable release-or-refuse decisions.\n"
        "- Completed evidence supports strict CTC release certification, fixed-budget materials "
        "public-label utility, and real human-audited release/refusal behavior.\n"
        "- Materials fixed-budget rows may be described as public-label computational follow-up "
        "or retrospective public-DFT utility.\n"
        "- External-source materials joins may be described as source-discordance stress tests.\n\n"
        "## Disallowed Oversell Language\n\n"
        "- Do not claim prospective materials discovery from A1/A2 or A3 unless the A3 DFT gates "
        "are met.\n"
        "- Do not describe OQMD or alex-mp diagnostics as positive independent validation.\n"
        "- Do not describe CGCNN K=100 as the paper-facing utility primary unless a separate "
        "predeclaration artifact exists.\n"
        "- Do not imply experimental synthesis, universal materials discovery, or model training "
        "improvement.\n\n"
        "## A3 DFT Gate\n\n"
        "The paper does not claim prospective materials discovery unless all of the following are "
        "true: `released_n >= 25`, `selection_frozen == true`, `dft_completed_n >= 25`, and "
        "`primary_FTR <= alpha`. Until then, MatterGen/A3 rows are pending or diagnostic only.\n",
        encoding="utf-8",
    )


def update_artifact_index() -> None:
    path = ROOT / "outputs" / "artifact_index.csv"
    df = pd.read_csv(path)
    rows = [
        {
            "milestone": "protocol_claim_alignment",
            "path": "outputs/milestones/protocol_claim_alignment/",
            "evidence_state": "completed_claim_scope_guardrail",
            "manifest": "outputs/milestones/protocol_claim_alignment/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/protocol_claim_alignment",
        },
        {
            "milestone": "materials_fixed_budget_scientific_utility",
            "path": "outputs/milestones/materials_fixed_budget_scientific_utility/",
            "evidence_state": "completed_public_label_fixed_budget_utility",
            "manifest": "outputs/milestones/materials_fixed_budget_scientific_utility/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/materials_fixed_budget_scientific_utility",
        },
        {
            "milestone": "ctc_scientific_artifact_consequence",
            "path": "outputs/milestones/ctc_scientific_artifact_consequence/",
            "evidence_state": "completed_ctc_downstream_artifact_consequence",
            "manifest": "outputs/milestones/ctc_scientific_artifact_consequence/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ctc_scientific_artifact_consequence",
        },
    ]
    df = df[~df["milestone"].isin([row["milestone"] for row in rows])]
    df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    df.to_csv(path, index=False)


def main() -> None:
    materials = build_materials_fixed_budget_utility()
    build_ctc_artifact_consequence()
    build_protocol_claim_alignment(materials)
    write_abstract_claim_scope()
    update_artifact_index()
    write_root_manifest()


if __name__ == "__main__":
    main()
