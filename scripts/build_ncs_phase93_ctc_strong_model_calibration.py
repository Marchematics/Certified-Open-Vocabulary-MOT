#!/usr/bin/env python3
"""Calibrate Phase91 CTC strong-model surrogate labels against existing human labels.

Phase93 is a retrospective calibration of the Phase91 deterministic
image/template/segmentation surrogate against the already available CTC strict
human-audit table. It is not new external human evidence and must not be used
as a completed real-audit PARC-A replication.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
from scipy.stats import beta


ROOT = Path(__file__).resolve().parents[1]
PHASE81 = ROOT / "outputs/milestones/ncs_phase81_ctc_external_blind_audit_mini_study"
PHASE91 = ROOT / "outputs/milestones/ncs_phase91_ctc_strong_model_annotation"
HUMAN = ROOT / "outputs/milestones/ctc_strict_human_audit/ctc_strict_audit_human_confirmed_labels.csv"
OUT = ROOT / "outputs/milestones/ncs_phase93_ctc_strong_model_calibration"
LEDGER = ROOT / "outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv"
ARTIFACT_INDEX = ROOT / "outputs/artifact_index.csv"
CLAIM_TABLE = ROOT / "docs/claim_table.md"

SCOPE = (
    "ctc_strong_model_calibration_against_existing_human_labels;"
    "retrospective_internal_calibration;"
    "not_external_human_audit;"
    "not_CTC_ground_truth;"
    "not_completed_real_audit_positive_evidence;"
    "not_materials_or_DFT_evidence"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def cp_upper(failures: int, total: int, confidence: float = 0.95) -> float:
    if total <= 0:
        return 1.0
    if failures >= total:
        return 1.0
    return float(beta.ppf(confidence, failures + 1, total - failures))


def safe_div(num: float, den: float) -> float:
    return float(num / den) if den else 0.0


def load_joined_rows() -> pd.DataFrame:
    registry = pd.read_csv(PHASE81 / "table_ctc_external_blind_audit_packet_registry.csv")
    annotations = pd.read_csv(PHASE91 / "table_phase91_ctc_strong_model_annotations.csv")
    human = pd.read_csv(HUMAN)

    joined = (
        registry.merge(annotations, on="audit_item_id", how="left", validate="one_to_one")
        .merge(human, left_on="source_audit_id", right_on="audit_id", how="left", validate="many_to_one")
    )
    if joined["strong_model_label"].isna().any():
        raise RuntimeError("missing Phase91 strong-model labels after audit_item_id join")
    if joined["human_label"].isna().any():
        raise RuntimeError("missing existing human labels after source_audit_id join")

    joined["model_positive"] = joined["strong_model_label"].eq("same_cell_supported")
    joined["model_negative"] = joined["strong_model_label"].eq("unsupported")
    joined["model_uncertain"] = joined["strong_model_label"].eq("uncertain")
    joined["human_positive"] = joined["human_label"].eq("same_cell_link")
    joined["human_negative"] = joined["human_label"].eq("not_same_cell_link")
    joined["high_confidence_positive"] = joined["model_positive"] & joined["strong_model_confidence"].eq("high")
    for column in ["path_id", "ctc_dataset", "sequence_id", "frame_start", "frame_end"]:
        if column not in joined.columns and f"{column}_x" in joined.columns:
            joined[column] = joined[f"{column}_x"]
    joined["evidence_scope"] = SCOPE
    return joined


def summarize_group(group: pd.DataFrame, group_name: str, group_value: str) -> dict[str, object]:
    total = len(group)
    model_pos = group["model_positive"].sum()
    model_neg = group["model_negative"].sum()
    model_unc = group["model_uncertain"].sum()
    human_pos = group["human_positive"].sum()
    human_neg = group["human_negative"].sum()
    false_pos = int((group["model_positive"] & group["human_negative"]).sum())
    false_neg = int((group["model_negative"] & group["human_positive"]).sum())
    uncertain_human_pos = int((group["model_uncertain"] & group["human_positive"]).sum())
    uncertain_human_neg = int((group["model_uncertain"] & group["human_negative"]).sum())
    high_pos = group["high_confidence_positive"].sum()
    high_pos_false = int((group["high_confidence_positive"] & group["human_negative"]).sum())
    return {
        "group_name": group_name,
        "group_value": group_value,
        "rows": total,
        "human_positive": int(human_pos),
        "human_negative": int(human_neg),
        "model_positive": int(model_pos),
        "model_negative": int(model_neg),
        "model_uncertain": int(model_unc),
        "model_positive_precision_vs_existing_human": safe_div(model_pos - false_pos, model_pos),
        "model_positive_false_positive_count": false_pos,
        "model_positive_cp95_upper_false_positive_rate": cp_upper(false_pos, int(model_pos)),
        "model_negative_false_negative_count": false_neg,
        "model_uncertain_human_positive": uncertain_human_pos,
        "model_uncertain_human_negative": uncertain_human_neg,
        "high_confidence_positive": int(high_pos),
        "high_confidence_positive_false_count": high_pos_false,
        "high_confidence_positive_cp95_upper_false_positive_rate": cp_upper(high_pos_false, int(high_pos)),
        "evidence_scope": SCOPE,
    }


def build_tables(joined: pd.DataFrame) -> dict[str, pd.DataFrame]:
    confusion = pd.crosstab(joined["strong_model_label"], joined["human_label"], dropna=False).reset_index()
    confusion["evidence_scope"] = SCOPE

    rows = [summarize_group(joined, "all", "all")]
    for packet, group in joined.groupby("packet", sort=True):
        rows.append(summarize_group(group, "packet", str(packet)))
    for arm, group in joined.groupby("intended_arm", sort=True):
        rows.append(summarize_group(group, "intended_arm", str(arm)))
    by_group = pd.DataFrame(rows)

    high = summarize_group(joined[joined["high_confidence_positive"]], "high_confidence_positive", "true")
    gate = pd.DataFrame(
        [
            {
                "claim_gate": "phase93_ctc_strong_model_calibration",
                "status": "retrospective_surrogate_calibration_passed_against_existing_human_labels",
                "positive_evidence": "no",
                "joined_rows": len(joined),
                "high_confidence_positive_rows": high["rows"],
                "high_confidence_false_positive_count": high["model_positive_false_positive_count"],
                "high_confidence_cp95_upper_false_positive_rate": high[
                    "model_positive_cp95_upper_false_positive_rate"
                ],
                "allowed_current_claim": "Phase93 calibrates the Phase91 CTC surrogate against existing human labels for dry-run reliability assessment.",
                "forbidden_current_claim": "Do not claim new external human audit evidence, official CTC ground truth, completed real-audit PARC-A replication, materials evidence, or DFT evidence.",
                "evidence_scope": SCOPE,
            }
        ]
    )

    figure = by_group[
        [
            "group_name",
            "group_value",
            "rows",
            "human_positive",
            "human_negative",
            "model_positive",
            "model_negative",
            "model_uncertain",
            "model_positive_precision_vs_existing_human",
            "model_positive_cp95_upper_false_positive_rate",
            "high_confidence_positive",
            "high_confidence_positive_cp95_upper_false_positive_rate",
            "evidence_scope",
        ]
    ].copy()

    row_cols = [
        "audit_item_id",
        "packet",
        "intended_arm",
        "source_audit_id",
        "path_id",
        "strong_model_label",
        "strong_model_confidence",
        "strong_model_support_score",
        "model_positive",
        "model_negative",
        "model_uncertain",
        "high_confidence_positive",
        "human_label",
        "human_confidence",
        "human_review_status",
        "human_positive",
        "human_negative",
        "ctc_dataset",
        "sequence_id",
        "frame_start",
        "frame_end",
        "evidence_scope",
    ]
    return {
        "rows": joined[row_cols].copy(),
        "confusion": confusion,
        "by_group": by_group,
        "gate": gate,
        "figure": figure,
    }


def write_outputs(tables: dict[str, pd.DataFrame]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    tables["rows"].to_csv(OUT / "table_phase93_strong_model_vs_existing_human_labels.csv", index=False)
    tables["confusion"].to_csv(OUT / "table_phase93_strong_model_confusion.csv", index=False)
    tables["by_group"].to_csv(OUT / "table_phase93_strong_model_by_packet_calibration.csv", index=False)
    tables["gate"].to_csv(OUT / "table_phase93_high_confidence_gate.csv", index=False)
    tables["figure"].to_csv(OUT / "figure_phase93_strong_model_calibration_inputs.csv", index=False)


def write_docs(tables: dict[str, pd.DataFrame]) -> None:
    gate = tables["gate"].iloc[0]
    readme = f"""# Phase93 CTC Strong-Model Calibration

Status: `retrospective_surrogate_calibration_passed_against_existing_human_labels`.

Phase93 joins the frozen Phase81 CTC audit packet, Phase91 surrogate labels and
the existing CTC strict human-audit labels. It is a retrospective calibration
of the model surrogate, not a new external human audit.

Key dry-run facts:

- joined rows: `{int(gate['joined_rows'])}`;
- high-confidence surrogate positives: `{int(gate['high_confidence_positive_rows'])}`;
- high-confidence surrogate false positives versus existing human labels:
  `{int(gate['high_confidence_false_positive_count'])}`;
- CP95 upper false-positive fraction for high-confidence positives:
  `{float(gate['high_confidence_cp95_upper_false_positive_rate']):.6f}`.

Evidence scope: `{SCOPE}`.
"""
    (OUT / "README_evidence_scope.md").write_text(readme, encoding="utf-8")

    protocol = """# Phase93 Protocol: CTC Strong-Model Calibration

Inputs:

- Phase81 frozen CTC audit packet registry;
- Phase91 deterministic model-surrogate annotations;
- existing CTC strict human-audit labels.

Procedure:

1. Join Phase81 packet rows to Phase91 labels by `audit_item_id`.
2. Join to existing CTC human labels by `source_audit_id == audit_id`.
3. Treat `same_cell_supported` as model positive, `unsupported` as model
   negative, and `uncertain` as abstention.
4. Report confusion and high-confidence positive calibration against existing
   human labels.

This is retrospective calibration only. It is not external human audit evidence.
"""
    (OUT / "PHASE93_CTC_STRONG_MODEL_CALIBRATION_PROTOCOL.md").write_text(protocol, encoding="utf-8")


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


def update_artifact_index() -> None:
    row = {
        "milestone": "ncs_phase93_ctc_strong_model_calibration",
        "path": "outputs/milestones/ncs_phase93_ctc_strong_model_calibration/",
        "evidence_state": "retrospective_surrogate_calibration_passed_against_existing_human_labels",
        "manifest": "outputs/milestones/ncs_phase93_ctc_strong_model_calibration/MANIFEST_SHA256.txt",
        "public_bundle_check": "python scripts/validate_public_bundle.py outputs/milestones/ncs_phase93_ctc_strong_model_calibration",
        "notes": "CTC surrogate calibration against existing human labels; not new external human evidence.",
    }
    df = pd.read_csv(ARTIFACT_INDEX)
    df = df[df["milestone"] != row["milestone"]]
    pd.concat([df, pd.DataFrame([row]).reindex(columns=df.columns)], ignore_index=True).to_csv(
        ARTIFACT_INDEX, index=False
    )


def update_ledger() -> None:
    row = {
        "claim_id": "CTC-PHASE93-STRONG-MODEL-CALIBRATION-001",
        "claim_text": "Phase93 calibrates the CTC strong-model surrogate against existing human labels on the frozen Phase81 packet.",
        "evidence_type": "retrospective_surrogate_calibration",
        "positive_evidence": "no",
        "scope": "existing_human_label_calibration;not_external_human_audit",
        "artifact_path": "outputs/milestones/ncs_phase93_ctc_strong_model_calibration/table_phase93_high_confidence_gate.csv",
        "hash": sha256_file(OUT / "table_phase93_high_confidence_gate.csv"),
        "validation_command": "make reproduce-ncs-phase93-ctc-strong-model-calibration",
        "status": "PASS",
        "overclaim_guardrail": "do_not_claim_new_external_human_audit_or_completed_real_audit_from_surrogate_calibration",
    }
    df = pd.read_csv(LEDGER)
    df = df[df["claim_id"] != row["claim_id"]]
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(LEDGER, index=False)


def update_claim_table() -> None:
    section = """\n## Phase93 CTC Strong-Model Calibration\n\nStatus: `retrospective_surrogate_calibration_passed_against_existing_human_labels`.\n\nPhase93 calibrates Phase91 deterministic CTC surrogate labels against existing\nCTC strict human-audit labels on the frozen Phase81 packet. It supports dry-run\nsurrogate reliability assessment only. It is not new external human audit\nevidence, official CTC ground truth, completed real-audit PARC-A replication,\nmaterials evidence, or DFT evidence.\n"""
    marker = "## Phase93 CTC Strong-Model Calibration"
    text = CLAIM_TABLE.read_text(encoding="utf-8")
    if marker in text:
        before = text.split(marker)[0].rstrip()
        after = text.split(marker, 1)[1]
        next_idx = after.find("\n## ")
        text = before + "\n" + section + (after[next_idx:] if next_idx >= 0 else "")
    else:
        text = text.rstrip() + "\n" + section
    CLAIM_TABLE.write_text(text, encoding="utf-8")


def main() -> None:
    joined = load_joined_rows()
    tables = build_tables(joined)
    write_outputs(tables)
    write_docs(tables)
    write_manifest(OUT)
    update_artifact_index()
    update_ledger()
    update_claim_table()
    write_root_manifest()
    print(f"[phase93-ctc] wrote {rel(OUT)}")
    print("[phase93-ctc] status=retrospective_surrogate_calibration_passed_against_existing_human_labels")


if __name__ == "__main__":
    main()
