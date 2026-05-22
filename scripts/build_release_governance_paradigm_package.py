#!/usr/bin/env python3
"""Build the release-governance problem-paradigm package.

This package is a paper-facing synthesis layer. It does not create new
experiments; it binds completed CTC active-audit evidence, the T1 empirical
baseline frontier, and refusal attribution into one claim-evidence closure.
"""

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
    return path, sha256_file(Path(path))


def build_components() -> pd.DataFrame:
    strong_path, strong_sha = source(
        "outputs/milestones/audit_budget_frontier_strong_positive/table_strong_positive_gate_audit.csv"
    )
    t1_path, t1_sha = source("outputs/milestones/t1_clean_acceptance_package/table_t1_baseline_frontier_summary.csv")
    t1_lead_path, t1_lead_sha = source(
        "outputs/milestones/t1_clean_acceptance_package/table_t1_clean_acceptance_lead_numbers.csv"
    )
    t1_gate_path, t1_gate_sha = source(
        "outputs/milestones/t1_clean_acceptance_package/table_t1_materials_validation_go_no_go.csv"
    )
    refusal_path, refusal_sha = source(
        "outputs/milestones/nmi_reviewer_p0_hardening/table_refusal_feasibility_attribution.csv"
    )
    audit_path, audit_sha = source(
        "outputs/milestones/nmi_reviewer_p0_hardening/table_human_audit_uncertainty_intervals.csv"
    )
    hierarchy_path, hierarchy_sha = source(
        "outputs/milestones/nmi_maintext_evidence_package/table_headline_evidence_hierarchy.csv"
    )

    strong = pd.read_csv(strong_path)
    primary = strong[strong["target_row"].eq("ctc_learned_strict_alpha010_K100")].iloc[0]
    leads = pd.read_csv(t1_lead_path)
    k300 = leads[leads["lead_id"].eq("materials_ALIGNN_K300_fixed_budget")].iloc[0]
    k500 = leads[leads["lead_id"].eq("materials_ALIGNN_K500_fixed_budget")].iloc[0]
    family = leads[leads["lead_id"].eq("baseline_family_coverage")].iloc[0]
    gate = leads[leads["lead_id"].eq("materials_independent_validation_gate")].iloc[0]
    refusal = pd.read_csv(refusal_path)
    audit = pd.read_csv(audit_path)

    return pd.DataFrame(
        [
            {
                "component_id": "problem_definition",
                "manuscript_role": "opening_frame",
                "component_sentence": (
                    "The paper studies release-time governance for frozen scientific candidate universes under "
                    "scarce one-sided verification, where unverified candidates are not negative labels and release, "
                    "refusal, or route-to-audit are the scientific decisions."
                ),
                "lead_number": "One primary headline, one T1 baseline frontier, and scoped boundary diagnostics are linked in the evidence hierarchy.",
                "source_artifact": hierarchy_path,
                "source_sha256": hierarchy_sha,
                "claim_boundary": "problem-frame only; does not assert a new materials discovery result",
            },
            {
                "component_id": "ctc_active_audit_primary_anchor",
                "manuscript_role": "primary_headline",
                "component_sentence": (
                    "CTC active verification is the strict anchor: a 0.5% top-score audit produced 20/20 nonempty "
                    "safe CTC K=100 releases with zero observed false releases at alpha=0.10."
                ),
                "lead_number": (
                    f"{int(primary['top_safe_seeds'])}/{int(primary['seeds'])} safe seeds; "
                    f"{int(primary['top_total_released'])} releases; "
                    f"{primary['top_total_false_releases']:.0f} false releases; "
                    f"{primary['budget_ratio_vs_random_full']:.0f}x budget ratio versus full random audit."
                ),
                "source_artifact": strong_path,
                "source_sha256": strong_sha,
                "claim_boundary": "completed simulated-audit strong positive for CTC only",
            },
            {
                "component_id": "t1_empirical_baseline_frontier",
                "manuscript_role": "clean_acceptance_support",
                "component_sentence": (
                    "The T1 empirical baseline frontier makes the materials contribution honest and comparable: "
                    "raw prefixes, matched-size raw, thresholds, conformal, e-value, e-BH-style, PU, oracle, and "
                    "PARC rows are shown together while only PARC carries the full release-certificate object."
                ),
                "lead_number": family["lead_number"],
                "source_artifact": t1_path,
                "source_sha256": t1_sha,
                "claim_boundary": "target-object-aware baseline frontier; not equality of baseline guarantees",
            },
            {
                "component_id": "materials_fixed_budget_frontier",
                "manuscript_role": "retrospective_materials_support",
                "component_sentence": (
                    "Materials is framed as a retrospective public-label release-policy frontier: ALIGNN K=300/500 "
                    "shows fixed-budget utility and matched-volume diagnostics without claiming fixed-size ranking gain."
                ),
                "lead_number": f"{k300['lead_number']} {k500['lead_number']}",
                "source_artifact": t1_lead_path,
                "source_sha256": t1_lead_sha,
                "claim_boundary": "retrospective public-label utility; raw top-R separates smaller queue effect",
            },
            {
                "component_id": "materials_validation_boundary",
                "manuscript_role": "explicit_no_go_boundary",
                "component_sentence": (
                    "The materials validation boundary is part of the contribution: independent, external-source, "
                    "and DFT-follow-up routes are kept out of positive evidence until their gates are completed."
                ),
                "lead_number": gate["lead_number"],
                "source_artifact": t1_gate_path,
                "source_sha256": t1_gate_sha,
                "claim_boundary": "do not claim independent or forward-looking materials validation success",
            },
            {
                "component_id": "refusal_attribution_closure",
                "manuscript_role": "governance_closure_support",
                "component_sentence": (
                    "Refusal is reported as an attributable governance decision: refusal rows are tied to "
                    "evidence-mass or finite-resolution gates rather than treated as unexplained selector failures."
                ),
                "lead_number": f"{len(refusal)} refusal rows have failure-mode attribution.",
                "source_artifact": refusal_path,
                "source_sha256": refusal_sha,
                "claim_boundary": "refusal attribution diagnostic; not a new release-positive row",
            },
            {
                "component_id": "human_audit_uncertainty_boundary",
                "manuscript_role": "audited_boundary_support",
                "component_sentence": (
                    "Human-audit rows are presented with interval uncertainty so zero observed false releases are not "
                    "mistaken for universal zero risk."
                ),
                "lead_number": f"{len(audit)} audit interval rows with Clopper-Pearson, Wilson, and Jeffreys intervals.",
                "source_artifact": audit_path,
                "source_sha256": audit_sha,
                "claim_boundary": "audited boundary support; external labels remain pending where not returned",
            },
        ]
    )


def build_claim_map(components: pd.DataFrame) -> pd.DataFrame:
    source_by_component = {
        row["component_id"]: (row["source_artifact"], row["source_sha256"])
        for _, row in components.iterrows()
    }
    rows = []

    def add(section: str, claim_id: str, sentence: str, component: str, status: str, boundary: str) -> None:
        source_artifact, source_sha256 = source_by_component[component]
        rows.append(
            {
                "section": section,
                "claim_id": claim_id,
                "exact_sentence": sentence,
                "evidence_component": component,
                "support_status": status,
                "source_artifact": source_artifact,
                "source_sha256": source_sha256,
                "claim_boundary": boundary,
            }
        )

    add(
        "abstract",
        "release_governance_problem",
        (
            "We study release-time governance for frozen scientific candidate universes under scarce one-sided "
            "verification, where unverified candidates cannot be treated as negatives."
        ),
        "problem_definition",
        "supported_problem_frame",
        "not a generator claim and not a forward-looking materials-discovery claim",
    )
    add(
        "abstract",
        "ctc_active_audit_headline",
        (
            "In cell tracking, a 0.5% targeted audit converts refusal into strict alpha=0.10 certified release, "
            "whereas matched-budget random audit releases no seeds and full random audit is 200x larger."
        ),
        "ctc_active_audit_primary_anchor",
        "supported_primary_headline",
        "CTC K=100 only; simulated-audit scope",
    )
    add(
        "abstract",
        "materials_baseline_frontier",
        (
            "In materials, the paper reports a retrospective public-label release-policy frontier, including "
            "matched-volume raw prefixes and different-target baselines, without elevating external-source "
            "diagnostics into validation success."
        ),
        "t1_empirical_baseline_frontier",
        "supported_secondary_headline",
        "retrospective public-label utility only",
    )
    add(
        "introduction",
        "publication_is_statistical_object",
        (
            "The object of inference is not the upstream score itself, but the publication action: which finite "
            "candidate set may be released, refused, or routed to further audit under a stated false-release target."
        ),
        "problem_definition",
        "supported_problem_frame",
        "finite frozen candidate universes only",
    )
    add(
        "results",
        "refusal_closure",
        (
            "Refusal outcomes are interpretable scientific-governance outputs because we attribute them to "
            "evidence-mass or finite-resolution gates rather than treating empty release as an unexplained failure."
        ),
        "refusal_attribution_closure",
        "supported_diagnostic_closure",
        "diagnostic attribution, not a positive release",
    )
    add(
        "limitations",
        "materials_boundary",
        (
            "The materials rows should be read as retrospective public-label release-policy evidence; external-source "
            "and DFT-follow-up routes remain outside positive evidence until their gates are completed."
        ),
        "materials_validation_boundary",
        "supported_boundary",
        "explicit no-go boundary",
    )
    return pd.DataFrame(rows)


def build_figure_blueprint() -> pd.DataFrame:
    rows = [
        {
            "figure_id": "Fig1_release_governance_paradigm",
            "paper_role": "problem_paradigm",
            "source_artifact": "outputs/milestones/release_governance_problem_paradigm/table_release_governance_paradigm_components.csv",
            "panel_plan": "candidate universe -> scarce one-sided verification -> release/refuse/audit decision -> evidence hierarchy",
            "claim_boundary": "conceptual figure; no new quantitative evidence",
        },
        {
            "figure_id": "Fig2_active_audit_ctc_anchor",
            "paper_role": "primary_headline",
            "source_artifact": "outputs/milestones/audit_budget_frontier_strong_positive/figure_active_audit_strong_positive_source.csv",
            "panel_plan": "0.5% top-score audit vs matched-budget random and full random audit; seed-safe release counts",
            "claim_boundary": "CTC K=100 primary; CTC K=300 support; materials excluded",
        },
        {
            "figure_id": "Fig3_t1_empirical_baseline_frontier",
            "paper_role": "clean_acceptance_support",
            "source_artifact": "outputs/milestones/t1_clean_acceptance_package/figure_t1_empirical_baseline_frontier_source.csv",
            "panel_plan": "materials fixed-budget utility plus empirical baseline families and certificate properties",
            "claim_boundary": "target-object-aware; not a forward-looking materials result",
        },
        {
            "figure_id": "ExtendedData_refusal_and_audit_boundaries",
            "paper_role": "boundary_support",
            "source_artifact": "outputs/milestones/nmi_reviewer_p0_hardening/figure_reviewer_p0_support_source.csv",
            "panel_plan": "refusal attribution, audit confidence intervals, assumption diagnostics, materials no-go ledger",
            "claim_boundary": "diagnostic and uncertainty support only",
        },
    ]
    return pd.DataFrame(rows)


def write_markdown(out_dir: Path, components: pd.DataFrame, claims: pd.DataFrame) -> None:
    abstract = (
        "# Release-Governance Abstract Draft\n\n"
        "Scientific AI systems increasingly generate ranked candidate lists faster than verification can keep up. "
        "We study the release-time governance problem for frozen scientific candidate universes under scarce "
        "one-sided verification, where verified positives provide support but unverified candidates cannot be "
        "treated as negatives. PARC turns this setting into an auditable release, refusal, or route-to-audit "
        "decision under a stated false-release target. In cell tracking, a 0.5% targeted audit converts refusal "
        "into strict alpha=0.10 certified release, with 20/20 nonempty safe seeds and zero observed false releases, "
        "whereas matched-budget random audit releases no seeds and full random audit is 200x larger in the frozen "
        "grid. In materials, we report a retrospective public-label release-policy frontier: raw prefixes, "
        "matched-volume raw, thresholds, conformal, e-value, e-BH-style, PU, oracle, and PARC rows are compared "
        "while external-source and DFT-follow-up routes remain outside positive evidence. Together, these results "
        "position publication itself as the statistical object: a scientific candidate should be released only "
        "when the finite compatible set has enough one-sided evidence, and otherwise refusal is a documented "
        "governance output rather than a hidden failure.\n"
    )
    (out_dir / "release_governance_abstract_v2.md").write_text(abstract, encoding="utf-8")

    skeleton = (
        "# Release-Governance Maintext Skeleton\n\n"
        "## Mini-Outline\n\n"
        "1. Define the problem as release-time governance for frozen scientific candidate universes.\n"
        "2. Use CTC active verification as the only strict primary headline.\n"
        "3. Use T1 as the empirical baseline frontier and materials release-policy support.\n"
        "4. Use refusal attribution and audit intervals to close the governance loop.\n"
        "5. State the materials boundary explicitly instead of implying validation success.\n\n"
        "## Claim-Evidence Map\n\n"
    )
    for _, row in claims.iterrows():
        skeleton += (
            f"- Claim: {row['exact_sentence']}\n"
            f"  Evidence: `{row['source_artifact']}`\n"
            f"  Status: {row['support_status']}; boundary: {row['claim_boundary']}\n"
        )
    skeleton += (
        "\n## Self-Review\n\n"
        "- Contribution: the paper is a release-governance interface, not a generator.\n"
        "- Writing clarity: the first results section should name CTC active audit as the primary headline.\n"
        "- Experimental strength: T1 is a baseline-frontier strengthening package, not independent materials validation.\n"
        "- Evaluation completeness: refusal attribution and audit intervals must stay visible.\n"
        "- Method design: claims must stay within frozen finite candidate universes and one-sided verification.\n"
    )
    (out_dir / "release_governance_maintext_skeleton.md").write_text(skeleton, encoding="utf-8")

    lead_lines = "\n".join(
        f"- {row['component_id']}: {row['lead_number']} ({row['claim_boundary']})"
        for _, row in components.iterrows()
    )
    closeout = (
        "# Release-Governance Problem Paradigm\n\n"
        "Status: completed paper-facing synthesis package.\n\n"
        "This package implements the route-2 positioning: the paper should be read as release-time governance "
        "under scarce one-sided verification. It binds CTC active-audit evidence, the T1 empirical baseline "
        "frontier, refusal attribution, and audit uncertainty into one manuscript-facing closure. It does not "
        "add new experimental labels and does not promote materials diagnostic routes into positive evidence.\n\n"
        "## Components\n\n"
        f"{lead_lines}\n\n"
        "## Required Main-Text Discipline\n\n"
        "- CTC active audit is the only primary strict headline.\n"
        "- T1 is the empirical baseline frontier and clean-acceptance support.\n"
        "- Materials are retrospective public-label release-policy evidence, not a forward-looking validation claim.\n"
        "- Refusal attribution is part of the governance result, but remains diagnostic rather than a new positive release row.\n"
    )
    (out_dir / "RELEASE_GOVERNANCE_PARADIGM_CLOSEOUT.md").write_text(closeout, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="outputs/milestones/release_governance_problem_paradigm")
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    components = build_components()
    claims = build_claim_map(components)
    figures = build_figure_blueprint()

    components.to_csv(out_dir / "table_release_governance_paradigm_components.csv", index=False)
    claims.to_csv(out_dir / "table_release_governance_claim_evidence_map.csv", index=False)
    figures.to_csv(out_dir / "table_release_governance_figure_blueprint.csv", index=False)
    write_markdown(out_dir, components, claims)
    provenance = {
        "status": "completed",
        "evidence_status": "paper_facing_synthesis_only",
        "claim_boundary": "route-2 release-governance positioning; no new materials validation evidence",
        "outputs": [
            "table_release_governance_paradigm_components.csv",
            "table_release_governance_claim_evidence_map.csv",
            "table_release_governance_figure_blueprint.csv",
            "release_governance_abstract_v2.md",
            "release_governance_maintext_skeleton.md",
            "RELEASE_GOVERNANCE_PARADIGM_CLOSEOUT.md",
        ],
    }
    (out_dir / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(out_dir)
    print(json.dumps(provenance, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
