#!/usr/bin/env python3
"""Build Phase76 PARC lifecycle calculus artifacts.

This phase is a synthesis layer.  It does not create a new empirical claim.
It turns the completed positive, diagnostic and no-go results into a coherent
release-card lifecycle: release, refusal, active audit, expiry, recertification
and risk triage.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase76_parc_lifecycle_calculus"
PHASE63 = ROOT / "outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification"
PHASE65B = ROOT / "outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics"
PHASE69 = ROOT / "outputs/milestones/ncs_phase69_durability_budgeted_parc"
PHASE74 = ROOT / "outputs/milestones/ncs_phase74_risk_gated_recertification"
PHASE75 = ROOT / "outputs/milestones/ncs_phase75_active_versioned_recertification"
PHASE70 = ROOT / "outputs/milestones/ncs_phase70_dft_v2_checkpoint"

SCOPE = (
    "PARC_lifecycle_calculus;"
    "synthesis_of_completed_artifacts;"
    "not_new_empirical_claim;"
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


def write_supplement() -> None:
    tex = r"""\section{PARC lifecycle calculus}
\label{sec:parc-lifecycle-calculus}

PARC is a lifecycle rule for finite scientific candidate queues under
one-sided partial verification.  The object is not only a selected set.  The
object is a release card: a versioned statement of the candidate universe,
reference label version, one-sided support source, score, block construction,
release/refusal decision and recertification status.

\paragraph{Setup.}
Let \(P\) be a frozen finite candidate universe and let \(Y_p\in\{0,1\}\)
denote validity under a fixed reference version.  One-sided support is a
binary observation \(A_p\) satisfying
\[
  A_p=1 \Rightarrow Y_p=1 .
\]
For a calibration block \(b\), PARC removes only verified positives from the
calibration null superset and keeps all unverified candidates in the null
superset.  Candidate scores and block definitions are frozen before release.

\begin{theorem}[Least-favourable null-superset dominance]
If one-sided reliability holds, every false calibration candidate remains in
the calibration null superset.  Therefore the maximum score over the
calibration null superset is least-favourable for the false-candidate score in
the corresponding exchangeable test block.  The resulting block rank
\(p\)-value is super-uniform for false candidates, and any monotone
calibrating transform that yields an e-value remains valid for false
candidates.
\end{theorem}

\begin{proof}
One-sided reliability removes only candidates known to be valid.  Hence no
false candidate is removed from the calibration null superset.  The block
maximum over this superset is at least as large as the maximum over the
unobserved false-only subset.  Under the stated block-exchangeability
condition, ranking a false test score against this superset maximum is
conservative.  The e-value statement follows from the standard
super-uniform-to-e-value transform used by PARC.
\end{proof}

\begin{proposition}[Refusal lower bound]
For a requested budget \(K\), risk target \(\alpha\), and compatible release
set \(R\), PARC self-consistency requires
\[
  E_p \ge \frac{K}{\alpha |R|}
  \quad \text{for all } p\in R .
\]
If no compatible non-empty set satisfies this inequality, PARC returns
certified refusal.  This refusal is a statement about evidence insufficiency
for the frozen release card, not a claim that no valid candidates exist.
\end{proposition}

\begin{proposition}[Active audit gain]
Consider a calibration candidate \(q\) that is currently a high-scoring member
of the calibration null superset.  If auditing \(q\) returns one-sided support
\(A_q=1\), then \(q\) is removed from the null superset.  This can weakly reduce
the relevant calibration block maximum and can increase the e-values of
follow-up candidates whose scores are compared against that block.  Targeted
audit policies can therefore turn certified refusal into certified release
without treating unverified candidates as negatives.
\end{proposition}

\begin{proposition}[Versioned certificate accounting]
Let \(Y_p^{(0)}\) and \(Y_p^{(1)}\) denote validity under reference versions
\(t_0\) and \(t_1\).  For any release set \(R\),
\[
 \mathrm{FTR}_{1}(R)
 =
 \mathrm{FTR}_{0}(R)
 + \frac{|\{p\in R:Y_p^{(0)}=1,Y_p^{(1)}=0\}|}{|R|\vee 1}
 - \frac{|\{p\in R:Y_p^{(0)}=0,Y_p^{(1)}=1\}|}{|R|\vee 1}.
\]
Thus inherited current-reference burden is the old-reference burden plus
stable-to-unstable drift minus unstable-to-stable correction.
\end{proposition}

\begin{theorem}[Versioned recertification]
Fix a new reference version \(t_1\).  If candidate universe, score, blocks,
compatibility and release grid are frozen, and if \(t_1\)-version one-sided
support satisfies \(A_p^{(1)}=1\Rightarrow Y_p^{(1)}=1\), then rerunning PARC
at \(t_1\) restores an expected \(t_1\)-relative false-release guarantee
whenever the returned set is non-empty and self-consistent.  If no such set is
found, PARC returns recertified refusal.
\end{theorem}

\paragraph{Lifecycle interpretation.}
The same calculus supports several release-card states: certified release,
certified refusal, active-audit requirement, expiry after reference update,
recertified release, recertified refusal and risk-triage requirement.  The
states are mutually scoped to the recorded reference version and evidence
sources.  They should not be read as prospective materials discovery, DFT
validation or absolute physical truth.
"""
    (OUT / "supplement_parc_lifecycle_calculus.tex").write_text(tex, encoding="utf-8")


def build_schema() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "PARC release-card lifecycle schema",
        "type": "object",
        "required": [
            "release_card_id",
            "candidate_universe_hash",
            "reference_version",
            "score_source",
            "block_definition",
            "alpha",
            "requested_budget_K",
            "lifecycle_state",
            "evidence_scope",
            "guardrails",
        ],
        "properties": {
            "release_card_id": {"type": "string"},
            "candidate_universe_hash": {"type": "string"},
            "reference_version": {"type": "string"},
            "score_source": {"type": "string"},
            "block_definition": {"type": "string"},
            "alpha": {"type": "number", "minimum": 0, "maximum": 1},
            "requested_budget_K": {"type": "integer", "minimum": 0},
            "release_size": {"type": "integer", "minimum": 0},
            "lifecycle_state": {
                "type": "string",
                "enum": [
                    "certified_release",
                    "certified_refusal",
                    "expired_after_reference_update",
                    "recertified_release",
                    "recertified_refusal",
                    "risk_triage_required",
                    "active_audit_required",
                ],
            },
            "one_sided_support_source": {"type": "string"},
            "active_audit_policy": {"type": "string"},
            "durability_risk_model": {"type": "string"},
            "recertification_status": {"type": "string"},
            "evidence_scope": {"type": "string"},
            "guardrails": {"type": "array", "items": {"type": "string"}},
            "artifact_paths": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": True,
    }
    (OUT / "release_card_schema.json").write_text(json.dumps(schema, indent=2, sort_keys=True), encoding="utf-8")


def build_states() -> pd.DataFrame:
    rows = [
        {
            "state": "certified_release",
            "entry_condition": "non-empty compatible set satisfies PARC self-consistency",
            "exit_condition": "reference update, audit failure, or new release request",
            "allowed_claim": "version-scoped expected false-release control",
            "forbidden_claim": "absolute truth, prospective materials discovery, or guarantee under a future reference",
        },
        {
            "state": "certified_refusal",
            "entry_condition": "no compatible non-empty set satisfies self-consistency",
            "exit_condition": "additional one-sided support or changed reference version",
            "allowed_claim": "evidence insufficient for this frozen release card",
            "forbidden_claim": "no valid candidates exist",
        },
        {
            "state": "expired_after_reference_update",
            "entry_condition": "reference version changes after a prior certificate",
            "exit_condition": "recertification under the new reference",
            "allowed_claim": "old certificate is version-bound and must not be silently inherited",
            "forbidden_claim": "old alpha certificate automatically transports to new reference",
        },
        {
            "state": "recertified_release",
            "entry_condition": "PARC rerun under new reference returns non-empty self-consistent release",
            "exit_condition": "new reference update or evidence audit",
            "allowed_claim": "new-reference scoped release",
            "forbidden_claim": "prospective discovery or DFT validation",
        },
        {
            "state": "recertified_refusal",
            "entry_condition": "PARC rerun under new reference returns refusal",
            "exit_condition": "additional one-sided support or narrower release request",
            "allowed_claim": "new-reference evidence insufficiency",
            "forbidden_claim": "method failure or no valid candidates exist",
        },
        {
            "state": "risk_triage_required",
            "entry_condition": "reference drift risk model flags high-risk certificate inheritance",
            "exit_condition": "recertification, active audit, or manual review",
            "allowed_claim": "release-card risk triage",
            "forbidden_claim": "label-free deployment predictor or repaired alpha certificate",
        },
        {
            "state": "active_audit_required",
            "entry_condition": "current evidence mass is insufficient but candidate audit can add one-sided positives",
            "exit_condition": "targeted audit returns enough support or still refuses",
            "allowed_claim": "verification-budget design",
            "forbidden_claim": "unverified candidates are negatives",
        },
    ]
    df = pd.DataFrame(rows)
    df["evidence_scope"] = SCOPE
    return df


def build_ctc_replay() -> pd.DataFrame:
    primary = pd.read_csv(PHASE63 / "table_parc_a_primary_gate.csv")
    k100 = primary[primary["target_row"].eq("ctc_learned_strict_alpha010_K100")].iloc[0]
    mech = pd.read_csv(PHASE65B / "table_parc_a_mechanism_gate.csv").set_index("gate")
    rows = [
        {
            "domain": "CTC cell tracking",
            "step": 1,
            "lifecycle_state": "active_audit_required",
            "event": "initial scarce one-sided support is insufficient for release",
            "reference_version": "CTC official labels masked for audit emulation",
            "K": int(k100["K"]),
            "alpha": float(k100["alpha"]),
            "audit_policy": "none_or_matched_random",
            "audit_budget_fraction": 0.0,
            "release_size": 0,
            "nonempty_seeds": 0,
            "safe_seeds": 0,
            "observed_FTR": "",
            "artifact": rel(PHASE63 / "table_parc_a_primary_gate.csv"),
            "interpretation": "without targeted one-sided support, release remains unavailable",
            "evidence_scope": SCOPE,
        },
        {
            "domain": "CTC cell tracking",
            "step": 2,
            "lifecycle_state": "certified_release",
            "event": "targeted audit acquires verified positives and restores release",
            "reference_version": "CTC official labels masked for audit emulation",
            "K": int(k100["K"]),
            "alpha": float(k100["alpha"]),
            "audit_policy": k100["audit_policy"],
            "audit_budget_fraction": float(k100["audit_budget_fraction"]),
            "release_size": int(k100["total_released"]),
            "nonempty_seeds": int(k100["nonempty_seeds"]),
            "safe_seeds": int(k100["safe_seeds"]),
            "observed_FTR": float(k100["mean_FTR"]),
            "artifact": rel(PHASE63 / "table_parc_a_primary_gate.csv"),
            "interpretation": "PARC-A turns verification budget into a strict release card",
            "evidence_scope": SCOPE,
        },
        {
            "domain": "CTC cell tracking",
            "step": 3,
            "lifecycle_state": "certified_release",
            "event": "mechanism: high-score positives remove limiting null-superset block maxima",
            "reference_version": "CTC official labels masked for audit emulation",
            "K": int(k100["K"]),
            "alpha": float(k100["alpha"]),
            "audit_policy": "score_targeted_0p2pct",
            "audit_budget_fraction": 0.002,
            "release_size": int(k100["K"] * k100["safe_seeds"]),
            "nonempty_seeds": int(mech.loc["score_0p2pct_safe_release_20of20", "value"]),
            "safe_seeds": int(mech.loc["score_0p2pct_safe_release_20of20", "value"]),
            "observed_FTR": 0.0,
            "artifact": rel(PHASE65B / "table_parc_a_mechanism_gate.csv"),
            "interpretation": "active audit gain explains why targeted support is not a generic threshold trick",
            "evidence_scope": SCOPE,
        },
    ]
    return pd.DataFrame(rows)


def build_materials_replay() -> pd.DataFrame:
    triage = pd.read_csv(PHASE69 / "table_risk_triage_frontier.csv")
    triage_row = triage[
        triage["risk_model"].eq("system_margin_distribution")
        & triage["K"].eq(300)
        & triage["retain_fraction"].eq(0.4)
    ].iloc[0]
    budget = pd.read_csv(PHASE69 / "table_durability_budgeted_release_frontier.csv")
    budget_row = budget[
        budget["risk_model"].eq("system_margin_distribution")
        & budget["K"].eq(300)
        & budget["alpha0"].eq(0.01)
        & budget["retain_fraction"].eq(0.4)
    ].iloc[0]
    phase74 = pd.read_csv(PHASE74 / "table_risk_gated_primary_row.csv").iloc[0]
    phase75 = pd.read_csv(PHASE75 / "table_active_recertification_policy_comparison.csv")
    best75 = phase75.sort_values(
        ["nonempty_seeds", "safe_seeds", "mean_release_size", "mean_FTR_t1_if_nonempty"],
        ascending=[False, False, False, True],
    ).iloc[0]
    dft = pd.read_csv(PHASE70 / "table_dft_v2_execution_checkpoint_summary.csv").iloc[0]
    rows = [
        {
            "domain": "WBM materials",
            "step": 1,
            "lifecycle_state": "certified_release",
            "event": "t0 public-label PARC release exists under original reference",
            "reference_version": "WBM/Matbench t0",
            "K": 300,
            "alpha": 0.10,
            "release_size": "pre-existing t0 release rows",
            "observed_FTR": "t0-scoped",
            "artifact": rel(PHASE69 / "table_durability_budgeted_release_frontier.csv"),
            "interpretation": "t0 certificate is version-scoped and does not automatically transport",
            "evidence_scope": SCOPE,
        },
        {
            "domain": "WBM materials",
            "step": 2,
            "lifecycle_state": "expired_after_reference_update",
            "event": "current-MP t1 reference changes the validity labels",
            "reference_version": "Materials Project current t1",
            "K": 300,
            "alpha": 0.10,
            "release_size": int(budget_row["release_size_candidate_level"]),
            "observed_FTR": float(budget_row["observed_FTR_t1"]),
            "artifact": rel(PHASE69 / "table_durability_budgeted_release_frontier.csv"),
            "interpretation": "version-shift accounting is required before inheriting a release",
            "evidence_scope": SCOPE,
        },
        {
            "domain": "WBM materials",
            "step": 3,
            "lifecycle_state": "risk_triage_required",
            "event": "t0 public-label release-card metadata predicts drift risk",
            "reference_version": "Materials Project current t1 audit",
            "K": int(triage_row["K"]),
            "alpha": 0.10,
            "release_size": int(triage_row["n_retained_low_risk"]),
            "observed_FTR": float(triage_row["retained_flip_rate"]),
            "artifact": rel(PHASE69 / "table_risk_triage_frontier.csv"),
            "interpretation": "triage reduces retained drift burden but is not a repaired alpha certificate",
            "evidence_scope": SCOPE,
        },
        {
            "domain": "WBM materials",
            "step": 4,
            "lifecycle_state": "recertified_refusal",
            "event": "risk-gated filtered-universe recertification still refuses",
            "reference_version": "Materials Project current t1",
            "K": int(phase74["K_original"]),
            "alpha": 0.10,
            "release_size": int(phase74["mean_release_size"]),
            "observed_FTR": "",
            "artifact": rel(PHASE74 / "table_risk_gated_primary_row.csv"),
            "interpretation": "risk-gating upstream does not recover a current-MP release certificate",
            "evidence_scope": SCOPE,
        },
        {
            "domain": "WBM materials",
            "step": 5,
            "lifecycle_state": "recertified_refusal",
            "event": "active t1 recertification also fails GO-medium/GO-strong gate",
            "reference_version": "Materials Project current t1",
            "K": int(best75["K"]),
            "alpha": float(best75["alpha"]),
            "release_size": float(best75["mean_release_size"]),
            "observed_FTR": float(best75["mean_FTR_t1_if_nonempty"]),
            "artifact": rel(PHASE75 / "table_active_recertification_policy_comparison.csv"),
            "interpretation": "targeted calibration-side t1 support does not repair the materials certificate",
            "evidence_scope": SCOPE,
        },
        {
            "domain": "WBM materials",
            "step": 6,
            "lifecycle_state": "active_audit_required",
            "event": "independent DFT v2 remains a checkpoint, not evidence",
            "reference_version": "blinded DFT v2 manifest",
            "K": "",
            "alpha": "",
            "release_size": int(dft["completed_jobs"]),
            "observed_FTR": "",
            "artifact": rel(PHASE70 / "table_dft_v2_execution_checkpoint_summary.csv"),
            "interpretation": "do not use DFT v2 until stable_exact and workflow gates pass",
            "evidence_scope": SCOPE,
        },
    ]
    return pd.DataFrame(rows)


def build_baseline_capabilities() -> pd.DataFrame:
    rows = [
        {
            "method": "PARC lifecycle",
            "one_sided_validity": True,
            "can_release": True,
            "can_refuse": True,
            "can_acquire_audit": True,
            "can_expire_certificate": True,
            "can_recertify": True,
            "has_release_card": True,
            "handles_reference_drift": True,
            "capability_note": "release/refusal/active-audit/versioned-recertification lifecycle",
        },
        {
            "method": "PARC core",
            "one_sided_validity": True,
            "can_release": True,
            "can_refuse": True,
            "can_acquire_audit": False,
            "can_expire_certificate": False,
            "can_recertify": False,
            "has_release_card": True,
            "handles_reference_drift": False,
            "capability_note": "single-version release/refusal certificate",
        },
        {
            "method": "PARC-A",
            "one_sided_validity": True,
            "can_release": True,
            "can_refuse": True,
            "can_acquire_audit": True,
            "can_expire_certificate": False,
            "can_recertify": False,
            "has_release_card": True,
            "handles_reference_drift": False,
            "capability_note": "verification-budgeted release acquisition",
        },
        {
            "method": "PARC-D",
            "one_sided_validity": True,
            "can_release": False,
            "can_refuse": False,
            "can_acquire_audit": False,
            "can_expire_certificate": True,
            "can_recertify": False,
            "has_release_card": True,
            "handles_reference_drift": True,
            "capability_note": "durability-risk triage, not full alpha certificate",
        },
        {
            "method": "e-BH selection",
            "one_sided_validity": False,
            "can_release": True,
            "can_refuse": False,
            "can_acquire_audit": False,
            "can_expire_certificate": False,
            "can_recertify": False,
            "has_release_card": False,
            "handles_reference_drift": False,
            "capability_note": "selection procedure without release-card lifecycle",
        },
        {
            "method": "raw top-K",
            "one_sided_validity": False,
            "can_release": True,
            "can_refuse": False,
            "can_acquire_audit": False,
            "can_expire_certificate": False,
            "can_recertify": False,
            "has_release_card": False,
            "handles_reference_drift": False,
            "capability_note": "ranking baseline only",
        },
        {
            "method": "score threshold",
            "one_sided_validity": False,
            "can_release": True,
            "can_refuse": True,
            "can_acquire_audit": False,
            "can_expire_certificate": False,
            "can_recertify": False,
            "has_release_card": False,
            "handles_reference_drift": False,
            "capability_note": "thresholding without null-superset evidence construction",
        },
        {
            "method": "split conformal threshold",
            "one_sided_validity": False,
            "can_release": True,
            "can_refuse": True,
            "can_acquire_audit": False,
            "can_expire_certificate": False,
            "can_recertify": False,
            "has_release_card": False,
            "handles_reference_drift": False,
            "capability_note": "different target object, no lifecycle recertification",
        },
        {
            "method": "post-filter e-value",
            "one_sided_validity": True,
            "can_release": True,
            "can_refuse": False,
            "can_acquire_audit": False,
            "can_expire_certificate": False,
            "can_recertify": False,
            "has_release_card": False,
            "handles_reference_drift": False,
            "capability_note": "valid scores alone without SCS/lifecycle",
        },
        {
            "method": "PU classifier-release",
            "one_sided_validity": False,
            "can_release": True,
            "can_refuse": False,
            "can_acquire_audit": False,
            "can_expire_certificate": False,
            "can_recertify": False,
            "has_release_card": False,
            "handles_reference_drift": False,
            "capability_note": "classifier baseline, not release-card calculus",
        },
    ]
    df = pd.DataFrame(rows)
    df["evidence_scope"] = SCOPE
    return df


def write_readme(status: str) -> None:
    text = f"""# Phase76 PARC Lifecycle Calculus

Status: `{status}`.

Phase76 is a synthesis layer. It consolidates the PARC theorem pieces,
release-card lifecycle states, CTC active-verification replay, materials
reference-update replay, and lifecycle capability baselines.

It does not add new empirical evidence. It explicitly preserves the Phase74
and Phase75 no-go outcomes: materials current-MP recertification remains a
refusal/risk-triage story, not a recovered alpha certificate.

Guardrails:

- no DFT evidence;
- no prospective materials discovery;
- no current-MP alpha certificate from materials recertification;
- no label-free durability predictor claim;
- e-BH is compared on lifecycle capability, not as a strawman FTR baseline.
"""
    (OUT / "README_evidence_scope.md").write_text(text, encoding="utf-8")


def update_artifact_index(status: str) -> None:
    path = ROOT / "outputs/artifact_index.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["milestone"] != "ncs_phase76_parc_lifecycle_calculus"]
    rows.append(
        {
            "milestone": "ncs_phase76_parc_lifecycle_calculus",
            "path": "outputs/milestones/ncs_phase76_parc_lifecycle_calculus/",
            "evidence_state": status,
            "manifest": "outputs/milestones/ncs_phase76_parc_lifecycle_calculus/MANIFEST_SHA256.txt",
            "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase76_parc_lifecycle_calculus",
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
    marker = "## Phase76 PARC Lifecycle Calculus"
    if marker in text:
        text = text.split(marker)[0].rstrip() + "\n"
    addition = f"""

## Phase76 PARC Lifecycle Calculus

Status: `{status}`.

Phase76 consolidates PARC as a release-card lifecycle calculus rather than a
single selection rule. It supplies supplement-ready theory statements, a JSON
release-card schema, lifecycle state table, CTC active-audit replay, materials
reference-update replay, and lifecycle capability baselines. The allowed claim
is conceptual and infrastructural: PARC supports release, refusal, audit
acquisition, expiry and recertification states. It does not convert Phase74 or
Phase75 materials no-go outcomes into a current-MP alpha certificate.
"""
    path.write_text(text.rstrip() + addition, encoding="utf-8")


def update_evidence_ledger(status: str) -> None:
    path = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
    rows = list(csv.DictReader(path.open()))
    rows = [row for row in rows if row["claim_id"] != "PARC-LIFECYCLE-001"]
    artifact = OUT / "table_lifecycle_baseline_capabilities.csv"
    rows.append(
        {
            "claim_id": "PARC-LIFECYCLE-001",
            "claim_text": "PARC is represented as a release-card lifecycle calculus covering release, refusal, active audit, expiry, recertification and risk triage.",
            "evidence_type": "lifecycle_calculus_synthesis",
            "positive_evidence": "yes",
            "scope": status,
            "artifact_path": rel(artifact),
            "hash": sha256_file(artifact),
            "validation_command": "make reproduce-ncs-phase76-parc-lifecycle-calculus",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_new_empirical_evidence_DFT_or_prospective_discovery",
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
    status = "completed_lifecycle_calculus_synthesis"
    write_supplement()
    build_schema()
    states = build_states()
    ctc = build_ctc_replay()
    materials = build_materials_replay()
    baseline = build_baseline_capabilities()
    figure = pd.concat(
        [
            ctc.assign(panel="ctc_active_audit_lifecycle"),
            materials.assign(panel="materials_reference_update_lifecycle"),
            states.assign(panel="release_card_states"),
            baseline.assign(panel="baseline_lifecycle_capabilities"),
        ],
        ignore_index=True,
        sort=False,
    )
    states.to_csv(OUT / "table_release_card_states.csv", index=False)
    ctc.to_csv(OUT / "table_lifecycle_replay_ctc.csv", index=False)
    materials.to_csv(OUT / "table_lifecycle_replay_materials.csv", index=False)
    figure.to_csv(OUT / "figure_lifecycle_replay_inputs.csv", index=False)
    baseline.to_csv(OUT / "table_lifecycle_baseline_capabilities.csv", index=False)
    write_readme(status)
    provenance = {
        "status": status,
        "phase": "phase76",
        "source_artifacts": {
            "phase63_primary_gate": rel(PHASE63 / "table_parc_a_primary_gate.csv"),
            "phase65b_mechanism_gate": rel(PHASE65B / "table_parc_a_mechanism_gate.csv"),
            "phase69_triage": rel(PHASE69 / "table_risk_triage_frontier.csv"),
            "phase74_primary": rel(PHASE74 / "table_risk_gated_primary_row.csv"),
            "phase75_policy_comparison": rel(PHASE75 / "table_active_recertification_policy_comparison.csv"),
            "phase70_dft_checkpoint": rel(PHASE70 / "table_dft_v2_execution_checkpoint_summary.csv"),
        },
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
