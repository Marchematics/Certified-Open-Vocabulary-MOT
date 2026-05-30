#!/usr/bin/env python3
"""Build Phase81 CTC external blind one-sided audit mini-study packet.

Phase78 integrates the existing human-confirmed CTC audit.  Phase81 freezes the
next reviewer-facing step: a blinded two-auditor packet with independent labels
pending.  This script intentionally does not create new labels or positive
evidence.  It creates the packet, rubric, arm registry, adjudication template,
and claim guardrails needed to turn PARC-A from masked-label emulation into a
real verification-workflow mini-study once labels are returned.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "outputs/milestones/ctc_strict_human_audit/ctc_strict_audit_human_confirmed_labels.csv"
OUT = ROOT / "outputs/milestones/ncs_phase81_ctc_external_blind_audit_mini_study"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "ctc_external_blind_audit_packet_frozen_pending_labels;"
    "two_auditor_blind_packet;"
    "supports_future_PARC_A_workflow_validation_only_after_returned_labels;"
    "not_completed_positive_evidence;"
    "not_new_CTC_ground_truth;"
    "not_materials_evidence;"
    "not_DFT_evidence"
)

RNG_SEED = 8101
TOTAL_PACKET_SIZE = 600

AUDITOR_TEMPLATE_COLUMNS = [
    "audit_item_id",
    "ctc_dataset",
    "sequence_id",
    "frame_start",
    "frame_end",
    "source_image_path",
    "source_frame_index",
    "source_bbox_x",
    "source_bbox_y",
    "source_bbox_w",
    "source_bbox_h",
    "target_image_path",
    "target_frame_index",
    "target_bbox_x",
    "target_bbox_y",
    "target_bbox_w",
    "target_bbox_h",
    "auditor_label",
    "auditor_confidence",
    "auditor_notes",
]

FORBIDDEN_BLIND_COLUMNS = {
    "intended_arm",
    "source_audit_id",
    "queue_membership",
    "queue_calibration",
    "queue_simulated_strict_release",
    "queue_raw_topK_reference",
    "simulated_release_hits",
    "simulated_release_budgets",
    "simulated_release_seeds",
    "candidate_rank",
    "score",
    "path_id",
    "human_label",
    "human_verified_positive_for_calibration",
    "human_reason",
    "human_confidence",
    "human_review_status",
    "human_confirmation_note",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def stable_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sample_rows(
    frame: pd.DataFrame,
    mask: pd.Series,
    n: int,
    arm: str,
    rng: np.random.Generator,
    already_selected: set[str],
) -> pd.DataFrame:
    pool = frame[mask & ~frame["audit_id"].astype(str).isin(already_selected)].copy()
    if len(pool) < n:
        n = len(pool)
    if n <= 0:
        return pool.iloc[0:0].copy()
    chosen = pool.sample(n=n, random_state=int(rng.integers(0, 2**31 - 1))).copy()
    chosen["intended_arm"] = arm
    already_selected.update(chosen["audit_id"].astype(str).tolist())
    return chosen


def load_source() -> pd.DataFrame:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    labels = pd.read_csv(SOURCE)
    required = {
        "audit_id",
        "path_id",
        "queue_calibration",
        "queue_simulated_strict_release",
        "queue_raw_topK_reference",
        "ctc_dataset",
        "sequence_id",
        "frame_start",
        "frame_end",
        "source_image_path",
        "source_frame_index",
        "source_bbox_x",
        "source_bbox_y",
        "source_bbox_w",
        "source_bbox_h",
        "target_image_path",
        "target_frame_index",
        "target_bbox_x",
        "target_bbox_y",
        "target_bbox_w",
        "target_bbox_h",
        "human_label",
    }
    missing = required.difference(labels.columns)
    if missing:
        raise ValueError(f"missing required source columns: {sorted(missing)}")
    return labels


def build_packet(labels: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(RNG_SEED)
    selected_ids: set[str] = set()
    arms = [
        (
            "parc_release_core",
            labels["queue_simulated_strict_release"].astype(bool)
            & ~labels["queue_raw_topK_reference"].astype(bool),
            250,
        ),
        (
            "raw_topK_reference_overlap",
            labels["queue_raw_topK_reference"].astype(bool),
            100,
        ),
        (
            "calibration_one_sided_support_pool",
            labels["queue_calibration"].astype(bool) & labels["human_label"].eq("same_cell_link"),
            150,
        ),
        (
            "hard_negative_or_uncertain_control",
            labels["human_label"].isin(["not_same_cell_link", "uncertain"]),
            45,
        ),
        (
            "random_blind_control_from_available_reviewed_rows",
            pd.Series(True, index=labels.index),
            55,
        ),
    ]
    parts = [sample_rows(labels, mask, n, arm, rng, selected_ids) for arm, mask, n in arms]
    packet = pd.concat(parts, ignore_index=True)
    if len(packet) != TOTAL_PACKET_SIZE:
        raise RuntimeError(f"expected {TOTAL_PACKET_SIZE} selected rows, got {len(packet)}")
    packet["_blind_sort_key"] = packet["audit_id"].astype(str).map(stable_digest)
    packet = packet.sort_values("_blind_sort_key").reset_index(drop=True)
    packet["audit_item_id"] = [f"CTC-PHASE81-{idx:04d}" for idx in range(1, len(packet) + 1)]
    packet["packet_randomization_seed"] = RNG_SEED
    packet["evidence_scope"] = SCOPE
    return packet


def write_packet_files(packet: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    registry_cols = [
        "audit_item_id",
        "intended_arm",
        "audit_id",
        "path_id",
        "ctc_dataset",
        "sequence_id",
        "frame_start",
        "frame_end",
        "source_image_path",
        "source_frame_index",
        "source_bbox_x",
        "source_bbox_y",
        "source_bbox_w",
        "source_bbox_h",
        "target_image_path",
        "target_frame_index",
        "target_bbox_x",
        "target_bbox_y",
        "target_bbox_w",
        "target_bbox_h",
        "packet_randomization_seed",
        "evidence_scope",
    ]
    packet[registry_cols].rename(columns={"audit_id": "source_audit_id"}).to_csv(
        OUT / "table_ctc_external_blind_audit_packet_registry.csv", index=False
    )

    template = packet[AUDITOR_TEMPLATE_COLUMNS[:-3]].copy()
    for col in ["auditor_label", "auditor_confidence", "auditor_notes"]:
        template[col] = ""
    template.to_csv(OUT / "external_blind_auditor_A_template.csv", index=False)
    template.to_csv(OUT / "external_blind_auditor_B_template.csv", index=False)

    adjudication = pd.DataFrame(
        {
            "audit_item_id": packet["audit_item_id"],
            "auditor_A_label": "",
            "auditor_A_confidence": "",
            "auditor_B_label": "",
            "auditor_B_confidence": "",
            "agreement_status": "",
            "adjudicated_label": "",
            "adjudication_reason": "",
            "adjudicator_initials": "",
        }
    )
    adjudication.to_csv(OUT / "external_blind_adjudication_template.csv", index=False)

    schema = {
        "allowed_labels": ["same_cell_supported", "unsupported", "uncertain"],
        "one_sided_positive_label": "same_cell_supported",
        "forbidden_negative_use": "unsupported and uncertain labels are audit outcomes only; PARC calibration may use only same_cell_supported as verified positives",
        "required_return_columns": [
            "audit_item_id",
            "auditor_label",
            "auditor_confidence",
            "auditor_notes",
        ],
        "arm_blinding": "Auditor templates exclude arm, score, rank, previous human label, PARC status and official GT fields.",
        "pending_status": "No Phase81 label outcome is claimed until returned templates are ingested and adjudicated.",
    }
    (OUT / "label_ingest_schema.json").write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")


def write_summaries(packet: pd.DataFrame, labels: pd.DataFrame) -> None:
    arm_summary = (
        packet.groupby("intended_arm", dropna=False)
        .agg(
            selected_rows=("audit_item_id", "count"),
            datasets=("ctc_dataset", lambda s: ",".join(sorted(map(str, s.dropna().unique())))),
            unique_sequences=("sequence_id", "nunique"),
        )
        .reset_index()
    )
    arm_summary["blind_labels_returned"] = "no"
    arm_summary["claim_status"] = "packet_frozen_pending_independent_labels"
    arm_summary["evidence_scope"] = SCOPE
    arm_summary.to_csv(OUT / "table_ctc_external_blind_audit_arm_plan.csv", index=False)

    availability = pd.DataFrame(
        [
            {
                "desired_arm": "PARC release",
                "available_in_phase81_packet": "yes",
                "selected_rows": int(packet["intended_arm"].eq("parc_release_core").sum()),
                "source": "existing CTC strict human-audit reviewed rows",
                "blocker_or_note": "",
            },
            {
                "desired_arm": "raw-only top-K",
                "available_in_phase81_packet": "no",
                "selected_rows": 0,
                "source": "not available in current public Phase78 source package",
                "blocker_or_note": "All tracked raw_topK_reference rows overlap the simulated strict-release queue; a true raw-only arm requires regenerating or restoring the full candidate universe before external labeling.",
            },
            {
                "desired_arm": "raw top-K reference overlap",
                "available_in_phase81_packet": "yes_as_overlap_control_not_raw_only",
                "selected_rows": int(packet["intended_arm"].eq("raw_topK_reference_overlap").sum()),
                "source": "existing CTC strict human-audit reviewed rows",
                "blocker_or_note": "Use only as overlap/reference control, not as the requested raw-only comparator.",
            },
            {
                "desired_arm": "boundary/hard negative control",
                "available_in_phase81_packet": "yes_limited",
                "selected_rows": int(packet["intended_arm"].eq("hard_negative_or_uncertain_control").sum()),
                "source": "existing reviewed not-same/uncertain rows",
                "blocker_or_note": "Limited to 45 available not-same rows in the tracked publication package.",
            },
            {
                "desired_arm": "random control",
                "available_in_phase81_packet": "yes_within_available_reviewed_rows",
                "selected_rows": int(packet["intended_arm"].eq("random_blind_control_from_available_reviewed_rows").sum()),
                "source": "random draw from available reviewed rows after other arms",
                "blocker_or_note": "This is not a random draw from the full candidate universe unless the full universe is restored.",
            },
        ]
    )
    availability["evidence_scope"] = SCOPE
    availability.to_csv(OUT / "table_ctc_external_blind_audit_arm_availability.csv", index=False)

    template = pd.read_csv(OUT / "external_blind_auditor_A_template.csv")
    leaks = sorted(FORBIDDEN_BLIND_COLUMNS.intersection(template.columns))
    integrity = pd.DataFrame(
        [
            {
                "check": "packet_size",
                "value": len(packet),
                "passes": len(packet) == TOTAL_PACKET_SIZE,
                "evidence_scope": SCOPE,
            },
            {
                "check": "two_auditor_templates_created",
                "value": "external_blind_auditor_A_template.csv;external_blind_auditor_B_template.csv",
                "passes": (OUT / "external_blind_auditor_A_template.csv").exists()
                and (OUT / "external_blind_auditor_B_template.csv").exists(),
                "evidence_scope": SCOPE,
            },
            {
                "check": "blind_templates_hide_arm_score_rank_and_prior_labels",
                "value": ",".join(leaks),
                "passes": len(leaks) == 0,
                "evidence_scope": SCOPE,
            },
            {
                "check": "raw_only_arm_available",
                "value": int(
                    (
                        labels["queue_raw_topK_reference"].astype(bool)
                        & ~labels["queue_simulated_strict_release"].astype(bool)
                    ).sum()
                ),
                "passes": False,
                "evidence_scope": SCOPE,
            },
            {
                "check": "returned_independent_labels_available",
                "value": 0,
                "passes": False,
                "evidence_scope": SCOPE,
            },
        ]
    )
    integrity.to_csv(OUT / "table_ctc_external_blind_audit_packet_integrity.csv", index=False)

    claim_gate = pd.DataFrame(
        [
            {
                "claim_gate": "ctc_external_blind_audit_mini_study",
                "status": "packet_frozen_pending_independent_labels",
                "positive_evidence": "no",
                "auditor_count_required": 2,
                "packet_rows": len(packet),
                "claim_ready_condition": "returned labels from two blinded auditors plus adjudication; release arm support rate and raw/boundary/random controls reported",
                "current_blocker": "independent blind labels not returned; true raw-only arm not available in tracked public source package",
                "allowed_current_claim": "A CTC external blind one-sided audit mini-study packet has been frozen.",
                "forbidden_current_claim": "Do not claim completed external audit, expert microscopy adjudication, raw-only comparator success, or new positive evidence from Phase81.",
                "evidence_scope": SCOPE,
            }
        ]
    )
    claim_gate.to_csv(OUT / "table_ctc_external_blind_audit_claim_gate.csv", index=False)

    figure = pd.DataFrame(
        [
            {
                "panel": "A",
                "quantity": "packet_rows",
                "value": len(packet),
                "label": "frozen blind audit packet rows",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "B",
                "quantity": "parc_release_rows",
                "value": int(packet["intended_arm"].eq("parc_release_core").sum()),
                "label": "PARC release arm rows",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "B",
                "quantity": "raw_only_rows_available",
                "value": 0,
                "label": "true raw-only arm rows available in current packet",
                "evidence_scope": SCOPE,
            },
            {
                "panel": "C",
                "quantity": "independent_labels_returned",
                "value": 0,
                "label": "pending labels",
                "evidence_scope": SCOPE,
            },
        ]
    )
    figure.to_csv(OUT / "figure_ctc_external_blind_audit_packet_inputs.csv", index=False)


def write_docs() -> None:
    protocol = f"""# Phase81 CTC External Blind One-Sided Audit Mini-Study Protocol

Status: `packet_frozen_pending_independent_labels`.

Objective: convert the PARC-A CTC active-verification result from masked-label
emulation toward a real verification-workflow mini-study.  Two independent
auditors receive blinded link-pair review templates and label each row as:

- `same_cell_supported`;
- `unsupported`;
- `uncertain`.

Only `same_cell_supported` can be used as one-sided verified support.  Unsupported
or uncertain labels are not trusted negatives for PARC calibration.

Frozen packet:

- packet rows: {TOTAL_PACKET_SIZE};
- randomized item IDs: `CTC-PHASE81-0001` ... `CTC-PHASE81-0600`;
- templates: `external_blind_auditor_A_template.csv` and
  `external_blind_auditor_B_template.csv`;
- adjudication template: `external_blind_adjudication_template.csv`.

Important limitation: the current tracked Phase78 source package does not
contain a true raw-only top-K arm.  All tracked raw-topK reference rows overlap
the simulated strict-release queue.  Therefore this packet includes a
raw-topK-overlap reference control and records true raw-only as a blocker until
the full CTC candidate universe is restored or regenerated.

Current evidence boundary:

- this is not completed positive evidence;
- do not claim expert microscopy adjudication;
- do not claim raw-only comparator success;
- do not claim a new CTC ground-truth benchmark;
- do not use this as materials or DFT evidence.
"""
    (OUT / "PHASE81_CTC_EXTERNAL_BLIND_AUDIT_PROTOCOL.md").write_text(protocol, encoding="utf-8")

    readme = f"""# Phase81 CTC External Blind Audit Packet

Status: `packet_frozen_pending_independent_labels`.

This milestone freezes a two-auditor blind review packet for a CTC one-sided
audit mini-study.  It does not create or ingest new labels.  It exists so that
the final manuscript can truthfully distinguish:

- Phase63/65b: masked-label active-audit emulation;
- Phase78: integrated trained human-confirmed CTC release audit;
- Phase81: external blind mini-study packet pending independent labels.

Claim boundary:

`Phase81` may currently support only the claim that an external blind audit
packet and scoring schema are frozen.  It may not support a completed audit result
until both auditor templates are returned and adjudicated.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")


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


def upsert_artifact_index() -> None:
    row = {
        "milestone": "ncs_phase81_ctc_external_blind_audit_mini_study",
        "path": rel(OUT) + "/",
        "evidence_state": "packet_frozen_pending_independent_labels_not_positive_evidence",
        "manifest": rel(OUT / "MANIFEST_SHA256.txt"),
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase81_ctc_external_blind_audit_mini_study",
    }
    if ARTIFACT_INDEX.exists():
        index = pd.read_csv(ARTIFACT_INDEX)
        index = index[index["milestone"] != row["milestone"]]
        for col in row:
            if col not in index.columns:
                index[col] = ""
        index = pd.concat([index[index.columns], pd.DataFrame([row])[index.columns]], ignore_index=True)
    else:
        index = pd.DataFrame([row])
    index.to_csv(ARTIFACT_INDEX, index=False)


def upsert_evidence_ledger() -> None:
    row = {
        "claim_id": "CTC-EXT-BLIND-AUDIT-001",
        "claim_text": "A CTC external blind one-sided audit mini-study packet is frozen for two independent auditors.",
        "evidence_type": "external_blind_audit_packet",
        "positive_evidence": "no",
        "scope": "packet_frozen_pending_independent_labels;not_completed_audit",
        "artifact_path": rel(OUT / "table_ctc_external_blind_audit_claim_gate.csv"),
        "hash": sha256_file(OUT / "table_ctc_external_blind_audit_claim_gate.csv"),
        "validation_command": "make reproduce-ncs-phase81-ctc-external-blind-audit-mini-study",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_completed_external_audit_expert_adjudication_raw_only_comparator_or_new_positive_evidence",
    }
    ledger = pd.read_csv(LEDGER)
    ledger = ledger[ledger["claim_id"] != row["claim_id"]]
    ledger = pd.concat([ledger, pd.DataFrame([row])], ignore_index=True)
    ledger.to_csv(LEDGER, index=False)


def upsert_claim_table() -> None:
    section = """\n## Phase81 CTC External Blind Audit Mini-Study\n\nStatus: `packet_frozen_pending_independent_labels`.\n\nPhase81 freezes a two-auditor blind CTC link-audit mini-study packet (600 rows)\nwith auditor templates, adjudication template, ingest schema and arm registry.\nIt is designed to turn the PARC-A CTC active-audit result into a real\nverification-workflow study once independent labels are returned.  Current\ntracked source rows do not contain a true raw-only top-K arm; this is recorded\nas a blocker.  Phase81 is not completed positive evidence and must not be\nwritten as expert microscopy adjudication, raw-only comparator success, or a\nnew CTC benchmark.\n"""
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    marker = "## Phase81 CTC External Blind Audit Mini-Study"
    if marker in text:
        text = text[: text.index(marker)].rstrip() + "\n" + section
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    labels = load_source()
    packet = build_packet(labels)
    write_packet_files(packet)
    write_summaries(packet, labels)
    write_docs()
    write_manifest(OUT)
    upsert_artifact_index()
    upsert_evidence_ledger()
    upsert_claim_table()
    write_root_manifest()
    print(f"[phase81] wrote {OUT.relative_to(ROOT)}")
    print("[phase81] status=packet_frozen_pending_independent_labels")


if __name__ == "__main__":
    main()
