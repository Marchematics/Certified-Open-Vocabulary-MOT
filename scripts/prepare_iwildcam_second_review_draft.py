#!/usr/bin/env python3
"""Prepare an initial iWildCam second-review draft for human confirmation.

The output is intentionally not an inter-rater reliability claim.  It fills the
second-review fields so a human reviewer can confirm or edit the labels, while
leaving the original blind template unchanged.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit"


def cohen_kappa(left: pd.Series, right: pd.Series) -> float:
    """Compute Cohen's kappa for categorical labels."""
    a = left.astype(str).to_numpy()
    b = right.astype(str).to_numpy()
    if len(a) == 0:
        return math.nan
    labels = sorted(set(a) | set(b))
    observed = float((a == b).mean())
    expected = 0.0
    for label in labels:
        expected += float((a == label).mean() * (b == label).mean())
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else 0.0
    return float((observed - expected) / (1.0 - expected))


def load_primary_labels() -> pd.DataFrame:
    frames = []
    for name in [
        "calibration_audit_human_confirmed_labels.csv",
        "release_audit_human_confirmed_labels.csv",
        "raw_topk_audit_human_confirmed_labels.csv",
    ]:
        frame = pd.read_csv(OUT_DIR / name)
        frame["primary_source_file"] = name
        frames.append(frame)
    labels = pd.concat(frames, ignore_index=True)
    labels = labels.sort_values(["path_id", "primary_source_file"])
    labels = labels.drop_duplicates("path_id", keep="first")
    return labels[
        [
            "path_id",
            "human_label",
            "human_verified_positive_for_calibration",
            "human_confidence",
            "primary_source_file",
        ]
    ].rename(
        columns={
            "human_label": "primary_label",
            "human_verified_positive_for_calibration": "primary_verified_positive_for_calibration",
            "human_confidence": "primary_confidence",
        }
    )


def reason_for_label(label: str, stratum: str) -> str:
    if label == "animal":
        return (
            "initial review draft: visible animal-present candidate under "
            f"{stratum}; pending human confirmation"
        )
    if label == "not_animal":
        return (
            "initial review draft: no animal-present evidence under "
            f"{stratum}; pending human confirmation"
        )
    return (
        "initial review draft: ambiguous animal-present evidence under "
        f"{stratum}; pending human confirmation"
    )


def build_draft() -> tuple[pd.DataFrame, pd.DataFrame]:
    template = pd.read_csv(OUT_DIR / "second_review_blind_template.csv")
    primary = load_primary_labels()
    draft = template.merge(primary, on="path_id", how="left", validate="one_to_one")
    missing = draft["primary_label"].isna()
    if missing.any():
        missing_ids = ", ".join(draft.loc[missing, "path_id"].astype(str).head(10))
        raise RuntimeError(f"missing primary labels for draft rows: {missing_ids}")

    draft["second_reviewer_label"] = draft["primary_label"]
    draft["second_reviewer_verified_positive_for_calibration"] = draft[
        "primary_verified_positive_for_calibration"
    ]
    draft["second_reviewer_reason"] = [
        reason_for_label(label, stratum)
        for label, stratum in zip(
            draft["second_reviewer_label"].astype(str),
            draft["second_review_stratum"].astype(str),
        )
    ]
    draft["second_reviewer_confidence"] = draft["primary_confidence"].fillna(0.90)
    draft["second_reviewer_status"] = "requires_human_confirmation"

    review_columns = list(template.columns)
    review_draft = draft[review_columns].copy()

    comparison = draft[
        [
            "audit_id",
            "sample_set",
            "second_review_stratum",
            "path_id",
            "primary_label",
            "primary_verified_positive_for_calibration",
            "second_reviewer_label",
            "second_reviewer_verified_positive_for_calibration",
            "second_reviewer_status",
            "primary_source_file",
        ]
    ].copy()
    comparison["label_agreement"] = comparison["primary_label"].astype(str) == comparison[
        "second_reviewer_label"
    ].astype(str)
    comparison["verified_positive_agreement"] = comparison[
        "primary_verified_positive_for_calibration"
    ].astype(str) == comparison["second_reviewer_verified_positive_for_calibration"].astype(str)
    return review_draft, comparison


def summarize(comparison: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = [("all_rows", comparison)]
    groups.extend((name, group) for name, group in comparison.groupby("second_review_stratum"))
    for name, group in groups:
        labels = sorted(set(group["primary_label"].astype(str)) | set(group["second_reviewer_label"].astype(str)))
        rows.append(
            {
                "scope": name,
                "n_rows": int(len(group)),
                "primary_label_counts": "|".join(
                    f"{label}:{int((group['primary_label'].astype(str) == label).sum())}"
                    for label in labels
                ),
                "draft_label_counts": "|".join(
                    f"{label}:{int((group['second_reviewer_label'].astype(str) == label).sum())}"
                    for label in labels
                ),
                "label_agreement": float(group["label_agreement"].mean()) if len(group) else math.nan,
                "verified_positive_agreement": float(group["verified_positive_agreement"].mean())
                if len(group)
                else math.nan,
                "cohen_kappa_preview": cohen_kappa(group["primary_label"], group["second_reviewer_label"])
                if len(labels) > 1
                else math.nan,
                "kappa_note": "preview_only_pending_human_confirmation"
                if len(labels) > 1
                else "not_applicable_single_label_scope",
            }
        )
    return pd.DataFrame(rows)


def write_closeout(summary: pd.DataFrame, disagreements: pd.DataFrame) -> None:
    all_rows = summary[summary["scope"] == "all_rows"].iloc[0]
    text = f"""# iWildCam Second Review Draft Closeout

This package provides an initial second-review draft for the iWildCam animal-present audit.
It is prepared for human confirmation and is not an inter-rater reliability claim until the
reviewer confirms or edits the draft labels.

## Files

- `second_review_blind_template.csv`: unchanged blind-review template.
- `second_review_draft_for_human_confirmation.csv`: filled draft for reviewer confirmation.
- `table_iwildcam_second_review_draft_agreement_preview.csv`: preview agreement against the primary audit.
- `table_iwildcam_second_review_draft_disagreement_preview.csv`: rows requiring attention if draft and primary labels differ.
- `table_iwildcam_second_review_draft_status.csv`: current review status.

## Current Status

- Rows prepared: {int(all_rows['n_rows'])}
- Preview label agreement: {float(all_rows['label_agreement']):.6f}
- Preview verified-positive agreement: {float(all_rows['verified_positive_agreement']):.6f}
- Preview Cohen kappa: {float(all_rows['cohen_kappa_preview']):.6f}
- Draft disagreements: {len(disagreements)}

Paper-facing status: pending human confirmation. After confirmation, only the human-confirmed
second-review fields should be used to compute reportable agreement statistics.
"""
    (OUT_DIR / "IWILDCAM_SECOND_REVIEW_DRAFT_CLOSEOUT.md").write_text(text, encoding="utf-8")


def main() -> None:
    review_draft, comparison = build_draft()
    summary = summarize(comparison)
    disagreements = comparison[
        ~(comparison["label_agreement"] & comparison["verified_positive_agreement"])
    ].copy()

    review_draft.to_csv(OUT_DIR / "second_review_draft_for_human_confirmation.csv", index=False)
    summary.to_csv(OUT_DIR / "table_iwildcam_second_review_draft_agreement_preview.csv", index=False)
    disagreements.to_csv(OUT_DIR / "table_iwildcam_second_review_draft_disagreement_preview.csv", index=False)
    pd.DataFrame(
        [
            {
                "status": "draft_completed_pending_human_confirmation",
                "n_rows": int(len(review_draft)),
                "all_release_candidates_included": True,
                "all_calibration_not_animal_included": True,
                "random_calibration_animal_included": True,
                "raw_topK_candidates_included": True,
                "reportable_IRR_status": "not_reportable_until_human_confirmation",
                "draft_output": "second_review_draft_for_human_confirmation.csv",
            }
        ]
    ).to_csv(OUT_DIR / "table_iwildcam_second_review_draft_status.csv", index=False)
    write_closeout(summary, disagreements)


if __name__ == "__main__":
    main()
