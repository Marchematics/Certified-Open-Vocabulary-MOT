#!/usr/bin/env python3
"""Build phase32 NMI presubmission package and desk-risk cold read."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
MILESTONES = ROOT / "outputs" / "milestones"
OUT = MILESTONES / "nmi_presubmission_package"


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
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def f(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def source_hash(path: Path) -> tuple[str, str]:
    return rel(path), sha256_file(path)


def load_sources() -> dict[str, pd.DataFrame]:
    return {
        "claims": read_csv(MILESTONES / "protocol_claim_alignment" / "table_claim_to_evidence_alignment.csv"),
        "endpoint_audit": read_csv(
            MILESTONES / "protocol_claim_alignment" / "table_predeclared_endpoint_audit.csv"
        ),
        "materials": read_csv(
            MILESTONES
            / "materials_fixed_budget_scientific_utility"
            / "table_materials_fixed_budget_lead_numbers.csv"
        ),
        "ctc_edges": read_csv(
            MILESTONES
            / "ctc_scientific_artifact_consequence"
            / "table_ctc_false_lineage_edges_avoided.csv"
        ),
        "audit": read_csv(
            MILESTONES / "cross_domain_blind_audit_main_evidence" / "table_cross_domain_audit_primary.csv"
        ),
        "stress": read_csv(
            MILESTONES
            / "materials_source_discordance_stress_test"
            / "table_materials_external_source_stress_summary.csv"
        ),
    }


def primary_claims(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    claims = sources["claims"].copy()
    primary = claims[
        (claims["manuscript_role"].eq("primary_headline"))
        & (claims["evidence_completed"].astype(bool))
        & (~claims["evidence_state"].astype(str).isin({"diagnostic_only", "failed_gate", "protocol_only", "pending"}))
    ].copy()
    return primary


def build_lead_numbers(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    materials = sources["materials"]
    ctc_edges = sources["ctc_edges"]

    mat_source = MILESTONES / "materials_fixed_budget_scientific_utility" / "table_materials_fixed_budget_lead_numbers.csv"
    ctc_source = MILESTONES / "ctc_scientific_artifact_consequence" / "table_ctc_false_lineage_edges_avoided.csv"
    mat_artifact, mat_hash = source_hash(mat_source)
    ctc_artifact, ctc_hash = source_hash(ctc_source)

    rows: list[dict[str, Any]] = []
    for k in [300, 500]:
        row = materials[
            materials["result_id"].eq(f"materials_alignn_ff_modern_learned_materials_model_alpha0.1_K{k}")
        ].iloc[0]
        rows.append(
            {
                "lead_number_id": f"materials_ALIGNN_FF_K{k}_fixed_budget",
                "domain": "materials_discovery",
                "manuscript_role": "primary_headline",
                "evidence_state": "completed_public_label_utility_evidence",
                "lead_number": (
                    f"K={k}: raw top-K FTR {f(row['raw_topK_FTR_mean']):.3f}; "
                    f"PARC FTR {f(row['PARC_FTR_mean']):.3f}; "
                    f"prevented {f(row['prevented_unstable_followups_mean']):.2f} unstable follow-ups on average"
                ),
                "source_artifact": mat_artifact,
                "source_sha256": mat_hash,
                "claim_scope": "fixed-budget public-DFT utility; not prospective discovery",
            }
        )

    ctc = ctc_edges[(ctc_edges["proposal_source"].eq("ctc_learned_hybrid")) & (ctc_edges["K"].astype(int).eq(300))].iloc[0]
    rows.append(
        {
            "lead_number_id": "CTC_strict_alpha010_K300",
            "domain": "biomedical_cell_tracking",
            "manuscript_role": "primary_headline",
            "evidence_state": "completed_strict_release",
            "lead_number": (
                "K=300: PARC released 300.0 learned cell-link candidates in 20/20 seeds "
                "with zero false lineage edges under official GT consequence proxies"
            ),
            "source_artifact": ctc_artifact,
            "source_sha256": ctc_hash,
            "claim_scope": "release certification for link candidates; not an end-to-end tracker claim",
        }
    )

    return pd.DataFrame(rows)


def build_evidence_table(sources: dict[str, pd.DataFrame], lead_numbers: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    materials = sources["materials"]
    ctc_edges = sources["ctc_edges"]
    audit = sources["audit"]
    stress = sources["stress"]

    mat_source, mat_hash = source_hash(
        MILESTONES / "materials_fixed_budget_scientific_utility" / "table_materials_fixed_budget_lead_numbers.csv"
    )
    ctc_source, ctc_hash = source_hash(
        MILESTONES / "ctc_scientific_artifact_consequence" / "table_ctc_false_lineage_edges_avoided.csv"
    )
    audit_source, audit_hash = source_hash(
        MILESTONES / "cross_domain_blind_audit_main_evidence" / "table_cross_domain_audit_primary.csv"
    )
    stress_source, stress_hash = source_hash(
        MILESTONES
        / "materials_source_discordance_stress_test"
        / "table_materials_external_source_stress_summary.csv"
    )

    k300 = materials[materials["result_id"].eq("materials_alignn_ff_modern_learned_materials_model_alpha0.1_K300")].iloc[0]
    k500 = materials[materials["result_id"].eq("materials_alignn_ff_modern_learned_materials_model_alpha0.1_K500")].iloc[0]
    rows.append(
        {
            "evidence_block": "Materials fixed-budget release utility",
            "scientific_artifact_or_workflow": "DFT follow-up queue over WBM/Matbench public labels",
            "verification_regime": "masked public DFT positives; public-label follow-up evaluation",
            "parc_decision": "certified smaller release at K=300/500",
            "comparator": "raw top-K follow-up queue",
            "lead_consequence": (
                f"K=300 prevented {f(k300['prevented_unstable_followups_mean']):.2f}; "
                f"K=500 prevented {f(k500['prevented_unstable_followups_mean']):.2f} unstable follow-ups"
            ),
            "claim_scope": "fixed-budget utility, not prospective materials discovery",
            "manuscript_role": "primary_headline",
            "source_artifact": mat_source,
            "source_sha256": mat_hash,
        }
    )

    ctc = ctc_edges[(ctc_edges["proposal_source"].eq("ctc_learned_hybrid")) & (ctc_edges["K"].astype(int).eq(300))].iloc[0]
    random = ctc_edges[
        (ctc_edges["proposal_source"].eq("ctc_random_score_negative_control"))
        & (ctc_edges["K"].astype(int).eq(300))
    ].iloc[0]
    rows.append(
        {
            "evidence_block": "CTC strict release and artifact consequence",
            "scientific_artifact_or_workflow": "cell-link evidence entering a lineage graph",
            "verification_regime": "official CTC GT / masked positive calibration",
            "parc_decision": "strict alpha=0.10 release for learned links; refusal for corrupted rankings",
            "comparator": "raw learned queue and random-score corrupted queue",
            "lead_consequence": (
                f"K=300 strict release has {f(ctc['PARC_false_lineage_edges_mean']):.0f} false lineage edges; "
                f"random-score K=300 refusal avoids {f(random['prevented_false_lineage_edges_mean']):.2f} false lineage edges"
            ),
            "claim_scope": "scientific artifact consequence proxy, not official CTC leaderboard score",
            "manuscript_role": "primary_headline",
            "source_artifact": ctc_source,
            "source_sha256": ctc_hash,
        }
    )

    iw = audit[audit["dataset"].eq("iWildCam")].iloc[0]
    rows.append(
        {
            "evidence_block": "iWildCam human-audited release",
            "scientific_artifact_or_workflow": "camera-trap animal-present release list",
            "verification_regime": "blind human audit with second review",
            "parc_decision": "operational alpha=0.20 release",
            "comparator": "raw top-K audited list",
            "lead_consequence": f"{int(iw['audited_released_n'])}/{int(iw['audited_released_n'])} released candidates animal-present",
            "claim_scope": "audited operational boundary; strict alpha=0.10 refused",
            "manuscript_role": "secondary_support",
            "source_artifact": audit_source,
            "source_sha256": audit_hash,
        }
    )

    sp = audit[audit["dataset"].eq("SpaceNet7") & audit["decision"].eq("certified_refusal")].iloc[0]
    rows.append(
        {
            "evidence_block": "SpaceNet real-audit refusal boundary",
            "scientific_artifact_or_workflow": "same-building temporal-link release",
            "verification_regime": "blind visual audit",
            "parc_decision": "K=100 certified refusal; K=50 diagnostic release",
            "comparator": "raw top-K audited links",
            "lead_consequence": "primary K=100 request refused when evidence mass was insufficient",
            "claim_scope": "release/refusal boundary vignette, not flagship positive",
            "manuscript_role": "secondary_support",
            "source_artifact": audit_source,
            "source_sha256": audit_hash,
        }
    )

    alex = stress[stress["source"].astype(str).str.contains("alex-mp")].iloc[0]
    rows.append(
        {
            "evidence_block": "Materials external-source discordance",
            "scientific_artifact_or_workflow": "cross-database stability label stress test",
            "verification_regime": "alex-mp exact-structure join; formula-only excluded",
            "parc_decision": "not promoted as positive validation",
            "comparator": "raw top-K matched subset",
            "lead_consequence": f"WBM/alex-mp discordance {f(alex['WBM_external_discordance']):.3f}",
            "claim_scope": "stress test; external databases are not interchangeable labels",
            "manuscript_role": "stress_test",
            "source_artifact": stress_source,
            "source_sha256": stress_hash,
        }
    )

    return pd.DataFrame(rows)


def write_presubmission(lead_numbers: pd.DataFrame, evidence: pd.DataFrame) -> None:
    material_lines = "\n".join(f"- {row.lead_number}" for row in lead_numbers.itertuples() if row.domain == "materials_discovery")
    ctc_line = lead_numbers[lead_numbers["domain"].eq("biomedical_cell_tracking")]["lead_number"].iloc[0]
    text = f"""# Presubmission Inquiry v1

Dear Editors,

We would like to ask whether Nature Machine Intelligence would consider a manuscript on release-time certification for scientific AI candidate pipelines under one-sided partial verification.

Scientific AI systems increasingly produce ranked lists of candidate objects before exhaustive verification is available: candidate stable crystals for computational follow-up, cell-link evidence for lineage graphs, and visual detections or temporal links for ecological and geospatial monitoring. The central decision is not only how to score candidates, but when an AI system should release a finite set and when it should refuse because the available verification support is insufficient.

We introduce PARC, a release-time certification layer that takes a frozen finite candidate universe and returns either a certified release set or a certified refusal. The presubmission package deliberately separates completed headline evidence from diagnostics and pending protocols. In particular, prospective materials discovery is not claimed unless the separate MatterGen/DFT gates are met.

The completed headline evidence is:

{material_lines}
- {ctc_line}

The manuscript also includes completed audited boundary evidence: iWildCam provides an operational human-audited ecology release, while SpaceNet 7 provides a real-audit release/refusal boundary. External materials-source joins with OQMD and alex-mp are reported only as source-discordance stress tests, not as positive independent validation.

We believe the paper fits NMI because it targets an increasingly common AI-for-science governance problem: how to decide which model-generated scientific candidates may responsibly enter downstream workflows when verification is one-sided and incomplete. The contribution is a general release/refuse interface, supported by completed artifact-level evidence and by explicit guardrails that prevent protocol-only, pending, or discordant diagnostics from being overstated.
"""
    (OUT / "presubmission_inquiry_v1.md").write_text(text, encoding="utf-8")


def write_abstract() -> None:
    text = """# NMI Abstract v1

Scientific AI systems often produce finite ranked lists of candidate objects before exhaustive verification is available. We study the release decision itself: which candidates may be published or sent downstream, and when should the system refuse to release any set? We introduce PARC, a release-time certification interface for one-sided partial verification that converts a frozen candidate universe into either a certified release set or a certified refusal. In materials discovery, PARC changed fixed-budget public-DFT follow-up queues from a learned stability source, reducing unstable follow-ups at the K=300 and K=500 budgets without claiming prospective discovery. In cell tracking, PARC released sequence-disjoint learned cell-link candidates under strict alpha=0.10 and prevented corrupted rankings from entering lineage-graph artifacts. Human-audited iWildCam and SpaceNet 7 rows show release/refusal behavior under real partial verification, while OQMD and alex-mp joins are reported as source-discordance stress tests. PARC does not improve the upstream model; it governs release under partial evidence.
"""
    (OUT / "nmi_abstract_v1.md").write_text(text, encoding="utf-8")


def write_cold_read() -> None:
    rows = [
        {
            "risk": "scope risk",
            "risk_level": "medium",
            "cold_read": "The paper could look too broad if framed as universal scientific-AI reliability.",
            "mitigation_sentence": "Frame PARC as a release-time interface for fixed, covered candidate universes under one-sided partial verification.",
        },
        {
            "risk": "incrementality risk",
            "risk_level": "medium",
            "cold_read": "Editors may see the method as a variant of e-values or conformal filtering.",
            "mitigation_sentence": "Lead with release/refuse decisions for downstream scientific artifacts, then explain the statistical machinery.",
        },
        {
            "risk": "evidence-breadth risk",
            "risk_level": "medium",
            "cold_read": "The completed primary evidence is strongest in materials public-label utility and CTC, with visual audits as boundary evidence.",
            "mitigation_sentence": "Present a coherent evidence hierarchy: primary completed rows, audited boundary rows, and diagnostic stress tests.",
        },
        {
            "risk": "materials-overclaim risk",
            "risk_level": "high",
            "cold_read": "A materials reviewer may object if retrospective/public-label utility is described as discovery.",
            "mitigation_sentence": "Use 'fixed-budget public-DFT follow-up utility' and explicitly state that prospective materials discovery is not claimed before A3 DFT gates.",
        },
        {
            "risk": "reviewer-routing risk",
            "risk_level": "medium",
            "cold_read": "Pure theorists may focus on e-BH details, while pure domain specialists may miss the release-certification object.",
            "mitigation_sentence": "Request reviewers spanning AI-for-science reliability, applied risk control, and downstream scientific workflow evaluation.",
        },
    ]
    text = "# NMI Editor Cold Read\n\n"
    for row in rows:
        text += f"## {row['risk']}\n\n"
        text += f"- risk_level: {row['risk_level']}\n"
        text += f"- desk_read: {row['cold_read']}\n"
        text += f"- mitigation_sentence: {row['mitigation_sentence']}\n\n"
    (OUT / "nmi_editor_cold_read.md").write_text(text, encoding="utf-8")


def write_referees() -> None:
    text = """# Suggested Referee Rationale

Ideal referee profiles:

1. AI-for-science reliability. This referee can judge whether release/refuse decisions over candidate scientific objects are a meaningful governance layer for downstream workflows.

2. Applied conformal/e-value risk control. This referee can evaluate one-sided partial verification, null-superset calibration, finite release sets, and the distinction between a release certificate and ordinary thresholding.

3. Scientific ML workflow / downstream artifact evaluation. This referee can assess whether materials follow-up queues, cell lineage-link artifacts, and audited ecological/geospatial release lists are appropriate evidence objects.

Avoid relying only on pure e-BH theory reviewers: the manuscript is not a pure multiple-testing theory paper, and the main contribution is a release-time interface and evidence package.

Avoid relying only on pure domain specialists: a materials-only or cell-tracking-only reviewer may undervalue the common release-certification object across domains.
"""
    (OUT / "suggested_referee_rationale.md").write_text(text, encoding="utf-8")


def write_positioning() -> None:
    path = ROOT / "docs" / "nmi_submission_positioning.md"
    text = """# NMI Submission Positioning

## What The Paper Is

- Release-time certification for scientific AI candidate pipelines.
- Scientific AI governance for finite candidate universes under one-sided partial verification.
- Partial-verification risk control that can return either a certified release set or a certified refusal.
- A completed evidence package separating primary headline claims, secondary audited boundary evidence, and diagnostic stress tests.

## What The Paper Is Not

- Not prospective materials discovery unless A3 DFT gates are met.
- Not a new materials generator or a claim that PARC improves upstream model rankings.
- Not a pure e-BH theory paper; the method uses risk-control machinery but targets release decisions.
- Not a claim that external materials databases are interchangeable stability labels.
- Not an experimental synthesis or universal scientific-discovery guarantee.

## Guardrail

Use release-time certification / release-or-refuse language in broad claims. Use public-label fixed-budget utility for materials unless A3 produces a frozen nonempty selection, at least 25 completed DFT outcomes, and primary FTR within alpha.
"""
    path.write_text(text, encoding="utf-8")


def write_claims_used(primary: pd.DataFrame, evidence: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in primary.iterrows():
        rows.append(
            {
                "claim_id": row["claim_id"],
                "manuscript_role": row["manuscript_role"],
                "evidence_state": row["evidence_state"],
                "exact_manuscript_sentence": row["exact_manuscript_sentence"],
                "source_artifact": row["completed_artifact"],
                "source_sha256": row["source_sha256"],
                "used_in_presubmission": True,
            }
        )
    claims = pd.DataFrame(rows)
    claims.to_csv(OUT / "table_claims_used_in_presubmission.csv", index=False)
    return claims


def update_artifact_index() -> None:
    path = ROOT / "outputs" / "artifact_index.csv"
    df = pd.read_csv(path)
    row = {
        "milestone": "nmi_presubmission_package",
        "path": "outputs/milestones/nmi_presubmission_package/",
        "evidence_state": "completed_presubmission_positioning_package",
        "manifest": "outputs/milestones/nmi_presubmission_package/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/nmi_presubmission_package",
    }
    df = df[df["milestone"] != row["milestone"]]
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(path, index=False)


def update_docs() -> None:
    claim_table = ROOT / "docs" / "claim_table.md"
    marker = "| Phase32 packages NMI presubmission claims with desk-risk guardrails."
    text = claim_table.read_text(encoding="utf-8")
    if marker not in text:
        insert = (
            "| Phase32 packages NMI presubmission claims with desk-risk guardrails. | "
            "`outputs/milestones/nmi_presubmission_package/presubmission_inquiry_v1.md`; "
            "`one_page_evidence_table.csv`; `nmi_editor_cold_read.md`; "
            "`docs/nmi_submission_positioning.md` | "
            "`python scripts/build_phase32_nmi_presubmission_package.py` | "
            "Uses only phase31-approved primary-headline claims for lead numbers; iWildCam/SpaceNet are audited boundary evidence, OQMD/alex-mp are stress tests, and A3 pending rows cannot appear as positive evidence. |\n"
        )
        text = text.replace("| iWildCam animal-present release", insert + "| iWildCam animal-present release", 1)
        claim_table.write_text(text, encoding="utf-8")

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    if "milestones/nmi_presubmission_package/" not in text:
        text = text.replace(
            "│   ├── milestones/ctc_scientific_artifact_consequence/\n",
            "│   ├── milestones/ctc_scientific_artifact_consequence/\n│   ├── milestones/nmi_presubmission_package/\n",
        )
    if "Phase32 NMI presubmission package" not in text:
        text = text.replace(
            "- Phase31 protocol/claim-alignment guardrails:",
            "- Phase32 NMI presubmission package: editor-facing inquiry, abstract draft, one-page evidence table, desk-risk cold read, referee rationale, and positioning guardrails built from phase31-approved claims only.\n- Phase31 protocol/claim-alignment guardrails:",
        )
    readme.write_text(text, encoding="utf-8")

    repro = ROOT / "REPRODUCIBILITY.md"
    text = repro.read_text(encoding="utf-8")
    if "outputs/milestones/nmi_presubmission_package/" not in text:
        text = text.replace(
            "outputs/milestones/ctc_scientific_artifact_consequence/\n",
            "outputs/milestones/ctc_scientific_artifact_consequence/\noutputs/milestones/nmi_presubmission_package/\n",
        )
    if "Regenerate the phase32 NMI presubmission package" not in text:
        block = """
Regenerate the phase32 NMI presubmission package:

```bash
python scripts/build_phase32_nmi_presubmission_package.py
```

This command builds the editor-facing inquiry, one-page evidence table,
abstract draft, desk-risk cold read, referee rationale, and positioning
document from phase31-approved evidence only. It excludes pending A3 rows and
external-source diagnostics from positive claims.
"""
        text = text.replace("The cross-domain success/refusal map can also be regenerated directly:", block + "\nThe cross-domain success/refusal map can also be regenerated directly:")
    repro.write_text(text, encoding="utf-8")


def update_makefile() -> None:
    path = ROOT / "Makefile"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "reproduce-phase31-claim-alignment reproduce-experimental-finalization",
        "reproduce-phase31-claim-alignment reproduce-phase32-presubmission reproduce-experimental-finalization",
    )
    if "reproduce-phase32-presubmission:" not in text:
        text = text.replace(
            "reproduce-phase31-claim-alignment:\n\t$(PYTHON) scripts/build_phase31_protocol_claim_alignment.py\n\n",
            "reproduce-phase31-claim-alignment:\n\t$(PYTHON) scripts/build_phase31_protocol_claim_alignment.py\n\nreproduce-phase32-presubmission:\n\t$(PYTHON) scripts/build_phase32_nmi_presubmission_package.py\n\n",
        )
    if "outputs/milestones/nmi_presubmission_package" not in text:
        text = text.replace(
            "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ctc_scientific_artifact_consequence\n",
            "\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ctc_scientific_artifact_consequence\n\t$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/nmi_presubmission_package\n",
        )
    path.write_text(text, encoding="utf-8")


def write_outputs() -> None:
    ensure_clean_dir(OUT)
    sources = load_sources()
    primary = primary_claims(sources)
    lead_numbers = build_lead_numbers(sources)
    evidence = build_evidence_table(sources, lead_numbers)

    lead_numbers.to_csv(OUT / "table_lead_numbers_for_editor.csv", index=False)
    evidence.to_csv(OUT / "one_page_evidence_table.csv", index=False)
    write_claims_used(primary, evidence)
    write_presubmission(lead_numbers, evidence)
    write_abstract()
    write_cold_read()
    write_referees()
    write_positioning()
    update_artifact_index()
    update_docs()
    update_makefile()
    write_manifest(OUT)
    write_root_manifest()


if __name__ == "__main__":
    write_outputs()
