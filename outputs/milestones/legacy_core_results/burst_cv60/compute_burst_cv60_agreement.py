#!/usr/bin/env python3
"""Compute agreement for the BURST CV60 relabel packet.

Run this after an independent rater fills burst_cv60_blind_labels_template.csv
or a copy of it. If labels are still blank, the script writes an explicit
requires-labels status instead of producing agreement numbers.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


DEFAULT_DIR = Path("<PARC_ROOT>/outputs/phase7_burst_cv60")


def normalize_label(value: object) -> str:
    text = str(value).strip().lower()
    if text in {"actually_true", "actually_false", "uncertain"}:
        return text
    return ""


def normalize_yes_no(value: object) -> str:
    text = str(value).strip().lower()
    if text in {"yes", "true", "1", "y"}:
        return "yes"
    if text in {"no", "false", "0", "n"}:
        return "no"
    return ""


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa = {label: a.count(label) / n for label in labels}
    pb = {label: b.count(label) / n for label in labels}
    pe = sum(pa[label] * pb[label] for label in labels)
    if abs(1.0 - pe) < 1e-12:
        return 1.0 if abs(1.0 - po) < 1e-12 else 0.0
    return (po - pe) / (1.0 - pe)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cv-dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--labels", type=Path, default=None, help="Filled second-rater label CSV. Defaults to blind template.")
    args = parser.parse_args()

    cv_dir = args.cv_dir
    reference = pd.read_csv(cv_dir / "burst_cv60_reference_labels.csv")
    label_path = args.labels or (cv_dir / "burst_cv60_blind_labels_template.csv")
    second = pd.read_csv(label_path)

    merged = reference.merge(
        second[[
            "cv_id", "second_rater_label", "second_rater_verified_positive_for_calibration",
            "second_rater_reason", "second_rater_confidence", "second_rater",
        ]],
        on="cv_id",
        how="left",
    )
    merged["second_label_norm"] = merged["second_rater_label"].map(normalize_label)
    merged["second_verified_norm"] = merged["second_rater_verified_positive_for_calibration"].map(normalize_yes_no)
    merged["first_verified_norm"] = merged["first_verified_positive_for_calibration"].map(normalize_yes_no)

    complete_label = merged[merged["second_label_norm"].ne("")]
    complete_verified = merged[merged["second_verified_norm"].ne("")]
    status = "completed" if len(complete_label) == len(merged) and len(complete_verified) == len(merged) else "requires_independent_cross_validation_labels"

    summary = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "n_total": int(len(merged)),
        "n_second_label_filled": int(len(complete_label)),
        "n_second_verified_filled": int(len(complete_verified)),
        "label_percent_agreement": None,
        "label_cohen_kappa": None,
        "verified_percent_agreement": None,
        "verified_cohen_kappa": None,
    }
    if len(complete_label):
        label_agree = (complete_label["first_rater_label"] == complete_label["second_label_norm"]).mean()
        summary["label_percent_agreement"] = float(label_agree)
        summary["label_cohen_kappa"] = cohen_kappa(
            complete_label["first_rater_label"].astype(str).tolist(),
            complete_label["second_label_norm"].astype(str).tolist(),
        )
    if len(complete_verified):
        verified_agree = (complete_verified["first_verified_norm"] == complete_verified["second_verified_norm"]).mean()
        summary["verified_percent_agreement"] = float(verified_agree)
        summary["verified_cohen_kappa"] = cohen_kappa(
            complete_verified["first_verified_norm"].astype(str).tolist(),
            complete_verified["second_verified_norm"].astype(str).tolist(),
        )

    disagreements = merged[
        (merged["second_label_norm"].ne("")) & (merged["first_rater_label"] != merged["second_label_norm"])
        | ((merged["second_verified_norm"].ne("")) & (merged["first_verified_norm"] != merged["second_verified_norm"]))
    ].copy()
    keep = [
        "cv_id", "dataset", "video_id", "path_id", "query", "query_segment", "audit_source",
        "first_rater_label", "second_label_norm", "first_verified_norm", "second_verified_norm",
        "first_rater_reason", "second_rater_reason", "cv_montage_path",
    ]
    disagreements[[c for c in keep if c in disagreements.columns]].to_csv(cv_dir / "burst_cv60_disagreements.csv", index=False)
    pd.DataFrame([summary]).to_csv(cv_dir / "burst_cv60_agreement.csv", index=False)
    (cv_dir / "burst_cv60_agreement_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    main()
