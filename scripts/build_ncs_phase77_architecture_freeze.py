#!/usr/bin/env python3
"""Build Phase77 NCS architecture-freeze artifacts.

Phase77 freezes the paper spine, claim hierarchy, display plan and overclaim
guardrails after the Phase76 lifecycle-calculus synthesis. It intentionally
does not add new experiments.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase77_ncs_architecture_freeze"
PHASE63 = ROOT / "outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification"
PHASE65B = ROOT / "outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics"
PHASE69 = ROOT / "outputs/milestones/ncs_phase69_durability_budgeted_parc"
PHASE74 = ROOT / "outputs/milestones/ncs_phase74_risk_gated_recertification"
PHASE75 = ROOT / "outputs/milestones/ncs_phase75_active_versioned_recertification"
PHASE76 = ROOT / "outputs/milestones/ncs_phase76_parc_lifecycle_calculus"
PHASE70 = ROOT / "outputs/milestones/ncs_phase70_dft_v2_checkpoint"

SCOPE = (
    "NCS_architecture_freeze;"
    "paper_spine_claim_hierarchy_display_plan_guardrails;"
    "no_new_empirical_evidence;"
    "materials_as_lifecycle_stress_test;"
    "PARC_A_as_primary_empirical_positive;"
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
        if ".pytest_cache" in path.parts or "tmp" in path.parts or "test_tmp" in path.parts:
            continue
        if path.name == "MANIFEST_SHA256.txt":
            continue
        rows.append(f"{sha256_file(path)}  {rel(path)}")
    (ROOT / "MANIFEST_SHA256.txt").write_text("\n".join(rows) + "\n", encoding="utf-8")


def load_numbers() -> dict[str, object]:
    phase63 = pd.read_csv(PHASE63 / "table_parc_a_primary_gate.csv")
    ctc100 = phase63[phase63["target_row"].eq("ctc_learned_strict_alpha010_K100")].iloc[0]
    phase65b = pd.read_csv(PHASE65B / "table_parc_a_mechanism_gate.csv").set_index("gate")
    triage = pd.read_csv(PHASE69 / "table_risk_triage_frontier.csv")
    triage_row = triage[
        triage["risk_model"].eq("system_margin_distribution")
        & triage["K"].eq(300)
        & triage["retain_fraction"].eq(0.7)
    ].iloc[0]
    phase74 = pd.read_csv(PHASE74 / "table_risk_gated_primary_row.csv").iloc[0]
    phase75 = pd.read_csv(PHASE75 / "table_active_recertification_policy_comparison.csv")
    best75 = phase75.sort_values(
        ["nonempty_seeds", "safe_seeds", "mean_release_size", "mean_FTR_t1_if_nonempty"],
        ascending=[False, False, False, True],
    ).iloc[0]
    dft = pd.read_csv(PHASE70 / "table_dft_v2_execution_checkpoint_summary.csv").iloc[0]
    return {
        "ctc_budget_fraction": float(ctc100["audit_budget_fraction"]),
        "ctc_safe_seeds": int(ctc100["safe_seeds"]),
        "ctc_nonempty_seeds": int(ctc100["nonempty_seeds"]),
        "ctc_total_released": int(ctc100["total_released"]),
        "ctc_mean_ftr": float(ctc100["mean_FTR"]),
        "ctc_random_full_multiplier": float(ctc100["budget_ratio_vs_full_random"]),
        "ctc_fine_budget_safe_seeds": int(phase65b.loc["score_0p2pct_safe_release_20of20", "value"]),
        "ctc_blockmax_multiplier": float(phase65b.loc["score_removes_more_blockmax_than_random_at_0p2pct", "value"]),
        "triage_retained_flip_rate": float(triage_row["retained_flip_rate"]),
        "triage_base_flip_rate": float(triage_row["base_flip_rate"]),
        "triage_retained_n": int(triage_row["n_retained_low_risk"]),
        "triage_flagged_fraction": float(triage_row["flagged_fraction"]),
        "triage_flips_flagged": float(triage_row["fraction_flips_flagged"]),
        "phase74_nonempty": int(phase74["nonempty_seeds"]),
        "phase74_k": int(phase74["K_original"]),
        "phase75_best_nonempty": int(best75["nonempty_seeds"]),
        "phase75_best_safe": int(best75["safe_seeds"]),
        "phase75_best_ftr": float(best75["mean_FTR_t1_if_nonempty"]),
        "phase75_best_k": int(best75["K"]),
        "dft_completed": int(dft["completed_jobs"]),
        "dft_failed": int(dft["failed_jobs"]),
        "dft_failure_rate": float(dft["early_failure_rate_over_finished_jobs"]),
    }


def build_claim_hierarchy(numbers: dict[str, object]) -> pd.DataFrame:
    rows = [
        {
            "claim_id": "NCS-THESIS",
            "claim_text": "Scientific AI candidate queues should be governed by release cards rather than static top-K lists.",
            "manuscript_role": "central_thesis",
            "evidence_state": "conceptual_synthesis_supported",
            "primary_artifact": rel(PHASE76 / "table_lifecycle_baseline_capabilities.csv"),
            "display_item": "Figure 1; Figure 6",
            "allowed_language": "release-card lifecycle framework for scientific AI candidate queues",
            "forbidden_language": "new generator, universal scientific discovery system, or broad success across all domains",
            "overclaim_guardrail": "do_not_claim_new_empirical_evidence_from_Phase76",
        },
        {
            "claim_id": "PARC-CORE",
            "claim_text": "PARC gives a one-sided release/refusal certificate for a frozen candidate universe and fixed reference version.",
            "manuscript_role": "main_method",
            "evidence_state": "theory_and_completed_artifacts",
            "primary_artifact": rel(PHASE76 / "supplement_parc_lifecycle_calculus.tex"),
            "display_item": "Figure 2",
            "allowed_language": "one-sided null-superset release/refusal certificate",
            "forbidden_language": "guarantee under unversioned truth or future reference updates",
            "overclaim_guardrail": "version_scope_required",
        },
        {
            "claim_id": "PARC-A-CTC",
            "claim_text": (
                f"PARC-A is the primary empirical positive: CTC K=100 reaches "
                f"{numbers['ctc_safe_seeds']}/20 safe releases and {numbers['ctc_total_released']} released links "
                f"with observed FTR {numbers['ctc_mean_ftr']} under targeted one-sided audit."
            ),
            "manuscript_role": "primary_empirical_positive",
            "evidence_state": "completed_positive_existing_label_audit_emulation",
            "primary_artifact": rel(PHASE63 / "table_parc_a_primary_gate.csv"),
            "display_item": "Figure 3",
            "allowed_language": "verification-budgeted release; existing-label one-sided audit emulation",
            "forbidden_language": "new human audit unless Phase78 completes; materials discovery",
            "overclaim_guardrail": "disclose_masked_label_emulation",
        },
        {
            "claim_id": "PARC-A-MECHANISM",
            "claim_text": (
                f"At 0.2% score-targeted audit, CTC reaches {numbers['ctc_fine_budget_safe_seeds']}/20 safe seeds; "
                f"high-score positives remove calibration block maxima {numbers['ctc_blockmax_multiplier']}x more than random."
            ),
            "manuscript_role": "mechanism_support",
            "evidence_state": "completed_mechanism_diagnostic",
            "primary_artifact": rel(PHASE65B / "table_parc_a_mechanism_gate.csv"),
            "display_item": "Figure 3",
            "allowed_language": "active audit gain mechanism",
            "forbidden_language": "generic score threshold alone explains the lifecycle",
            "overclaim_guardrail": "mechanism_support_not_new_labels",
        },
        {
            "claim_id": "PHASE76-LIFECYCLE",
            "claim_text": "Phase76 defines the lifecycle states: certified release/refusal, expiry, recertification, risk triage and active audit.",
            "manuscript_role": "conceptual_framework",
            "evidence_state": "completed_synthesis",
            "primary_artifact": rel(PHASE76 / "table_release_card_states.csv"),
            "display_item": "Figure 1",
            "allowed_language": "release-card lifecycle calculus",
            "forbidden_language": "standalone empirical positive",
            "overclaim_guardrail": "phase76_is_scaffold_not_new_result",
        },
        {
            "claim_id": "MATERIALS-STRESS",
            "claim_text": "Materials is a lifecycle stress test: t0 release cards expire under current-MP updates and recertification returns refusal/no-go.",
            "manuscript_role": "materials_stress_test",
            "evidence_state": "completed_boundary_and_no_go",
            "primary_artifact": rel(PHASE76 / "table_lifecycle_replay_materials.csv"),
            "display_item": "Figure 4",
            "allowed_language": "version-bound durability stress test; recertification refusal",
            "forbidden_language": "current-MP alpha certificate, DFT validation, or prospective discovery",
            "overclaim_guardrail": "materials_not_main_positive",
        },
        {
            "claim_id": "PARC-D-TRIAGE",
            "claim_text": (
                f"Durability-risk triage is positive but scoped: dropping the top "
                f"{numbers['triage_flagged_fraction']:.0%} high-risk rows leaves retained flip rate "
                f"{numbers['triage_retained_flip_rate']:.3f} versus base {numbers['triage_base_flip_rate']:.3f}; "
                f"the flagged rows contain {numbers['triage_flips_flagged']:.1%} of observed flips; "
                "it is not a repaired alpha certificate."
            ),
            "manuscript_role": "risk_triage_positive",
            "evidence_state": "completed_risk_triage_positive_not_certificate",
            "primary_artifact": rel(PHASE69 / "table_risk_triage_frontier.csv"),
            "display_item": "Figure 5",
            "allowed_language": "t0 public-label release-card risk triage",
            "forbidden_language": "label-free deployment predictor or full alpha certificate",
            "overclaim_guardrail": "triage_not_certificate",
        },
        {
            "claim_id": "PARC-D-CERT-NOGO",
            "claim_text": (
                f"Risk-gated recertification is no-go: Phase74 K={numbers['phase74_k']} primary row returns "
                f"{numbers['phase74_nonempty']}/20 non-empty seeds."
            ),
            "manuscript_role": "boundary_no_go",
            "evidence_state": "completed_no_go",
            "primary_artifact": rel(PHASE74 / "table_risk_gated_primary_row.csv"),
            "display_item": "Figure 4; Supplement",
            "allowed_language": "risk-gated recertification refuses",
            "forbidden_language": "near-success current-MP certificate",
            "overclaim_guardrail": "do_not_soften_no_go",
        },
        {
            "claim_id": "ACTIVE-RECERT-NOGO",
            "claim_text": (
                f"Active current-MP recertification is no-go: best row has {numbers['phase75_best_nonempty']}/20 "
                f"non-empty seeds, {numbers['phase75_best_safe']}/20 safe seeds and FTR {numbers['phase75_best_ftr']:.3f}."
            ),
            "manuscript_role": "boundary_no_go",
            "evidence_state": "completed_no_go",
            "primary_artifact": rel(PHASE75 / "table_active_recertification_policy_comparison.csv"),
            "display_item": "Figure 4; Supplement",
            "allowed_language": "targeted t1 support does not repair materials recertification",
            "forbidden_language": "constructive materials positive",
            "overclaim_guardrail": "phase75_no_go_explicit",
        },
        {
            "claim_id": "DFT-V2-PENDING",
            "claim_text": (
                f"DFT v2 is optional and pending: {numbers['dft_completed']} completed, {numbers['dft_failed']} failed, "
                "no stable_exact outcomes."
            ),
            "manuscript_role": "pending_bonus_not_core",
            "evidence_state": "execution_checkpoint_only",
            "primary_artifact": rel(PHASE70 / "table_dft_v2_execution_checkpoint_summary.csv"),
            "display_item": "Supplement only unless gates pass",
            "allowed_language": "ongoing blinded recomputation checkpoint",
            "forbidden_language": "DFT validation, stable/unstable outcome, or prospective discovery",
            "overclaim_guardrail": "exclude_from_core_until_claim_ready",
        },
    ]
    df = pd.DataFrame(rows)
    df["evidence_scope"] = SCOPE
    return df


def write_spine(numbers: dict[str, object]) -> None:
    abstract = (
        "Scientific AI pipelines increasingly produce finite candidate queues faster than they can be verified. "
        "We introduce PARC as a release-card lifecycle framework: it certifies release or refusal under one-sided "
        "verification, directs scarce verification budgets, records reference-version expiry and routes expired "
        "certificates to recertification, risk triage or refusal. In CTC cell tracking, targeted one-sided audit "
        f"certifies {numbers['ctc_total_released']} links across 20 seeds with no observed false releases, whereas "
        "random audit requires far more verification. Materials screening then stress-tests the lifecycle: t0 public-label "
        "release cards expire under a current-MP hull update; durability risk is predictable from t0 public-label "
        "chemical-system state, but passive and active current-MP recertification refuse. PARC therefore treats refusal, "
        "expiry and risk triage as first-class scientific outputs rather than failures to hide."
    )
    text = f"""# Phase77 NCS Architecture Freeze

Status: `completed_NCS_architecture_freeze`.

## Recommended Title

**Budgeted release certification for scientific AI candidate queues**

Alternative: **Release-card lifecycle certification for scientific AI candidate queues**

## One-sentence Claim

Scientific AI candidate pipelines need release cards rather than static top-K
lists: PARC certifies release or refusal under one-sided verification, PARC-A
shows how scarce targeted audits unlock certified release, and lifecycle
recertification prevents expired certificates from being inherited after
reference drift.

## Finding-first Abstract Skeleton

{abstract}

## Result Order

1. PARC defines one-sided release/refusal certificates for finite candidate queues.
2. Release cards have a lifecycle: certified release/refusal, active audit,
   expiry, recertification, risk triage and refusal.
3. PARC-A is the primary empirical positive in CTC: targeted audit converts
   scarce one-sided verification into certified release.
4. Materials is the lifecycle stress test, not the main positive: t0 public
   release cards expire after current-MP reference drift and recertification
   refuses.
5. PARC-D provides risk triage, not alpha repair.
6. Capability/reproducibility ledger distinguishes PARC lifecycle from
   e-BH-style selection, raw top-K and threshold baselines.

## Stop Rules

- Stop tuning materials K, margin, risk gates or active recertification.
- Do not add new visual/open-world domains.
- Do not wait for DFT v2 before rewriting the manuscript.
- DFT v2 enters only if stable_exact and workflow gates pass.
- The only new empirical study worth adding before writing is Phase78 CTC real
  one-sided audit.

## Evidence Boundary

The NCS core is PARC lifecycle + PARC-A CTC active verification. Materials is a
versioned lifecycle stress test showing expiry, risk triage and refusal. It is
not a prospective materials-discovery claim and not a current-MP alpha
certificate.
"""
    (OUT / "NCS_SPINE.md").write_text(text, encoding="utf-8")


def write_display_plan(numbers: dict[str, object]) -> None:
    text = f"""# NCS Display Plan

Each main figure has one dominant claim.  Dense robustness, no-go grids and DFT
execution details move to Extended Data or Supplement unless they are needed to
understand the lifecycle.

## Figure 1: Release-card lifecycle calculus

**Claim:** PARC turns static candidate queues into versioned release cards with
release, refusal, active audit, expiry, recertification and risk-triage states.

- Panel A, methodological bridge: candidate queue to release card.
- Panel B, definition: lifecycle state machine from `table_release_card_states`.
- Panel C, schema: required release-card fields from `release_card_schema.json`.
- Panel D, translational consequence: lifecycle replay overview for CTC and
  materials.
- Anchor panel: B.
- Main-text topic sentence: Scientific candidate publication is a lifecycle
  decision, not a one-shot top-K list.

## Figure 2: PARC release/refusal mechanism

**Claim:** One-sided null-superset evidence and self-consistency make both
release and refusal valid outputs.

- Panel A, definition: verified positives versus unverified candidates.
- Panel B, claim-supporting method: calibration null-superset block maxima.
- Panel C, method: e-values and self-consistency threshold.
- Panel D, failure mode: certified refusal when evidence mass is insufficient.
- Anchor panel: C.
- Main-text topic sentence: PARC keeps unverified candidates in the null
  superset and refuses when the release-card evidence is insufficient.

## Figure 3: PARC-A active verification primary positive

**Claim:** Targeted one-sided audit unlocks certified CTC release at tiny
verification budgets where random audit does not.

- Panel A, setup: CTC K=100 active-audit task.
- Panel B, anchor evidence: {numbers['ctc_safe_seeds']}/20 safe seeds,
  {numbers['ctc_total_released']} released links, observed FTR
  {numbers['ctc_mean_ftr']}.
- Panel C, benchmark comparison: random requires roughly
  {numbers['ctc_random_full_multiplier']:.0f}x the targeted budget.
- Panel D, mechanism: score-targeted positives remove null-superset block maxima
  {numbers['ctc_blockmax_multiplier']:.1f}x more than random at the fine-grid
  mechanism point.
- Anchor panel: B.
- Main-text topic sentence: PARC-A converts verification budget into release
  evidence rather than treating missing labels as negatives.

## Figure 4: Materials lifecycle stress test

**Claim:** Materials screening demonstrates why release cards must expire and
recertify under reference drift; it is not the main positive.

- Panel A, lifecycle timeline: t0 public-label release to current-MP t1 update.
- Panel B, version accounting: inherited release burden after reference update.
- Panel C, recertification boundary: Phase74 risk-gated recertification returns
  {numbers['phase74_nonempty']}/20 non-empty seeds.
- Panel D, active recertification boundary: Phase75 best row has
  {numbers['phase75_best_nonempty']}/20 non-empty and
  {numbers['phase75_best_safe']}/20 safe seeds.
- Anchor panel: C.
- Main-text topic sentence: After the reference changes, the correct lifecycle
  action is expiry plus recertification or refusal, not inherited publication.

## Figure 5: Durability-risk triage

**Claim:** t0 public-label chemical-system state predicts durability risk and
supports triage, but does not repair alpha certification.

- Panel A, model comparison: candidate margin/rank versus system features.
- Panel B, anchor evidence: dropping the top
  {numbers['triage_flagged_fraction']:.0%} high-risk rows leaves retained flip
  rate {numbers['triage_retained_flip_rate']:.3f} versus base
  {numbers['triage_base_flip_rate']:.3f}, while the flagged rows contain
  {numbers['triage_flips_flagged']:.1%} of observed flips.
- Panel C, decision map: low-risk retain, high-risk recertify/audit.
- Panel D, boundary: post-filter and risk-gated self-consistency failures.
- Anchor panel: B.
- Main-text topic sentence: Durability risk is a release-card triage signal, not
  a label-free deployment predictor or current-MP certificate.

## Figure 6: Lifecycle capability and claim ledger

**Claim:** PARC lifecycle differs from e-BH-style selection because it supports
one-sided evidence construction, refusal, audit acquisition, expiry,
recertification and release cards.

- Panel A, capability matrix: PARC lifecycle versus e-BH, raw top-K, threshold,
  conformal and PU baselines.
- Panel B, evidence hierarchy: completed positive, stress test, no-go, pending.
- Panel C, reproducibility ledger: claim-to-artifact mapping.
- Panel D, optional slot: DFT v2 enters only after stable_exact and workflow
  gates pass.
- Anchor panel: A.
- Main-text topic sentence: The contribution is a lifecycle capability rather
  than another static selector.

## Supplement Priority

- Full materials K/margin/risk-gate grids.
- Phase74/75 no-go details.
- DFT v2 execution checkpoint.
- Extended baseline risk-utility tables.
- Additional schema fields and release-card examples.
"""
    (OUT / "NCS_DISPLAY_PLAN.md").write_text(text, encoding="utf-8")


def write_guardrails() -> None:
    rows = [
        ("G1", "Do not claim prospective materials discovery.", "Use: versioned public-label lifecycle stress test."),
        ("G2", "Do not claim current-MP alpha certificate from materials.", "Use: expiry/refusal/risk-triage under current-MP audit."),
        ("G3", "Do not call Phase69b PARC-D a full certificate.", "Use: release-card risk triage, not alpha repair."),
        ("G4", "Do not soften Phase74 or Phase75 no-go.", "Use: principled recertification refusal/no-go."),
        ("G5", "Do not claim DFT v2 evidence before stable_exact outcomes and gates pass.", "Use: optional blinded checkpoint."),
        ("G6", "Do not call CTC active audit new human labels unless Phase78 completes.", "Use: masked-label one-sided audit emulation."),
        ("G7", "Do not frame PARC as a generator or model zoo.", "Use: release-card lifecycle layer."),
        ("G8", "Do not claim broad success across all domains.", "Use: primary CTC positive plus materials lifecycle stress test."),
        ("G9", "Do not present e-BH as a strawman FTR baseline.", "Compare lifecycle capabilities."),
        ("G10", "Do not add new materials filters to rescue alpha.", "Stop materials fast-fix route after Phase75."),
    ]
    text = "# NCS Overclaim Guardrails\n\n"
    for gid, forbidden, replacement in rows:
        text += f"## {gid}\n\nForbidden: {forbidden}\n\nAllowed replacement: {replacement}\n\n"
    (OUT / "NCS_OVERCLAIM_GUARDRAILS.md").write_text(text, encoding="utf-8")


def write_readme(status: str) -> None:
    text = f"""# Phase77 NCS Architecture Freeze

Status: `{status}`.

This milestone freezes the NCS paper architecture after Phase76. It supplies
the spine, claim hierarchy, display plan and overclaim guardrails. It is not a
new experiment and should not be used to create new empirical claims.

Frozen interpretation:

- primary empirical positive: PARC-A in CTC active verification;
- main conceptual scaffold: PARC release-card lifecycle calculus;
- materials role: lifecycle stress test with expiry, refusal and risk triage;
- DFT v2 role: optional checkpoint until claim-ready;
- no further materials K/margin/gate tuning should be used for the main story.
"""
    (OUT / "README_evidence_scope.md").write_text(text, encoding="utf-8")


def update_artifact_index(status: str) -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase77_ncs_architecture_freeze"]
    rows.append(
        {
            "milestone": "ncs_phase77_ncs_architecture_freeze",
            "path": "outputs/milestones/ncs_phase77_ncs_architecture_freeze/",
            "evidence_state": status,
            "manifest": "outputs/milestones/ncs_phase77_ncs_architecture_freeze/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase77_ncs_architecture_freeze",
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["milestone", "path", "evidence_state", "manifest", "public_bundle_check"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def update_claim_table(status: str) -> None:
    path = ROOT / "docs/claim_table.md"
    text = path.read_text(encoding="utf-8")
    marker = "## Phase77 NCS Architecture Freeze"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n"
    addition = f"""

## Phase77 NCS Architecture Freeze

Status: `{status}`.

Phase77 freezes the NCS manuscript spine around PARC release-card lifecycle
certification. The primary empirical positive is PARC-A in CTC active
verification. Materials is frozen as a lifecycle stress test showing
reference-version expiry, risk triage and recertification/refusal boundaries.
Phase77 explicitly stops further materials fast-fix tuning from entering the
main story.
"""
    path.write_text(text.rstrip() + addition, encoding="utf-8")


def update_evidence_ledger(status: str) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["claim_id"] != "NCS-ARCH-001"]
    artifact = OUT / "NCS_CLAIM_HIERARCHY.csv"
    rows.append(
        {
            "claim_id": "NCS-ARCH-001",
            "claim_text": "The NCS manuscript architecture is frozen around PARC lifecycle calculus, PARC-A CTC primary positive, and materials lifecycle stress-test boundaries.",
            "evidence_type": "manuscript_architecture_freeze",
            "positive_evidence": "yes",
            "scope": status,
            "artifact_path": rel(artifact),
            "hash": sha256_file(artifact),
            "validation_command": "make reproduce-ncs-phase77-architecture-freeze",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_new_empirical_evidence_materials_alpha_certificate_or_DFT_validation",
        }
    )
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "claim_id",
                "claim_text",
                "evidence_type",
                "positive_evidence",
                "scope",
                "artifact_path",
                "hash",
                "validation_command",
                "status",
                "overclaim_guardrail",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    status = "completed_NCS_architecture_freeze"
    numbers = load_numbers()
    claims = build_claim_hierarchy(numbers)
    claims.to_csv(OUT / "NCS_CLAIM_HIERARCHY.csv", index=False)
    write_spine(numbers)
    write_display_plan(numbers)
    write_guardrails()
    write_readme(status)
    provenance = {
        "status": status,
        "phase": "phase77",
        "source_phase76": rel(PHASE76),
        "source_phase63": rel(PHASE63),
        "source_phase69": rel(PHASE69),
        "scope": SCOPE,
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    write_manifest(OUT)
    update_artifact_index(status)
    update_claim_table(status)
    update_evidence_ledger(status)
    write_root_manifest()
    print(json.dumps({"status": status, "out_dir": rel(OUT)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
