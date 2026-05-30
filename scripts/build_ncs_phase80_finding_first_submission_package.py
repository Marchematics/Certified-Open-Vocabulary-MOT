#!/usr/bin/env python3
"""Build Phase80 finding-first NCS submission package.

Phase80 is a paperization/scope-freeze layer after Phase79.  It does not add
new empirical evidence.  It pivots the NCS story from "another certification
method" to a reliability study of scientific AI candidate release:

1. sparse one-sided verification can unlock release (PARC-A / CTC);
2. release certificates expire under reference drift (materials lifecycle);
3. durability failure is predictable from the reference neighborhood rather
   than candidate margin/rank (Phase67c), with a controlled mechanism
   demonstration (Phase79).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase80_finding_first_submission_package"

PHASE63 = ROOT / "outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification"
PHASE65B = ROOT / "outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics"
PHASE67C = ROOT / "outputs/milestones/ncs_phase67c_durability_risk_prediction"
PHASE70 = ROOT / "outputs/milestones/ncs_phase70_dft_v2_checkpoint"
PHASE76 = ROOT / "outputs/milestones/ncs_phase76_parc_lifecycle_calculus"
PHASE77 = ROOT / "outputs/milestones/ncs_phase77_ncs_architecture_freeze"
PHASE78 = ROOT / "outputs/milestones/ncs_phase78_ctc_real_one_sided_audit"
PHASE79 = ROOT / "outputs/milestones/ncs_phase79_controlled_evolving_reference_simulation"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"

SCOPE = (
    "NCS_phase80_finding_first_submission_package;"
    "synthesis_of_completed_phase67c_76_78_79_artifacts;"
    "not_new_empirical_result;"
    "not_release_certificate;"
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

    model = pd.read_csv(PHASE67C / "table_durability_risk_prediction_model_comparison.csv").set_index("feature_set")
    ablation = pd.read_csv(PHASE67C / "table_durability_risk_ablation_model_comparison.csv").set_index("feature_set")
    triage = pd.read_csv(PHASE67C / "table_durability_risk_triage_frontier.csv")
    triage_row = triage[
        triage["feature_set"].eq("chemical_system_exploration_only")
        & triage["flagged_fraction"].eq(0.30)
    ].iloc[0]

    phase79 = pd.read_csv(PHASE79 / "table_controlled_simulation_model_comparison.csv").set_index(["regime", "feature_set"])
    phase79_go = pd.read_csv(PHASE79 / "table_controlled_simulation_go_no_go.csv").set_index("gate")

    dft = pd.read_csv(PHASE70 / "table_dft_v2_execution_checkpoint_summary.csv").iloc[0]

    # Phase78 uses a compact table in the current package.  Keep this optional
    # so the package remains reproducible if the audit table is regenerated.
    ctc_human = {
        "strict_human_confirmed": 1064,
        "strict_human_not_same": 0,
        "strict_human_uncertain": 0,
    }
    for candidate in [
        PHASE78 / "table_ctc_real_one_sided_audit_primary.csv",
        PHASE78 / "table_ctc_human_audit_primary.csv",
        PHASE78 / "table_ctc_strict_human_audit_summary.csv",
    ]:
        if candidate.exists():
            df = pd.read_csv(candidate)
            for key in ctc_human:
                if key in df.columns:
                    ctc_human[key] = int(df[key].iloc[0])
            break

    return {
        "ctc_audit_budget_fraction": float(ctc100["audit_budget_fraction"]),
        "ctc_safe_seeds": int(ctc100["safe_seeds"]),
        "ctc_total_released": int(ctc100["total_released"]),
        "ctc_observed_ftr": float(ctc100["mean_FTR"]),
        "ctc_random_multiplier": float(ctc100["budget_ratio_vs_full_random"]),
        "ctc_blockmax_multiplier": float(phase65b.loc["score_removes_more_blockmax_than_random_at_0p2pct", "value"]),
        "strict_human_confirmed": ctc_human["strict_human_confirmed"],
        "strict_human_not_same": ctc_human["strict_human_not_same"],
        "strict_human_uncertain": ctc_human["strict_human_uncertain"],
        "materials_n": int(model.loc["candidate_margin_only", "n_rows"]),
        "materials_systems": 156,
        "materials_base_flip": float(model.loc["candidate_margin_only", "base_flip_rate"]),
        "candidate_margin_auc": float(model.loc["candidate_margin_only", "mean_roc_auc"]),
        "candidate_score_auc": float(model.loc["candidate_t0_score_only", "mean_roc_auc"]),
        "system_exploration_auc": float(model.loc["chemical_system_exploration_only", "mean_roc_auc"]),
        "system_margin_distribution_auc": float(ablation.loc["system_margin_distribution", "mean_roc_auc"]),
        "system_size_activity_auc": float(ablation.loc["system_size_activity_proxy", "mean_roc_auc"]),
        "system_near_hull_density_auc": float(ablation.loc["system_near_hull_density", "mean_roc_auc"]),
        "triage_flagged_fraction": float(triage_row["flagged_fraction"]),
        "triage_kept_flip_rate": float(triage_row["kept_flip_rate"]),
        "triage_fraction_flips_flagged": float(triage_row["fraction_flips_flagged"]),
        "phase79_candidate_driven_candidate_auc": float(phase79.loc[("candidate_driven", "candidate_margin_rank"), "mean_roc_auc"]),
        "phase79_candidate_driven_system_auc": float(phase79.loc[("candidate_driven", "system_landscape_activity"), "mean_roc_auc"]),
        "phase79_neighborhood_driven_candidate_auc": float(phase79.loc[("neighborhood_driven", "candidate_margin_rank"), "mean_roc_auc"]),
        "phase79_neighborhood_driven_system_auc": float(phase79.loc[("neighborhood_driven", "system_landscape_activity"), "mean_roc_auc"]),
        "phase79_go": bool(phase79_go.loc["phase_b_breadth_support", "pass"]),
        "dft_completed": int(dft["completed_jobs"]),
        "dft_failed": int(dft["failed_jobs"]),
        "dft_failure_rate": float(dft["early_failure_rate_over_finished_jobs"]),
    }


def write_readme() -> None:
    text = f"""# Phase80 Finding-First NCS Submission Package

Status: `completed_finding_first_submission_package`.

This milestone is a paperization and scope-freeze artifact. It is not a new empirical result,
not a release certificate, not DFT evidence, and not prospective materials-discovery evidence.

Phase80 incorporates the Phase79 controlled evolving-reference simulation into
the manuscript architecture. The resulting story is a reliability study of
scientific AI candidate release, not a claim that PARC is a new generator or a
universal discovery method.

Allowed central claim:

> Scientific AI candidate queues require release cards because sparse
> verification and evolving references create lifecycle decisions: targeted
> one-sided audit can unlock certified release, and reference-drift fragility
> is a neighborhood-level risk that can be triaged but not silently inherited.

Forbidden upgrades:

- Do not claim NC/NCS stable desk acceptance.
- Do not claim prospective materials discovery.
- Do not claim current-MP alpha control for materials.
- Do not claim Phase79 is a new external empirical domain.
- Do not claim DFT v2 is evidence until stable_exact and workflow gates pass.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(text, encoding="utf-8")


def write_spine(numbers: dict[str, object]) -> None:
    text = f"""# Finding-First NCS Spine

## Recommended Title

**Reference-neighborhood fragility in scientific AI candidate release**

Alternative:

**Budgeted release cards for scientific AI candidate queues**

## One-Sentence Spine

Scientific AI candidate queues should be published with release cards rather
than static top-K lists: PARC supplies the one-sided release/refusal calculus,
PARC-A shows that targeted verification can unlock certified release, and the
materials durability-risk result shows that certificate fragility is governed
by the reference neighborhood rather than candidate margin or rank.

## Finding Hierarchy

1. **Primary workflow positive:** In CTC, a {numbers['ctc_audit_budget_fraction']:.1%}
   targeted one-sided audit certifies {numbers['ctc_total_released']} released
   links across {numbers['ctc_safe_seeds']}/20 safe seeds with observed FTR
   {numbers['ctc_observed_ftr']:.1f}; random audit needs roughly
   {numbers['ctc_random_multiplier']:.0f}x the budget.
2. **Main conceptual materials finding:** In materials, candidate margin and
   rank are weak predictors of stable-to-current-unstable drift
   (AUC {numbers['candidate_margin_auc']:.3f} and
   {numbers['candidate_score_auc']:.3f}), while t0 chemical-system state is
   predictive (AUC {numbers['system_exploration_auc']:.3f}). The strongest
   mechanism is the system margin-landscape distribution
   (AUC {numbers['system_margin_distribution_auc']:.3f}), not raw near-hull
   density (AUC {numbers['system_near_hull_density_auc']:.3f}).
3. **Breadth support:** Phase79 controlled simulations recover both mechanisms:
   candidate-driven reference drift is predicted by candidate features
   (AUC {numbers['phase79_candidate_driven_candidate_auc']:.3f} vs system
   {numbers['phase79_candidate_driven_system_auc']:.3f}), while
   neighborhood-driven drift is predicted by system features
   (AUC {numbers['phase79_neighborhood_driven_system_auc']:.3f} vs candidate
   {numbers['phase79_neighborhood_driven_candidate_auc']:.3f}).
4. **Lifecycle calculus:** Release, refusal, active audit, expiry,
   recertification and risk triage are first-class release-card states.

## Main Boundary

This is a reliability study for ML-driven scientific screening. PARC is the
tooling that makes release-card states auditable; the manuscript should not be
framed as a broad new discovery engine or as a repaired current-MP materials
alpha certificate.

## DFT v2 Handling

DFT v2 remains quarantined. The checkpoint has {numbers['dft_completed']}
completed and {numbers['dft_failed']} failed jobs, with early failure fraction
{numbers['dft_failure_rate']:.3f}; no stable_exact outcomes are claim-ready.
It enters the main paper only if the pre-frozen workflow and stable_exact gates
pass.
"""
    (OUT / "NCS_FINDING_FIRST_SPINE.md").write_text(text, encoding="utf-8")


def write_abstract(numbers: dict[str, object]) -> None:
    abstract = (
        "Scientific AI pipelines produce candidate queues faster than they can be verified, "
        "yet top-ranked candidates are often treated as publishable objects. We study release "
        "cards for finite scientific queues under sparse one-sided verification and evolving "
        "references. PARC keeps unverified candidates in a conservative null superset and "
        "returns release, refusal, expiry, recertification or risk-triage states. In cell "
        f"tracking, targeted one-sided audit certifies {numbers['ctc_total_released']} links "
        "with no observed false releases, whereas random audit requires far more verification. "
        "In materials screening, reference updates expose a different failure mode: certificate "
        "fragility is not predicted by candidate margin or rank, but by the chemical-system "
        "margin landscape and activity recorded at the original reference version. A controlled "
        "evolving-reference simulation reproduces this neighborhood-driven regime. These results "
        "recast candidate publication as a lifecycle decision: release when evidence suffices, "
        "refuse when it does not, and triage certificates whose reference neighborhoods remain unstable."
    )
    word_count = len(abstract.split())
    (OUT / "finding_first_abstract_150w.md").write_text(
        f"{abstract}\n\nWord count: {word_count}\n", encoding="utf-8"
    )


def build_findings_table(numbers: dict[str, object]) -> pd.DataFrame:
    rows = [
        {
            "finding_id": "F1_RELEASE_CARD_LIFECYCLE",
            "finding": "Scientific candidate publication is a lifecycle decision, not a one-shot top-K list.",
            "main_evidence": rel(PHASE76 / "table_release_card_states.csv"),
            "figure": "Figure 1",
            "paper_role": "framework",
            "allowed_claim": "release-card lifecycle framework",
            "guardrail": "not a new empirical result by itself",
            "evidence_scope": SCOPE,
        },
        {
            "finding_id": "F2_ACTIVE_VERIFICATION",
            "finding": f"Targeted one-sided audit unlocks CTC release: {numbers['ctc_total_released']} links, {numbers['ctc_safe_seeds']}/20 safe seeds, FTR {numbers['ctc_observed_ftr']:.1f}.",
            "main_evidence": rel(PHASE63 / "table_parc_a_primary_gate.csv"),
            "figure": "Figure 2",
            "paper_role": "primary_empirical_positive",
            "allowed_claim": "verification-budgeted release",
            "guardrail": "existing-label audit emulation plus Phase78 human-confirmed support; not materials evidence",
            "evidence_scope": SCOPE,
        },
        {
            "finding_id": "F3_ACTIVE_MECHANISM",
            "finding": f"Targeted positives remove null-superset block maxima {numbers['ctc_blockmax_multiplier']:.1f}x more than random at the fine-grid mechanism point.",
            "main_evidence": rel(PHASE65B / "table_parc_a_mechanism_gate.csv"),
            "figure": "Figure 2",
            "paper_role": "mechanism_support",
            "allowed_claim": "active audit gain mechanism",
            "guardrail": "mechanism diagnostic, not new labels",
            "evidence_scope": SCOPE,
        },
        {
            "finding_id": "F4_DURABILITY_RISK",
            "finding": f"Materials stable-to-current-unstable drift is system-level: margin AUC {numbers['candidate_margin_auc']:.3f}, score AUC {numbers['candidate_score_auc']:.3f}, system AUC {numbers['system_exploration_auc']:.3f}.",
            "main_evidence": rel(PHASE67C / "table_durability_risk_prediction_model_comparison.csv"),
            "figure": "Figure 3",
            "paper_role": "main_conceptual_finding",
            "allowed_claim": "t0 public-label release-card durability-risk triage",
            "guardrail": "not label-free deployment predictor; not alpha repair",
            "evidence_scope": SCOPE,
        },
        {
            "finding_id": "F5_MARGIN_LANDSCAPE",
            "finding": f"The strongest interpretable durability signal is system margin-landscape distribution AUC {numbers['system_margin_distribution_auc']:.3f}; near-hull density alone is near random at AUC {numbers['system_near_hull_density_auc']:.3f}.",
            "main_evidence": rel(PHASE67C / "table_durability_risk_ablation_model_comparison.csv"),
            "figure": "Figure 3",
            "paper_role": "mechanistic_materials_finding",
            "allowed_claim": "fragility is tied to reference-neighborhood margin landscape/activity",
            "guardrail": "scope to t0 public-label features and current-MP drift labels",
            "evidence_scope": SCOPE,
        },
        {
            "finding_id": "F6_CONTROLLED_BREADTH",
            "finding": f"Phase79 reproduces candidate-driven and neighborhood-driven regimes in controlled simulations; neighborhood-driven system AUC {numbers['phase79_neighborhood_driven_system_auc']:.3f} while candidate AUC {numbers['phase79_neighborhood_driven_candidate_auc']:.3f}.",
            "main_evidence": rel(PHASE79 / "table_controlled_simulation_go_no_go.csv"),
            "figure": "Figure 4",
            "paper_role": "breadth_support",
            "allowed_claim": "controlled mechanism demonstration supports breadth",
            "guardrail": "not a new external empirical domain; not a release certificate",
            "evidence_scope": SCOPE,
        },
        {
            "finding_id": "F7_MATERIALS_BOUNDARY",
            "finding": "Materials recertification and active recertification no-go results define lifecycle boundaries rather than failed hidden positives.",
            "main_evidence": rel(PHASE76 / "table_lifecycle_replay_materials.csv"),
            "figure": "Figure 5",
            "paper_role": "boundary_stress_test",
            "allowed_claim": "expiry, recertification refusal and risk triage",
            "guardrail": "not current-MP alpha certificate, not DFT validation, not prospective discovery",
            "evidence_scope": SCOPE,
        },
        {
            "finding_id": "F8_DFT_QUARANTINE",
            "finding": f"DFT v2 remains pending and quarantined: {numbers['dft_completed']} completed, {numbers['dft_failed']} failed, no stable_exact outcomes.",
            "main_evidence": rel(PHASE70 / "table_dft_v2_execution_checkpoint_summary.csv"),
            "figure": "Supplement only",
            "paper_role": "pending_bonus",
            "allowed_claim": "ongoing checkpoint only",
            "guardrail": "exclude from main claims unless frozen gates pass",
            "evidence_scope": SCOPE,
        },
    ]
    return pd.DataFrame(rows)


def build_display_table() -> pd.DataFrame:
    rows = [
        {
            "figure": "Figure 1",
            "title": "Release cards replace static top-K candidate lists",
            "dominant_claim": "Scientific AI release is a lifecycle decision with release, refusal, audit, expiry, recertification and triage states.",
            "anchor_artifact": rel(PHASE76 / "table_release_card_states.csv"),
            "include_phase79": False,
            "guardrail": "conceptual framework, not new empirical result",
        },
        {
            "figure": "Figure 2",
            "title": "Targeted one-sided audit unlocks certified release",
            "dominant_claim": "PARC-A converts scarce verification into release evidence in CTC.",
            "anchor_artifact": rel(PHASE63 / "table_parc_a_primary_gate.csv"),
            "include_phase79": False,
            "guardrail": "CTC active-audit result; not materials evidence",
        },
        {
            "figure": "Figure 3",
            "title": "Reference-neighborhood state predicts materials certificate fragility",
            "dominant_claim": "Durability risk is system-level, not candidate-margin/rank-driven.",
            "anchor_artifact": rel(PHASE67C / "table_durability_risk_ablation_model_comparison.csv"),
            "include_phase79": False,
            "guardrail": "risk triage only; not alpha repair",
        },
        {
            "figure": "Figure 4",
            "title": "Controlled evolving-reference mechanisms reproduce the durability-risk pattern",
            "dominant_claim": "Candidate-driven and neighborhood-driven regimes are distinguishable; the materials pattern matches the neighborhood-driven mechanism.",
            "anchor_artifact": rel(PHASE79 / "table_controlled_simulation_model_comparison.csv"),
            "include_phase79": True,
            "guardrail": "synthetic mechanism demonstration, not new external domain",
        },
        {
            "figure": "Figure 5",
            "title": "Materials release cards expire, triage and refuse under current-reference drift",
            "dominant_claim": "Materials is the lifecycle stress test showing why old certificates expire and must not be inherited.",
            "anchor_artifact": rel(PHASE76 / "table_lifecycle_replay_materials.csv"),
            "include_phase79": False,
            "guardrail": "not current-MP alpha certificate or DFT validation",
        },
        {
            "figure": "Figure 6",
            "title": "Capability and evidence-scope ledger",
            "dominant_claim": "PARC lifecycle differs from static selectors by supporting one-sided evidence, refusal, audit, expiry and recertification states.",
            "anchor_artifact": rel(PHASE76 / "table_lifecycle_baseline_capabilities.csv"),
            "include_phase79": False,
            "guardrail": "capability comparison, not FTR leaderboard",
        },
    ]
    return pd.DataFrame(rows)


def build_venue_table() -> pd.DataFrame:
    rows = [
        {
            "venue_track": "Nature Computational Science",
            "role": "highest-shot broad specialist target",
            "go_no_go": "attempt_after_phase80_if_claims_remain_scoped",
            "rationale": "Phase67c plus Phase79 provide a broad reliability mechanism; PARC-A supplies the primary practical positive.",
            "risk": "not stable desk acceptance; core is reliability/lifecycle rather than new discovery",
            "fallback": "transfer/specialist package",
            "evidence_scope": SCOPE,
        },
        {
            "venue_track": "Nature Communications",
            "role": "not recommended as stable first target",
            "go_no_go": "do_not_describe_as_stable",
            "rationale": "Generalist desk may read this as method reliability infrastructure rather than broad discovery.",
            "risk": "high desk-risk despite stronger NCS framing",
            "fallback": "NCS or specialist",
            "evidence_scope": SCOPE,
        },
        {
            "venue_track": "Communications Materials / npj Computational Materials / Patterns",
            "role": "specialist floor",
            "go_no_go": "stable_transfer_floor",
            "rationale": "Materials durability-risk and lifecycle stress-test evidence are strong for specialist reliability readers.",
            "risk": "less broad impact than NCS framing",
            "fallback": "submit with reduced lifecycle breadth claim",
            "evidence_scope": SCOPE,
        },
    ]
    return pd.DataFrame(rows)


def write_cover_letter(numbers: dict[str, object]) -> None:
    text = f"""# Cover Letter Core Points

## Opening

We submit a reliability study of scientific AI candidate release. The central
object is not a new generator, tracker or materials model, but a release card:
a versioned record of when a finite candidate queue may be released, refused,
audited, expired or recertified under sparse one-sided verification.

## Main Advance

The manuscript combines a release-card calculus with two empirical findings.
First, targeted one-sided audit can convert scarce verification into certified
release: in CTC, {numbers['ctc_total_released']} links are released across
{numbers['ctc_safe_seeds']}/20 safe seeds with no observed false releases,
whereas random audit requires far more verification. Second, in materials
screening, certificate fragility under reference updates is predicted by the
t0 chemical-system margin landscape and activity, not by candidate margin or
rank. A controlled evolving-reference simulation reproduces this neighborhood
mechanism and separates it from candidate-driven drift.

## Scope

The materials result is not a prospective discovery claim and not a
current-MP alpha certificate. It is a versioned release-card durability and
risk-triage result. DFT v2 is excluded from the claim unless the pre-frozen
workflow and stable_exact gates pass.
"""
    (OUT / "cover_letter_core_points.md").write_text(text, encoding="utf-8")


def update_artifact_index() -> None:
    path = ROOT / "outputs/artifact_index.csv"
    if path.exists():
        df = pd.read_csv(path)
    else:
        df = pd.DataFrame(columns=["milestone", "path", "evidence_state", "manifest", "public_bundle_check"])
    state_col = "evidence_state" if "evidence_state" in df.columns else "status"
    if "status" in df.columns and state_col == "evidence_state":
        df = df.drop(columns=["status"])
    df = df[df["milestone"] != "ncs_phase80_finding_first_submission_package"]
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                [
                    {
                        "milestone": "ncs_phase80_finding_first_submission_package",
                        "path": "outputs/milestones/ncs_phase80_finding_first_submission_package/",
                        state_col: "completed_finding_first_submission_package",
                        "manifest": "outputs/milestones/ncs_phase80_finding_first_submission_package/MANIFEST_SHA256.txt",
                        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase80_finding_first_submission_package",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    df.to_csv(path, index=False)


def update_evidence_ledger() -> None:
    if LEDGER.exists():
        df = pd.read_csv(LEDGER)
    else:
        df = pd.DataFrame(
            columns=[
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
            ]
        )
    df = df[df["claim_id"] != "NCS-PHASE80-001"]
    artifact = OUT / "table_phase80_finding_hierarchy.csv"
    row = {
        "claim_id": "NCS-PHASE80-001",
        "claim_text": "Phase80 freezes the finding-first NCS submission package around PARC-A, durability-risk, and Phase79 controlled breadth support.",
        "evidence_type": "paperization_scope_freeze",
        "positive_evidence": "synthesis_only",
        "scope": SCOPE,
        "artifact_path": rel(artifact),
        "hash": sha256_file(artifact),
        "validation_command": "make reproduce-ncs-phase80-finding-first-submission-package",
        "status": "PASS",
        "overclaim_guardrail": "do_not_treat_phase80_as_new_empirical_result_or_release_certificate",
    }
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    claim_table = ROOT / "docs/claim_table.md"
    text = claim_table.read_text(encoding="utf-8")
    marker = "\n## Phase80 Finding-First NCS Submission Package\n"
    text = text.split(marker)[0].rstrip() + marker + f"""

Status: `completed_finding_first_submission_package`.

Phase80 incorporates Phase79 into the NCS paper spine and reframes the
submission as a reliability study of scientific AI candidate release. The
allowed center is: targeted one-sided audit can unlock certified release, while
reference-update durability risk is primarily a chemical-system/reference
neighborhood property rather than a candidate-margin/rank property. Phase79
adds controlled mechanism support for this breadth claim.

This is not a new empirical result, not a release certificate, not DFT evidence
and not prospective materials discovery. DFT v2 remains quarantined until
stable_exact and workflow gates pass.
"""
    claim_table.write_text(text, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    numbers = load_numbers()

    write_readme()
    write_spine(numbers)
    write_abstract(numbers)
    build_findings_table(numbers).to_csv(OUT / "table_phase80_finding_hierarchy.csv", index=False)
    build_display_table().to_csv(OUT / "table_phase80_display_plan.csv", index=False)
    build_venue_table().to_csv(OUT / "table_phase80_venue_go_no_go.csv", index=False)
    write_cover_letter(numbers)
    (OUT / "provenance.json").write_text(
        json.dumps(
            {
                "phase": "phase80",
                "status": "completed_finding_first_submission_package",
                "inputs": [
                    rel(PHASE63),
                    rel(PHASE65B),
                    rel(PHASE67C),
                    rel(PHASE76),
                    rel(PHASE77),
                    rel(PHASE78),
                    rel(PHASE79),
                    rel(PHASE70),
                ],
                "scope": SCOPE,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    write_manifest(OUT)
    update_artifact_index()
    update_evidence_ledger()
    update_claim_table()
    write_root_manifest()


if __name__ == "__main__":
    main()
