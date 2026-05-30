#!/usr/bin/env python3
"""Build Phase83 necessity-theory and prevented-harm paperization artifacts.

This milestone is a synthesis layer.  It does not add new empirical labels or
rerun PARC.  It makes two completed strands paper-facing:

1. why null-superset release/refusal is necessary under one-sided verification;
2. what scientific harm is prevented by release/refusal in completed artifacts.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase83_necessity_and_prevented_harm"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

CTC_UTILITY = ROOT / "outputs/milestones/ctc_decision_utility_main_evidence/table_ctc_release_utility_primary.csv"
MATERIALS_UTILITY = ROOT / "outputs/milestones/fixed_budget_scientific_utility_trial/table_false_followups_prevented.csv"
SPACENET_AUDIT = ROOT / "outputs/milestones/cross_domain_blind_audit_main_evidence/table_cross_domain_audit_primary.csv"

SCOPE = (
    "NCS_phase83_necessity_and_prevented_harm;"
    "synthesis_of_completed_artifacts;"
    "not_new_empirical_result;"
    "not_new_human_labels;"
    "not_DFT_evidence;"
    "not_prospective_materials_discovery"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def build_principles() -> pd.DataFrame:
    rows = [
        {
            "principle_id": "NEC-001",
            "principle": "least_favourable_null_superset",
            "core_statement": "With only one-sided support, unverified candidates must remain in the null superset; otherwise an admissible truth assignment can invalidate release control.",
            "paper_function": "explains why PARC is not a threshold/e-BH variant that treats unverified rows as negatives",
            "supporting_artifact": "outputs/milestones/ncs_phase76_parc_lifecycle_calculus/supplement_parc_lifecycle_calculus.tex",
            "scope": SCOPE,
        },
        {
            "principle_id": "NEC-002",
            "principle": "refusal_lower_bound",
            "core_statement": "If no compatible non-empty set satisfies the self-consistency inequality, refusal is the evidence-supported lifecycle state.",
            "paper_function": "turns materials and high-volume no-go rows into an evidence-supported lifecycle state rather than failed optimization",
            "supporting_artifact": "outputs/milestones/ncs_phase76_parc_lifecycle_calculus/supplement_parc_lifecycle_calculus.tex",
            "scope": SCOPE,
        },
        {
            "principle_id": "NEC-003",
            "principle": "active_audit_gain",
            "core_statement": "Targeted positives help when they remove high-scoring null-superset block maxima that limit release evidence.",
            "paper_function": "mechanistic explanation for the CTC PARC-A transition and the 182.5x block-max removal diagnostic",
            "supporting_artifact": "outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics/table_parc_a_mechanism_gate.csv",
            "scope": SCOPE,
        },
    ]
    return pd.DataFrame(rows)


def build_prevented_harm() -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    ctc = pd.read_csv(CTC_UTILITY)
    ctc_random_k300 = ctc[
        ctc["proposal_source"].eq("ctc_random_score_negative_control")
        & ctc["K"].eq(300)
        & ctc["alpha"].eq(0.1)
    ].iloc[0]
    rows.append(
        {
            "domain": "biomedical_cell_tracking",
            "dataset": "Cell Tracking Challenge",
            "release_card_state": "certified_refusal_control",
            "naive_release": "random-score top-300 lineage links",
            "harm_unit": "false lineage edges",
            "naive_harm_mean": float(ctc_random_k300["false_links_avoided_mean"]),
            "PARC_harm_mean": 0.0,
            "prevented_harm_mean": float(ctc_random_k300["false_links_avoided_mean"]),
            "K": 300,
            "alpha": 0.1,
            "source_artifact": rel(CTC_UTILITY),
            "claim_scope": "completed_official_GT_refusal_consequence;not_new_human_audit",
            "evidence_scope": SCOPE,
        }
    )

    ctc_noisy_k5000 = ctc[
        ctc["proposal_source"].eq("ctc_noisy_geometric_linker")
        & ctc["K"].eq(5000)
        & ctc["alpha"].eq(0.1)
    ].iloc[0]
    rows.append(
        {
            "domain": "biomedical_cell_tracking",
            "dataset": "Cell Tracking Challenge",
            "release_card_state": "certified_refusal_control",
            "naive_release": "noisy geometric top-5000 lineage links",
            "harm_unit": "false lineage edges",
            "naive_harm_mean": float(ctc_noisy_k5000["false_links_avoided_mean"]),
            "PARC_harm_mean": 0.0,
            "prevented_harm_mean": float(ctc_noisy_k5000["false_links_avoided_mean"]),
            "K": 5000,
            "alpha": 0.1,
            "source_artifact": rel(CTC_UTILITY),
            "claim_scope": "completed_official_GT_refusal_consequence;not_new_human_audit",
            "evidence_scope": SCOPE,
        }
    )

    materials = pd.read_csv(MATERIALS_UTILITY)
    for k in [500, 5000]:
        row = materials[
            materials["proposal_source"].eq("alignn_ff_modern_learned_materials_model")
            & materials["K"].eq(k)
            & materials["alpha"].eq(0.1)
        ].iloc[0]
        rows.append(
            {
                "domain": "materials_screening",
                "dataset": "Matbench Discovery WBM",
                "release_card_state": "certified_stopping_or_refusal",
                "naive_release": f"ALIGNN-FF raw top-{k} follow-up queue",
                "harm_unit": "unstable public-DFT follow-ups",
                "naive_harm_mean": float(row["raw_unstable_count_mean"]),
                "PARC_harm_mean": float(row["PARC_unstable_count_mean"]),
                "prevented_harm_mean": float(row["prevented_unstable_followups_mean"]),
                "K": int(k),
                "alpha": 0.1,
                "source_artifact": rel(MATERIALS_UTILITY),
                "claim_scope": "completed_public_DFT_label_followup;not_prospective_discovery;not_DFT_recomputation",
                "evidence_scope": SCOPE,
            }
        )

    spacenet = pd.read_csv(SPACENET_AUDIT)
    sn = spacenet[
        spacenet["domain"].eq("earth_observation")
        & spacenet["dataset"].eq("SpaceNet7")
        & spacenet["K"].eq(100)
    ].iloc[0]
    raw_false = float(sn["raw_topK_audited_n"]) * float(sn["raw_topK_conservative_FTR"])
    rows.append(
        {
            "domain": "earth_observation",
            "dataset": "SpaceNet7",
            "release_card_state": "certified_refusal_boundary",
            "naive_release": "raw top-K same-building temporal links in audited comparator",
            "harm_unit": "audited false persistence links",
            "naive_harm_mean": raw_false,
            "PARC_harm_mean": 0.0,
            "prevented_harm_mean": raw_false,
            "K": int(sn["K"]),
            "alpha": float(sn["alpha"]),
            "source_artifact": rel(SPACENET_AUDIT),
            "claim_scope": "completed_human_audited_refusal_boundary;not_new_labels",
            "evidence_scope": SCOPE,
        }
    )

    return pd.DataFrame(rows)


def write_supplement() -> None:
    tex = r"""\section{Necessity of release/refusal under one-sided verification}
\label{sec:necessity-prevented-harm}

The PARC lifecycle is motivated by the information structure of scientific
candidate queues.  The setting provides one-sided support:
\[
  A_p=1 \Rightarrow Y_p=1 ,
\]
but it does not provide the converse.  Therefore an unverified candidate cannot
be treated as negative without adding an assumption not present in the data.

\paragraph{Least-favourable null-superset principle.}
Under one-sided support, every false calibration candidate remains in the
calibration null superset.  Any method that removes unverified candidates from
the denominator must justify an additional assumption about their validity.  In
the absence of such an assumption, the conservative null-superset denominator
is the least-favourable release-card denominator.

\paragraph{Refusal lower bound.}
For requested budget \(K\), target \(\alpha\), and candidate e-values \(E_p\),
a compatible non-empty release \(R\) must satisfy
\[
  \min_{p\in R} E_p \ge {K \over \alpha |R|}.
\]
When no compatible non-empty set satisfies this inequality, refusal is the
evidence-supported output.  This is not a statement that no scientifically
valid candidates exist; it is a statement that the current release card lacks
enough one-sided evidence for the requested release.

\paragraph{Active-audit gain principle.}
Targeted verification can change the release-card state by removing verified
positives from limiting null-superset block maxima.  This explains why a small
number of high-value one-sided audits can unlock release while random audits of
the same size may leave the denominator unchanged.

\paragraph{Prevented-harm interpretation.}
False-release control is not only a statistical object.  It prevents concrete
scientific artifacts from being polluted: false lineage edges in cell tracking,
unstable crystal follow-ups in materials screening, and false persistence links
in temporal mapping.  Phase83 reports these quantities only by reformatting
completed artifacts; it does not add new empirical labels or new DFT evidence.
"""
    (OUT / "supplement_necessity_and_prevented_harm.tex").write_text(tex, encoding="utf-8")


def write_docs(principles: pd.DataFrame, harm: pd.DataFrame) -> None:
    readme = f"""# Phase83 Necessity and Prevented Harm

Status: `completed_paperization_synthesis_not_new_empirical_result`.

This milestone packages two paper-facing arguments:

1. one-sided verification makes null-superset release/refusal necessary unless
   stronger label assumptions are added;
2. release/refusal prevents concrete scientific harm in completed artifacts.

It does not add new human labels, new DFT calculations, prospective materials
evidence, or a new empirical result.

Rows:

- necessity principles: {len(principles)}
- prevented-harm rows: {len(harm)}

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    closeout = f"""# Phase83 Closeout

Phase83 turns existing evidence into a compact editor-facing argument.

Main message:

> PARC is not merely a selector.  Under one-sided verification, release cards
> need a null-superset denominator, a principled refusal state and targeted
> audit rules; otherwise false candidates can enter downstream scientific
> artifacts.

Claim boundary:

- allowed: synthesis of completed theory and prevented-harm artifacts;
- forbidden: new real-audit evidence, new DFT validation, prospective
  materials discovery, or a stronger alpha certificate than the source
  artifacts support.
"""
    (OUT / "NCS_PHASE83_NECESSITY_AND_PREVENTED_HARM.md").write_text(closeout, encoding="utf-8")


def write_tables() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    principles = build_principles()
    harm = build_prevented_harm()
    principles.to_csv(OUT / "table_necessity_principles.csv", index=False)
    harm.to_csv(OUT / "table_prevented_scientific_harm.csv", index=False)

    figure = harm[
        [
            "domain",
            "dataset",
            "release_card_state",
            "harm_unit",
            "naive_harm_mean",
            "PARC_harm_mean",
            "prevented_harm_mean",
            "K",
            "alpha",
            "evidence_scope",
        ]
    ].copy()
    figure["panel"] = ["A", "B", "C", "D", "E"][: len(figure)]
    figure.to_csv(OUT / "figure_prevented_harm_inputs.csv", index=False)

    claim_gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase83_necessity_and_prevented_harm",
                "status": "completed_paperization_synthesis_not_new_empirical_result",
                "positive_evidence": "synthesis_only",
                "necessity_principles": len(principles),
                "prevented_harm_rows": len(harm),
                "allowed_current_claim": "Completed theory and harm artifacts support a release-card lifecycle framing.",
                "forbidden_current_claim": "Do not claim Phase83 adds new labels, new DFT evidence, prospective materials discovery, or a new alpha certificate.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    claim_gate.to_csv(OUT / "table_phase83_claim_gate.csv", index=False)

    write_supplement()
    write_docs(principles, harm)


def upsert_artifact_index() -> None:
    row = {
        "milestone": "ncs_phase83_necessity_and_prevented_harm",
        "path": rel(OUT) + "/",
        "evidence_state": "completed_paperization_synthesis_not_new_empirical_result",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase83_necessity_and_prevented_harm",
    }
    index = pd.read_csv(ARTIFACT_INDEX)
    index = index[index["milestone"] != row["milestone"]]
    index = pd.concat([index, pd.DataFrame([row])[index.columns]], ignore_index=True)
    index.to_csv(ARTIFACT_INDEX, index=False)


def upsert_ledger() -> None:
    row = {
        "claim_id": "NCS-PHASE83-001",
        "claim_text": "Phase83 packages one-sided necessity principles and completed prevented-harm artifacts for the release-card lifecycle framing.",
        "evidence_type": "paperization_synthesis",
        "positive_evidence": "synthesis_only",
        "scope": "completed_theory_and_completed_artifact_synthesis;not_new_empirical_result",
        "artifact_path": rel(OUT / "table_phase83_claim_gate.csv"),
        "hash": sha256_file(OUT / "table_phase83_claim_gate.csv"),
        "validation_command": "make reproduce-ncs-phase83-necessity-and-prevented-harm",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_new_labels_DFT_prospective_materials_discovery_or_new_alpha_certificate",
    }
    ledger = pd.read_csv(LEDGER)
    ledger = ledger[ledger["claim_id"] != row["claim_id"]]
    ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
    ledger.to_csv(LEDGER, index=False)


def upsert_claim_table() -> None:
    section = """\n## Phase83 Necessity and Prevented Harm\n\nStatus: `completed_paperization_synthesis_not_new_empirical_result`.\n\nPhase83 packages the one-sided necessity argument and completed downstream\nharm artifacts into a paper-facing release-card framing.  It supports the claim\nthat PARC is not just a selector: the one-sided information structure requires\na null-superset denominator, a refusal state and active-audit logic.  It also\nsummarizes completed prevented-harm rows for CTC, materials and SpaceNet.  It\nis synthesis only and does not add new labels, DFT evidence, prospective\nmaterials discovery or a new alpha certificate.\n"""
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    marker = "## Phase83 Necessity and Prevented Harm"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    write_tables()
    write_manifest(OUT)
    upsert_artifact_index()
    upsert_ledger()
    upsert_claim_table()
    write_root_manifest()
    print(f"[phase83] wrote {OUT.relative_to(ROOT)}")
    print("[phase83] status=completed_paperization_synthesis_not_new_empirical_result")


if __name__ == "__main__":
    main()
