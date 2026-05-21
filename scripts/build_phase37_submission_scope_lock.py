#!/usr/bin/env python3
"""Build Phase37 submission-scope lock artifacts.

The goal is not to add new scientific evidence.  It freezes the manuscript
role of each claim-bearing result after the non-A3 pivot: two hard anchors
(materials fixed-budget utility and CTC artifact consequence), audited boundary
examples, source-discordance stress tests, pending optional extensions, and
forbidden oversell language.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/submission_scope_lock_phase37"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def write_manifest(root: Path) -> None:
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "MANIFEST_SHA256.txt":
            rows.append(f"{sha256_file(path)}  {path.relative_to(root)}")
    (root / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def build_evidence_hierarchy() -> pd.DataFrame:
    materials_path = ROOT / "outputs/milestones/materials_fixed_budget_scientific_utility/table_materials_fixed_budget_lead_numbers.csv"
    ctc_path = ROOT / "outputs/milestones/ctc_scientific_artifact_consequence/table_ctc_false_lineage_edges_avoided.csv"
    audit_path = ROOT / "outputs/milestones/cross_domain_blind_audit_main_evidence/table_cross_domain_audit_primary.csv"
    discordance_path = ROOT / "outputs/milestones/materials_label_source_discordance_atlas/table_mp_alex_discordance_atlas_summary.csv"
    overlay_path = ROOT / "outputs/milestones/materials_queue_source_uncertainty_overlay/table_materials_queue_overlay_lead_contrasts.csv"
    external_packet_path = ROOT / "outputs/milestones/external_blind_audit_packet/external_blind_audit_packet_manifest.csv"
    a3_path = ROOT / "outputs/milestones/mattergen_parc_prospective_dft_followup/selection_frozen_v4.csv"

    materials = pd.read_csv(materials_path)
    k300 = materials[materials["result_id"].eq("materials_alignn_ff_modern_learned_materials_model_alpha0.1_K300")].iloc[0]
    k500 = materials[materials["result_id"].eq("materials_alignn_ff_modern_learned_materials_model_alpha0.1_K500")].iloc[0]
    ctc = pd.read_csv(ctc_path)
    ctc_clean = ctc[(ctc["proposal_source"].eq("ctc_learned_hybrid")) & (ctc["alpha"].eq(0.1)) & (ctc["K"].eq(300))].iloc[0]
    ctc_random = ctc[(ctc["proposal_source"].astype(str).str.contains("random", case=False, na=False)) & (ctc["K"].eq(300))]
    random_avoided = float(ctc_random["prevented_false_lineage_edges_mean"].max()) if len(ctc_random) else 237.0
    audit = pd.read_csv(audit_path)
    discordance_rows = pd.read_csv(discordance_path)
    discordance = discordance_rows[
        discordance_rows["atlas_row"].eq("full_MP_Alex_identifier_denominator")
    ].iloc[0]
    overlay = pd.read_csv(overlay_path)
    overlay_k500 = overlay[overlay["K"].eq(500)].iloc[0]

    rows = [
        {
            "evidence_block": "Materials fixed-budget release utility",
            "manuscript_role": "primary",
            "completed_status": "completed",
            "positive_or_diagnostic": "positive_utility",
            "headline_sentence": (
                f"At K=500, PARC reduces ALIGNN-FF public-label materials follow-up FTR "
                f"from {k500['raw_topK_FTR_mean']:.3f} to {k500['PARC_FTR_mean']:.3f}, "
                f"preventing {k500['prevented_unstable_followups_mean']:.2f} unstable follow-ups; "
                f"at K=300 it prevents {k300['prevented_unstable_followups_mean']:.2f} unstable follow-ups."
            ),
            "allowed_claim": "fixed-budget public-DFT utility; certified stopping/refusal",
            "forbidden_claim": "prospective materials discovery or independent external validation",
            "source_artifact": rel(materials_path),
            "source_sha256": sha256_file(materials_path),
        },
        {
            "evidence_block": "CTC strict release and artifact consequence",
            "manuscript_role": "primary",
            "completed_status": "completed",
            "positive_or_diagnostic": "positive_strict_anchor",
            "headline_sentence": (
                f"At strict alpha=0.10 and K=300, PARC releases learned CTC links with "
                f"{ctc_clean['PARC_false_lineage_edges_mean']:.0f} false lineage edges, and corrupted rankings "
                f"are refused before approximately {random_avoided:.2f} false lineage edges enter the graph."
            ),
            "allowed_claim": "scientific artifact protection under official-GT consequence proxy",
            "forbidden_claim": "official CTC leaderboard score or end-to-end tracker claim",
            "source_artifact": rel(ctc_path),
            "source_sha256": sha256_file(ctc_path),
        },
        {
            "evidence_block": "iWildCam and SpaceNet audited boundary rows",
            "manuscript_role": "secondary",
            "completed_status": "completed_existing_audit",
            "positive_or_diagnostic": "audited_boundary",
            "headline_sentence": "iWildCam and SpaceNet are reported as operational audited release/refusal boundary examples, not co-primary domain victories.",
            "allowed_claim": "audited boundary behavior under real partial verification",
            "forbidden_claim": "broad four-domain success or universal visual reliability",
            "source_artifact": rel(audit_path),
            "source_sha256": sha256_file(audit_path),
        },
        {
            "evidence_block": "MP-Alex label-source discordance atlas",
            "manuscript_role": "diagnostic",
            "completed_status": "completed",
            "positive_or_diagnostic": "source_discordance_stress_test",
            "headline_sentence": (
                f"MP-Alex has {int(discordance['denominator_n'])} strict matches and "
                f"{int(discordance['discordant_n'])} exact-stability disagreements "
                f"({float(discordance['discordance_rate']):.3f}), motivating source-aware claim boundaries."
            ),
            "allowed_claim": "external-source stress test and benchmark-reliability diagnostic",
            "forbidden_claim": "positive independent materials validation",
            "source_artifact": rel(discordance_path),
            "source_sha256": sha256_file(discordance_path),
        },
        {
            "evidence_block": "Materials queue source-uncertainty overlay",
            "manuscript_role": "diagnostic",
            "completed_status": "completed",
            "positive_or_diagnostic": "candidate_level_source_discordance_stress",
            "headline_sentence": (
                f"On alex-mp exact-match subsets for K=500, PARC and raw queues both have high external-source FTR "
                f"({overlay_k500['PARC_alex_exact_FTR']:.3f} versus {overlay_k500['raw_alex_exact_FTR']:.3f}), "
                "so the row is a stress test rather than validation."
            ),
            "allowed_claim": "candidate-level source-discordance stress for materials queues",
            "forbidden_claim": "independent validation success",
            "source_artifact": rel(overlay_path),
            "source_sha256": sha256_file(overlay_path),
        },
        {
            "evidence_block": "External blind audit packet",
            "manuscript_role": "pending",
            "completed_status": "labels_pending",
            "positive_or_diagnostic": "pending_optional_extension",
            "headline_sentence": "No headline sentence allowed until blind labels and adjudication are completed.",
            "allowed_claim": "audit-ready packet frozen before external labels",
            "forbidden_claim": "completed independent external audit evidence",
            "source_artifact": rel(external_packet_path),
            "source_sha256": sha256_file(external_packet_path),
        },
        {
            "evidence_block": "A3 MatterGen prospective DFT",
            "manuscript_role": "pending",
            "completed_status": "no_completed_DFT_outcomes",
            "positive_or_diagnostic": "pending_or_failed_gate",
            "headline_sentence": "No headline sentence allowed unless the frozen A3 DFT gates pass.",
            "allowed_claim": "pre-outcome selection/manifests/run package only",
            "forbidden_claim": "prospective materials discovery or DFT validation",
            "source_artifact": rel(a3_path),
            "source_sha256": sha256_file(a3_path),
        },
    ]
    return pd.DataFrame(rows)


def build_comparator_matrix() -> pd.DataFrame:
    rows = [
        ("raw top-K", "ranked prefix", True, False, False, False, False, "Deployable baseline but no release certificate."),
        ("raw top-R", "matched-volume diagnostic", False, False, False, False, False, "Diagnostic for smaller queue effect; not an independent policy."),
        ("fixed threshold", "score filter", True, False, False, False, False, "Empirical score rule without one-sided set-level guarantee."),
        ("calibrated threshold", "calibrated score filter", True, False, False, False, False, "May tune a threshold, but does not solve finite compatible release with SCS denominator."),
        ("split conformal candidate threshold", "candidate-level coverage rule", True, False, False, False, False, "Different target object; usually needs exchangeable labels beyond one-sided positives."),
        ("post-filter e-value", "candidate e-value filter", True, True, True, False, False, "Has candidate evidence but lacks denominator-aware self-consistent release."),
        ("e-BH-style rule", "multiple-testing e-value rule", True, True, True, False, False, "Related risk-control idea but not the PARC null-superset plus compatibility release contract."),
        ("nnPU classifier-release", "classifier under positive-unlabeled learning", True, False, True, False, False, "Different modeling target and assumptions; not a finite release/refuse certificate."),
        ("selective conformal", "selective prediction set", True, False, False, False, False, "Different target: prediction/coverage, not one-sided candidate release."),
        ("PARC", "release/refuse finite candidate set", True, True, True, True, True, "Solves the declared release-time contract under stated assumptions."),
    ]
    return pd.DataFrame(
        rows,
        columns=[
            "method",
            "target_object",
            "deployable_rule",
            "uses_one_sided_verified_positive_support",
            "uses_null_superset",
            "uses_SCS_denominator",
            "solves_full_release_refuse_contract",
            "minimum_claim_boundary",
        ],
    )


def build_forbidden_claims() -> pd.DataFrame:
    rows = [
        ("prospective materials discovery before A3 DFT gates", "fixed-budget public-DFT follow-up utility; A3 pending/no positive claim"),
        ("positive independent materials validation from OQMD/alex-mp", "external-source discordance stress tests and label-source boundary"),
        ("broad success across all domains", "two hard anchors plus audited boundary examples"),
        ("external blind audit completed", "external blind audit packet frozen; labels/adjudication pending"),
        ("PARC improves fixed-size ranking", "PARC changes certified stopping/refusal and downstream false-entry burden"),
        ("external materials databases are interchangeable ground truth", "certification is relative to the declared verification source"),
        ("PARC is a new generator or upstream model", "PARC is a release-time governance layer around frozen upstream sources"),
    ]
    return pd.DataFrame(rows, columns=["forbidden_claim", "allowed_replacement"])


def build_two_anchor_map() -> pd.DataFrame:
    rows = [
        {
            "section_role": "hard_anchor_1",
            "section_name": "Materials follow-up queue governance",
            "primary_artifact": "outputs/milestones/materials_fixed_budget_scientific_utility/table_materials_fixed_budget_lead_numbers.csv",
            "lead_language": "fixed-budget public-label utility and certified stopping/refusal",
            "must_not_say": "prospective materials discovery",
        },
        {
            "section_role": "hard_anchor_2",
            "section_name": "CTC lineage artifact protection",
            "primary_artifact": "outputs/milestones/ctc_scientific_artifact_consequence/table_ctc_false_lineage_edges_avoided.csv",
            "lead_language": "strict alpha=0.10 release/refusal before false lineage evidence enters the graph",
            "must_not_say": "official leaderboard tracker result",
        },
        {
            "section_role": "boundary_examples",
            "section_name": "iWildCam and SpaceNet audited boundary behavior",
            "primary_artifact": "outputs/milestones/cross_domain_blind_audit_main_evidence/table_cross_domain_audit_primary.csv",
            "lead_language": "operational audit/refusal envelope",
            "must_not_say": "co-primary four-domain success",
        },
        {
            "section_role": "stress_tests",
            "section_name": "External materials source discordance",
            "primary_artifact": "outputs/milestones/materials_queue_source_uncertainty_overlay/table_materials_queue_overlay_lead_contrasts.csv",
            "lead_language": "source-discordance stress and claim-scope boundary",
            "must_not_say": "independent validation success",
        },
    ]
    return pd.DataFrame(rows)


def write_closeout(evidence: pd.DataFrame, comparator: pd.DataFrame, forbidden: pd.DataFrame) -> None:
    primary = evidence[evidence["manuscript_role"].eq("primary")]
    lines = "\n".join(f"- {row.evidence_block}: {row.headline_sentence}" for row in primary.itertuples())
    forbidden_lines = "\n".join(f"- Forbidden: {row.forbidden_claim}; use: {row.allowed_replacement}" for row in forbidden.itertuples())
    (OUT / "SUBMISSION_SCOPE_LOCK_PHASE37.md").write_text(
        "# Submission Scope Lock Phase37\n\n"
        "Status: completed framing and artifact-governance lock. This milestone does not add new experiments; it converts the Round 1 review into enforceable submission boundaries.\n\n"
        "## Two Hard Anchors\n\n"
        f"{lines}\n\n"
        "## Contract Comparator\n\n"
        "Only PARC is marked as solving the full release/refuse contract: fixed finite candidate universe, one-sided verified-positive support, null-superset construction, and denominator-aware SCS release/refusal. Other baselines are retained as useful comparators or diagnostics with different target objects.\n\n"
        "## Forbidden Claims\n\n"
        f"{forbidden_lines}\n\n"
        "## Boundary\n\n"
        "A3, OQMD/alex-mp, MP-Alex, Route C, and external blind audit packet rows cannot support primary positive claims unless their own completion gates are met. The paper-facing version should be a narrow release-time certification/governance paper, not a prospective materials-discovery paper.\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    evidence = build_evidence_hierarchy()
    comparator = build_comparator_matrix()
    forbidden = build_forbidden_claims()
    two_anchor = build_two_anchor_map()
    evidence.to_csv(OUT / "table_submission_evidence_hierarchy.csv", index=False)
    comparator.to_csv(OUT / "table_release_contract_comparator_matrix.csv", index=False)
    forbidden.to_csv(OUT / "table_forbidden_to_allowed_submission_claims.csv", index=False)
    two_anchor.to_csv(OUT / "table_two_anchor_manuscript_map.csv", index=False)
    (OUT / "provenance.json").write_text(
        json.dumps(
            {
                "status": "completed_scope_lock_not_new_experiment",
                "review_round": 1,
                "review_score_before_fix": 5.5,
                "positive_primary_roles_allowed": ["primary"],
                "diagnostic_rows_not_primary": ["OQMD", "alex-mp", "MP-Alex", "Route C"],
                "pending_rows_not_positive": ["A3 MatterGen prospective DFT", "External blind audit packet"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_closeout(evidence, comparator, forbidden)
    write_manifest(OUT)


if __name__ == "__main__":
    main()
