#!/usr/bin/env python3
"""Build NCS Phase58 reproducibility hardening artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening"


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


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def artifact_hash(path: str) -> str:
    return sha256_file(ROOT / path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    docs = {
        "REPRODUCE_PHASE49.md": """# Reproduce Phase49: Current-MP t0/t1 Snapshot Acquisition

Run:

```bash
make reproduce-materials-t0-t1
```

Primary outputs:

- `outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t0_t1_label_join.csv`
- `outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t1_hull_ftr_delta.csv`
- `outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t0_t1_gate_assessment.csv`

Claim boundary: completed current-MP hull-shift utility diagnostic; not a
strict temporal alpha certificate and not prospective materials discovery.
""",
        "REPRODUCE_T1_HULL_AUDIT.md": """# Reproduce t1 Hull-Shift Audit Tables

Run:

```bash
make reproduce-materials-figures
make reproduce-materials-baseline-frontier
```

This regenerates the paper-facing Phase49/50 tables, including:

- `table_t1_ftr_by_k_and_policy.csv`
- `table_t1_stable_to_unstable_drift.csv`
- `figure_t1_hull_shift_inputs.csv`
- `table_t1_bootstrap_ci.csv`
- `table_t1_randomization_tests.csv`
- `table_version_shift_decomposition.csv`
- `table_t1_mlip_baseline_frontier.csv`

The audit evaluates frozen t0-selected K=300/500 queues under a current-MP
hull. No t1 label is used for release selection.
""",
        "REPRODUCE_MLIP_AUDIT.md": """# Reproduce Candidate-Level MLIP Audits

Run:

```bash
make reproduce-materials-mlip-audit
```

This target rebuilds two scoped materials audit layers:

- Phase51 candidate-level explanation with ALIGNN-FF, CGCNN and MEGNet
  model-zoo scores.
- Phase53 candidate-level CHGNet/MACE score-support audit when the local
  private WBM raw-structure cache is available.
- Phase60 PARC-V support-gate feasibility audit.

The Phase53 CHGNet/MACE columns are raw energy-per-atom score proxies, not
reference-hull e_above_hull values. They support a queue-level release-vs-tail
score contrast and must not be cited as DFT evidence, strict t1 alpha control,
or prospective materials discovery.

Run:

```bash
make reproduce-ncs-phase60-parc-v-version-aware-release
```

to regenerate the PARC-V support-gate feasibility audit. Phase60 is a no-go
for a headline version-aware release claim: CHGNet/MACE support-gating is
non-empty but does not materially lower current-MP t1 FTR and is not a full SCS
rerun.
""",
        "DATA_PROVENANCE_MATERIALS.md": """# Materials Data Provenance

Candidate universe: frozen WBM/Matbench Discovery prototype queue.

t0 labels: WBM/Matbench public DFT stability labels used for the original
release certificate.

t1 labels: Materials Project current API GGA/GGA+U ComputedEntry hull audit
used only after release-set freezing.

Scores: frozen ALIGNN-FF release scores plus local public-source identifiers for
CGCNN and MEGNet model-zoo predictions. Phase53 adds CHGNet/MACE score proxies
computed from the local private WBM raw-structure cache. Public artifacts record
candidate IDs, structure hashes and scores, but not raw structures.

All claim-bearing tables carry an overclaim guardrail distinguishing utility
diagnostics from strict alpha certificates.
""",
    }
    for filename, text in docs.items():
        (OUT / filename).write_text(text, encoding="utf-8")

    ledger_rows = [
        {
            "claim_id": "M-T1-001",
            "claim_text": "Frozen PARC K=300/500 queues have lower current-MP t1 FTR than raw top-K.",
            "evidence_type": "current_MP_hull_shift_utility_audit",
            "positive_evidence": "yes",
            "scope": "not_strict_alpha_certificate",
            "artifact_path": "outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t1_ftr_by_k_and_policy.csv",
            "validation_command": "make reproduce-materials-t0-t1 && make reproduce-materials-figures",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_temporal_alpha_control_or_prospective_discovery",
        },
        {
            "claim_id": "M-T1-002",
            "claim_text": "Stable-to-unstable drift is not concentrated in the PARC release relative to raw top-K.",
            "evidence_type": "current_MP_hull_shift_utility_audit",
            "positive_evidence": "yes",
            "scope": "version_shift_drift_diagnostic",
            "artifact_path": "outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t1_stable_to_unstable_drift.csv",
            "validation_command": "make reproduce-materials-t0-t1 && make reproduce-materials-figures",
            "status": "PASS",
            "overclaim_guardrail": "drift_diagnostic_not_t1_certificate",
        },
        {
            "claim_id": "M-T1-003",
            "claim_text": "The current-MP t1 audit is not a strict alpha=0.10 temporal certificate.",
            "evidence_type": "claim_boundary",
            "positive_evidence": "no",
            "scope": "failed_strict_t1_alpha_gate",
            "artifact_path": "outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t0_t1_gate_assessment.csv",
            "validation_command": "make reproduce-materials-t0-t1",
            "status": "PASS",
            "overclaim_guardrail": "explicitly_forbid_t1_alpha_control_claim",
        },
        {
            "claim_id": "M-CAND-001",
            "claim_text": "Candidate-level t1 false releases are decomposed into boundary, drift, chemistry, and model-disagreement classes.",
            "evidence_type": "candidate_level_failure_explanation",
            "positive_evidence": "yes",
            "scope": "explanation_diagnostic_no_MLIP_consensus_claim",
            "artifact_path": "outputs/milestones/ncs_phase51_materials_t1_candidate_explanation/table_t1_false_release_decomposition.csv",
            "validation_command": "make reproduce-materials-mlip-audit",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_CHGNet_MACE_consensus_validation",
        },
        {
            "claim_id": "M-STAT-001",
            "claim_text": "Chemical-system block bootstrap intervals quantify t1 utility and drift uncertainty.",
            "evidence_type": "block_bootstrap_uncertainty",
            "positive_evidence": "yes",
            "scope": "paired_audit_uncertainty",
            "artifact_path": "outputs/milestones/ncs_phase52_materials_t1_uncertainty/table_t1_bootstrap_ci.csv",
            "validation_command": "make reproduce-materials-figures",
            "status": "PASS",
            "overclaim_guardrail": "confidence_intervals_are_not_theorem_guarantees",
        },
        {
            "claim_id": "M-STAT-002",
            "claim_text": "Rank-bin randomization tests compare PARC to raw top-K, matched raw top-R, and stratified raw subsets.",
            "evidence_type": "randomization_test",
            "positive_evidence": "yes",
            "scope": "empirical_audit_comparison",
            "artifact_path": "outputs/milestones/ncs_phase52_materials_t1_uncertainty/table_t1_randomization_tests.csv",
            "validation_command": "make reproduce-materials-figures",
            "status": "PASS",
            "overclaim_guardrail": "does_not_claim_matched_volume_ranking_improvement",
        },
        {
            "claim_id": "M-MLIP-001",
            "claim_text": "Phase53 CHGNet/MACE score-support proxies favor PARC release over raw-only extra-tail at K=300/500.",
            "evidence_type": "candidate_level_CHGNet_MACE_score_audit",
            "positive_evidence": "yes",
            "scope": "score_support_proxy_not_reference_hull_or_DFT_evidence",
            "artifact_path": "outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit/table_chgnet_mace_support_by_policy.csv",
            "validation_command": "make reproduce-ncs-phase53-chgnet-mace-candidate-audit",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_reference_hull_ehull_DFT_or_prospective_discovery",
        },
        {
            "claim_id": "M-MLIP-002",
            "claim_text": "Phase53 t1 false-case explanation is only partial under CHGNet/MACE score proxies.",
            "evidence_type": "candidate_level_CHGNet_MACE_boundary_diagnostic",
            "positive_evidence": "no",
            "scope": "partial_false_case_mechanism_not_completed_stability_validation",
            "artifact_path": "outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit/table_phase53_go_no_go.csv",
            "validation_command": "make reproduce-ncs-phase53-chgnet-mace-candidate-audit",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_CHGNet_MACE_explains_all_current_MP_false_releases",
        },
        {
            "claim_id": "M-VSHIFT-001",
            "claim_text": "The current-MP t1 burden decomposes into t0 FTR plus stable-to-current-not-stable drift minus not-stable-to-current-stable drift.",
            "evidence_type": "version_shift_accounting_identity",
            "positive_evidence": "yes",
            "scope": "deterministic_accounting_not_new_alpha_certificate",
            "artifact_path": "outputs/milestones/ncs_phase56_version_shift_accounting/table_version_shift_decomposition.csv",
            "validation_command": "make reproduce-ncs-phase56-version-shift-accounting",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_t1_alpha_control_from_accounting_identity",
        },
        {
            "claim_id": "M-BASE-T1-001",
            "claim_text": "The t1/CHGNet-MACE baseline frontier preserves the matched-volume boundary: PARC is certified stopping/refusal, not a matched-volume ranking improvement claim.",
            "evidence_type": "t1_MLIP_empirical_baseline_frontier",
            "positive_evidence": "yes",
            "scope": "capability_comparison_not_equal_target_object",
            "artifact_path": "outputs/milestones/ncs_phase57_t1_mlip_baseline_frontier/table_t1_mlip_baseline_frontier.csv",
            "validation_command": "make reproduce-ncs-phase57-t1-mlip-baseline-frontier",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_PARC_matched_volume_ranking_improvement",
        },
        {
            "claim_id": "M-PARCV-001",
            "claim_text": "A simple CHGNet/MACE support-gated PARC-V subset is non-empty but does not create a headline-capable current-MP t1 release result.",
            "evidence_type": "PARC_V_support_gate_feasibility_audit",
            "positive_evidence": "no",
            "scope": "completed_no_go_for_headline_not_full_SCS_rerun",
            "artifact_path": "outputs/milestones/ncs_phase60_parc_v_version_aware_release/table_parc_v_gate_audit.csv",
            "validation_command": "make reproduce-ncs-phase60-parc-v-version-aware-release",
            "status": "PASS",
            "overclaim_guardrail": "do_not_claim_new_PARC_V_theorem_t1_alpha_control_DFT_or_prospective_discovery",
        },
    ]
    for row in ledger_rows:
        row["hash"] = artifact_hash(row["artifact_path"])

    fieldnames = [
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
    write_csv(OUT / "EVIDENCE_SCOPE_LEDGER.csv", ledger_rows, fieldnames)

    closeout = """# NCS Phase58 Reproducibility Hardening

Status: `completed_evidence_ledger_and_reproduction_cards`

This milestone adds reproduction cards and an evidence-scope ledger for the
materials version-shift audit. The ledger is intentionally claim-boundary first:
every positive row maps to a source artifact and every boundary row has an
overclaim guardrail.
"""
    (OUT / "NCS_PHASE58_REPRODUCIBILITY_HARDENING.md").write_text(closeout, encoding="utf-8")
    provenance = {
        "milestone": "ncs_phase58_reproducibility_hardening",
        "ledger": rel(OUT / "EVIDENCE_SCOPE_LEDGER.csv"),
        "status": "completed_evidence_ledger_and_reproduction_cards",
    }
    (OUT / "provenance.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_manifest(OUT)
    write_root_manifest()
    print(f"wrote {rel(OUT)}")


if __name__ == "__main__":
    main()
