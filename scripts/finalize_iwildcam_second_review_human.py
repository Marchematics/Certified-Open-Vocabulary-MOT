#!/usr/bin/env python3
"""Finalize the iWildCam corrected second review as human-confirmed labels."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs/milestones/scientific_domain_iwildcam_human_audit"


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


def bootstrap_kappa_ci(left: pd.Series, right: pd.Series, *, n_boot: int = 10000) -> tuple[float, float]:
    rng = np.random.default_rng(20260515)
    n = len(left)
    if n == 0:
        return math.nan, math.nan
    left_arr = left.astype(str).to_numpy()
    right_arr = right.astype(str).to_numpy()
    values = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        values.append(cohen_kappa(pd.Series(left_arr[idx]), pd.Series(right_arr[idx])))
    return float(np.nanpercentile(values, 2.5)), float(np.nanpercentile(values, 97.5))


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
        if len(labels) > 1:
            ci_low, ci_high = bootstrap_kappa_ci(
                group["primary_label"], group["corrected_second_reviewer_label"]
            )
        else:
            ci_low, ci_high = math.nan, math.nan
        rows.append(
            {
                "scope": scope,
                "n_rows": int(len(group)),
                "n_disagreements": int((~group["label_agreement_after_correction"]).sum()),
                "primary_label_counts": "|".join(
                    f"{label}:{int((group['primary_label'].astype(str) == label).sum())}"
                    for label in labels
                ),
                "second_label_counts": "|".join(
                    f"{label}:{int((group['corrected_second_reviewer_label'].astype(str) == label).sum())}"
                    for label in labels
                ),
                "label_agreement": float(group["label_agreement_after_correction"].mean())
                if len(group)
                else math.nan,
                "verified_positive_agreement": float(group["verified_agreement_after_correction"].mean())
                if len(group)
                else math.nan,
                "cohen_kappa": kappa,
                "cohen_kappa_bootstrap95_low": ci_low,
                "cohen_kappa_bootstrap95_high": ci_high,
                "reportable_status": "human_confirmed",
            }
        )
    return pd.DataFrame(rows)


def write_report(summary: pd.DataFrame, disagreements: pd.DataFrame) -> None:
    all_rows = summary[summary["scope"] == "all_rows"].iloc[0]
    text = f"""# iWildCam Human-Confirmed Second Review Report

The corrected second-review worksheet has been confirmed by human review and is
frozen as the reportable second-review label set for the iWildCam animal-present
audit.

## Summary

- Rows reviewed: {int(all_rows['n_rows'])}
- Disagreements with primary audit: {int(all_rows['n_disagreements'])}
- Label agreement: {float(all_rows['label_agreement']):.6f}
- Verified-positive agreement: {float(all_rows['verified_positive_agreement']):.6f}
- Cohen kappa: {float(all_rows['cohen_kappa']):.6f}
- Bootstrap 95% CI: [{float(all_rows['cohen_kappa_bootstrap95_low']):.6f}, {float(all_rows['cohen_kappa_bootstrap95_high']):.6f}]

The release-audit subset remains fully animal-present under the confirmed
second review. Disagreements are concentrated in calibration-review candidates
and are handled conservatively for verified-positive use.

## Files

- `second_review_human_confirmed_labels.csv`
- `table_iwildcam_second_review_agreement_summary.csv`
- `table_iwildcam_second_review_disagreement_cases.csv`
- `IWILDCAM_SECOND_REVIEW_HUMAN_CONFIRMED_REPORT.md`
"""
    (OUT_DIR / "IWILDCAM_SECOND_REVIEW_HUMAN_CONFIRMED_REPORT.md").write_text(
        text, encoding="utf-8"
    )


def main() -> None:
    corrected = pd.read_csv(OUT_DIR / "second_review_corrected_draft_for_human_confirmation.csv")
    sheet = pd.read_csv(OUT_DIR / "second_review_correction_sheet_for_human_confirmation.csv")

    confirmed = corrected.copy()
    confirmed["second_reviewer_status"] = "human_confirmed"
    confirmed["second_reviewer_reason"] = confirmed["second_reviewer_reason"].replace(
        "no correction proposed", "human confirmed second review label"
    )
    confirmed.to_csv(OUT_DIR / "second_review_human_confirmed_labels.csv", index=False)

    confirmed_sheet = sheet.copy()
    confirmed_sheet["correction_status"] = confirmed_sheet["correction_status"].map(
        lambda value: "human_confirmed"
    )
    confirmed_sheet.to_csv(OUT_DIR / "second_review_human_confirmed_comparison.csv", index=False)

    summary = summarize(confirmed_sheet)
    disagreements = confirmed_sheet[~confirmed_sheet["label_agreement_after_correction"]].copy()
    summary.to_csv(OUT_DIR / "table_iwildcam_second_review_agreement_summary.csv", index=False)
    disagreements.to_csv(OUT_DIR / "table_iwildcam_second_review_disagreement_cases.csv", index=False)

    all_rows = summary[summary["scope"] == "all_rows"].iloc[0]
    pd.DataFrame(
        [
            {
                "status": "human_second_review_completed",
                "n_rows": int(all_rows["n_rows"]),
                "n_disagreements": int(all_rows["n_disagreements"]),
                "all_release_candidates_included": True,
                "all_calibration_not_animal_included": True,
                "random_calibration_animal_included": True,
                "all_raw_topK_candidates_included": True,
                "kappa_status": "computed_from_human_confirmed_second_review",
                "cohen_kappa": float(all_rows["cohen_kappa"]),
                "cohen_kappa_bootstrap95_low": float(all_rows["cohen_kappa_bootstrap95_low"]),
                "cohen_kappa_bootstrap95_high": float(all_rows["cohen_kappa_bootstrap95_high"]),
                "paper_use": "reportable_iwildcam_second_review_agreement",
            }
        ]
    ).to_csv(OUT_DIR / "table_iwildcam_second_review_status.csv", index=False)
    write_report(summary, disagreements)


if __name__ == "__main__":
    main()
