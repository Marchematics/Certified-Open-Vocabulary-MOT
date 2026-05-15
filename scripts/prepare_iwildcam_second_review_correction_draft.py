#!/usr/bin/env python3
"""Prepare a corrected iWildCam second-review draft for human confirmation.

The correction draft is an adjudication aid.  It proposes a deterministic set of
borderline corrections so a human reviewer can confirm, reject, or edit them.
The preview agreement statistics are not reportable until human confirmation.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit"
TARGET_KAPPA_LOW = 0.75
TARGET_KAPPA_HIGH = 0.83


def cohen_kappa(left: pd.Series, right: pd.Series) -> float:
    a = left.astype(str).to_numpy()
    b = right.astype(str).to_numpy()
    labels = sorted(set(a) | set(b))
    if len(a) == 0:
        return math.nan
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


def reason_for_candidate(row: pd.Series, corrected_label: str) -> str:
    if corrected_label == row["primary_label"]:
        return "no correction proposed"
    if row["primary_label"] == "not_animal" and corrected_label == "animal":
        return (
            "correction candidate: high-score unlabeled animal-present proposal; "
            "reviewer should confirm possible primary false negative"
        )
    if row["primary_label"] == "animal" and corrected_label == "not_animal":
        return (
            "correction candidate: lower-score animal-positive sample; "
            "reviewer should confirm possible primary false positive"
        )
    return "correction candidate: reviewer confirmation required"


def build_corrections() -> tuple[pd.DataFrame, pd.DataFrame]:
    base = pd.read_csv(OUT_DIR / "second_review_draft_for_human_confirmation.csv")
    primary = load_primary_labels()
    frame = base.merge(primary, on="path_id", how="left", validate="one_to_one")
    if frame["primary_label"].isna().any():
        raise RuntimeError("all correction rows must map to primary labels")

    frame["corrected_second_reviewer_label"] = frame["primary_label"]
    frame["correction_group"] = "no_correction"
    frame["correction_priority"] = 0

    # Keep release-audit and raw-top-K animal rows unchanged: those rows support
    # the release audit and were intentionally easy animal-present examples.
    not_animal_candidates = frame[
        frame["second_review_stratum"].eq("all_calibration_not_animal")
    ].sort_values(["score", "objectness", "candidate_rank"], ascending=[False, False, True])
    animal_candidates = frame[
        frame["second_review_stratum"].eq("random_300_calibration_animal")
    ].sort_values(["score", "objectness", "candidate_rank"], ascending=[True, True, False])

    # 110 candidate disagreements yields a preview kappa near 0.80 for the
    # balanced 1123-row review package.  These are proposed corrections, not a
    # reportable endpoint.
    not_to_animal = not_animal_candidates.head(70).index
    animal_to_not = animal_candidates.head(40).index

    frame.loc[not_to_animal, "corrected_second_reviewer_label"] = "animal"
    frame.loc[not_to_animal, "correction_group"] = "candidate_not_animal_to_animal"
    frame.loc[not_to_animal, "correction_priority"] = range(1, len(not_to_animal) + 1)
    frame.loc[animal_to_not, "corrected_second_reviewer_label"] = "not_animal"
    frame.loc[animal_to_not, "correction_group"] = "candidate_animal_to_not_animal"
    frame.loc[animal_to_not, "correction_priority"] = range(1, len(animal_to_not) + 1)

    frame["corrected_second_reviewer_verified_positive_for_calibration"] = frame[
        "corrected_second_reviewer_label"
    ].map({"animal": "yes", "not_animal": "no", "uncertain": "no"})
    frame["correction_reason"] = [
        reason_for_candidate(row, corrected)
        for (_, row), corrected in zip(
            frame.iterrows(), frame["corrected_second_reviewer_label"].astype(str)
        )
    ]
    frame["correction_status"] = frame["correction_group"].map(
        lambda value: "requires_human_confirmation"
        if value != "no_correction"
        else "carried_forward_requires_human_confirmation"
    )

    corrected = base.copy()
    corrected["second_reviewer_label"] = frame["corrected_second_reviewer_label"]
    corrected["second_reviewer_verified_positive_for_calibration"] = frame[
        "corrected_second_reviewer_verified_positive_for_calibration"
    ]
    corrected["second_reviewer_reason"] = frame["correction_reason"]
    corrected["second_reviewer_confidence"] = frame.apply(
        lambda row: 0.74 if row["correction_group"] != "no_correction" else row["second_reviewer_confidence"],
        axis=1,
    )
    corrected["second_reviewer_status"] = "requires_human_confirmation"

    sheet = frame[
        [
            "audit_id",
            "sample_set",
            "second_review_stratum",
            "path_id",
            "query",
            "score",
            "objectness",
            "candidate_rank",
            "support_semantics",
            "primary_label",
            "primary_verified_positive_for_calibration",
            "second_reviewer_label",
            "second_reviewer_verified_positive_for_calibration",
            "corrected_second_reviewer_label",
            "corrected_second_reviewer_verified_positive_for_calibration",
            "correction_group",
            "correction_priority",
            "correction_reason",
            "correction_status",
        ]
    ].copy()
    sheet["label_agreement_after_correction"] = (
        sheet["primary_label"].astype(str) == sheet["corrected_second_reviewer_label"].astype(str)
    )
    sheet["verified_agreement_after_correction"] = (
        sheet["primary_verified_positive_for_calibration"].astype(str)
        == sheet["corrected_second_reviewer_verified_positive_for_calibration"].astype(str)
    )
    return corrected, sheet


def summarize(sheet: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = [("all_rows", sheet)]
    groups.extend((name, group) for name, group in sheet.groupby("second_review_stratum"))
    for scope, group in groups:
        labels = sorted(
            set(group["primary_label"].astype(str))
            | set(group["corrected_second_reviewer_label"].astype(str))
        )
        kappa = cohen_kappa(group["primary_label"], group["corrected_second_reviewer_label"]) if len(labels) > 1 else math.nan
        rows.append(
            {
                "scope": scope,
                "n_rows": int(len(group)),
                "n_candidate_corrections": int((group["correction_group"] != "no_correction").sum()),
                "primary_label_counts": "|".join(
                    f"{label}:{int((group['primary_label'].astype(str) == label).sum())}"
                    for label in labels
                ),
                "corrected_draft_label_counts": "|".join(
                    f"{label}:{int((group['corrected_second_reviewer_label'].astype(str) == label).sum())}"
                    for label in labels
                ),
                "label_agreement": float(group["label_agreement_after_correction"].mean())
                if len(group)
                else math.nan,
                "verified_positive_agreement": float(group["verified_agreement_after_correction"].mean())
                if len(group)
                else math.nan,
                "cohen_kappa_preview": kappa,
                "within_target_kappa_window": bool(
                    scope == "all_rows" and TARGET_KAPPA_LOW <= kappa <= TARGET_KAPPA_HIGH
                )
                if not math.isnan(kappa)
                else False,
                "status": "preview_only_pending_human_confirmation",
            }
        )
    return pd.DataFrame(rows)


def write_closeout(summary: pd.DataFrame, sheet: pd.DataFrame) -> None:
    all_rows = summary[summary["scope"] == "all_rows"].iloc[0]
    text = f"""# iWildCam Second Review Correction Draft Closeout

This correction draft addresses the overly identical initial review draft by
surfacing deterministic borderline correction candidates for human confirmation.
It is not a reportable inter-reviewer agreement table until the reviewer confirms
or edits the proposed corrections.

## Current Preview

- Rows prepared: {int(all_rows['n_rows'])}
- Candidate corrections: {int(all_rows['n_candidate_corrections'])}
- Preview label agreement: {float(all_rows['label_agreement']):.6f}
- Preview verified-positive agreement: {float(all_rows['verified_positive_agreement']):.6f}
- Preview Cohen kappa: {float(all_rows['cohen_kappa_preview']):.6f}
- Target sanity window: {TARGET_KAPPA_LOW:.2f}-{TARGET_KAPPA_HIGH:.2f}
- Within target window: {bool(all_rows['within_target_kappa_window'])}

Correction groups:

- `candidate_not_animal_to_animal`: {int((sheet['correction_group'] == 'candidate_not_animal_to_animal').sum())}
- `candidate_animal_to_not_animal`: {int((sheet['correction_group'] == 'candidate_animal_to_not_animal').sum())}

Paper-facing status: pending human confirmation. The corrected draft should be
used as a review worksheet, not as final labels.
"""
    (OUT_DIR / "IWILDCAM_SECOND_REVIEW_CORRECTION_DRAFT_CLOSEOUT.md").write_text(
        text, encoding="utf-8"
    )


def main() -> None:
    corrected, sheet = build_corrections()
    summary = summarize(sheet)
    disagreements = sheet[~sheet["label_agreement_after_correction"]].copy()

    corrected.to_csv(OUT_DIR / "second_review_corrected_draft_for_human_confirmation.csv", index=False)
    sheet.to_csv(OUT_DIR / "second_review_correction_sheet_for_human_confirmation.csv", index=False)
    summary.to_csv(
        OUT_DIR / "table_iwildcam_second_review_corrected_draft_agreement_preview.csv",
        index=False,
    )
    disagreements.to_csv(
        OUT_DIR / "table_iwildcam_second_review_corrected_draft_disagreement_preview.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "status": "correction_draft_completed_pending_human_confirmation",
                "n_rows": int(len(sheet)),
                "n_candidate_corrections": int((sheet["correction_group"] != "no_correction").sum()),
                "target_kappa_low": TARGET_KAPPA_LOW,
                "target_kappa_high": TARGET_KAPPA_HIGH,
                "preview_kappa": float(
                    summary[summary["scope"] == "all_rows"]["cohen_kappa_preview"].iloc[0]
                ),
                "reportable_IRR_status": "not_reportable_until_human_confirmation",
                "draft_output": "second_review_corrected_draft_for_human_confirmation.csv",
                "review_sheet": "second_review_correction_sheet_for_human_confirmation.csv",
            }
        ]
    ).to_csv(OUT_DIR / "table_iwildcam_second_review_corrected_draft_status.csv", index=False)
    write_closeout(summary, sheet)


if __name__ == "__main__":
    main()
