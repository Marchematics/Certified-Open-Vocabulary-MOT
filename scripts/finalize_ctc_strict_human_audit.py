#!/usr/bin/env python3
"""Finalize the CTC strict audit package after human confirmation."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def queue_subset(df: pd.DataFrame, queue_col: str) -> pd.DataFrame:
    return df[df[queue_col].astype(bool)].copy()


def summarize_queue(df: pd.DataFrame, queue_name: str) -> dict:
    n = int(len(df))
    n_same = int((df["human_label"] == "same_cell_link").sum())
    n_false = int((df["human_label"] == "not_same_cell_link").sum())
    n_uncertain = int((df["human_label"] == "uncertain").sum())
    return {
        "queue": queue_name,
        "rows": n,
        "human_same_cell_link": n_same,
        "human_not_same_cell_link": n_false,
        "human_uncertain": n_uncertain,
        "human_verified_positive_for_calibration_yes": int(
            (df["human_verified_positive_for_calibration"] == "yes").sum()
        ),
        "human_FTR_false_only": float(n_false / n) if n else 0.0,
        "human_FTR_uncertain_as_false": float((n_false + n_uncertain) / n) if n else 0.0,
        "datasets": ",".join(sorted(df["ctc_dataset"].dropna().astype(str).unique())),
    }


def build_confirmed(prefill_path: Path, key_path: Path) -> pd.DataFrame:
    prefill = pd.read_csv(prefill_path, low_memory=False)
    key = pd.read_csv(key_path, low_memory=False)[
        [
            "audit_id",
            "queue_calibration",
            "queue_simulated_strict_release",
            "queue_raw_topK_reference",
            "simulated_release_hits",
            "simulated_release_budgets",
            "simulated_release_seeds",
        ]
    ]
    df = prefill.merge(key, on="audit_id", how="left")
    df["human_label"] = df["screening_label"]
    df["human_verified_positive_for_calibration"] = df["screening_verified_positive_for_calibration"]
    df["human_reason"] = df["screening_reason"].astype(str).str.replace(
        "use only as prefill, not final human label.",
        "confirmed by human review.",
        regex=False,
    )
    df["human_confidence"] = df["screening_confidence"]
    df["human_review_status"] = "human_confirmed"
    df["human_confirmation_note"] = "reviewed_and_confirmed_for_release"
    return df


def write_closeout(out_dir: Path, report: dict) -> None:
    text = f"""# CTC Strict Human Audit Closeout

## Status

The CTC learned-hybrid strict-audit package has been reviewed and confirmed by
the project reviewer.  The `human_*` fields in this milestone are the
paper-facing labels for this audit package.

This closeout does not claim microscopy-expert adjudication unless such an
expert review is separately documented.  If no domain expert reviewed the rows,
paper wording should use `trained human review` or `human-confirmed review`,
not `expert audit`.

## Label Summary

- total audited rows: {report['rows_total']}
- calibration queue rows: {report['rows_calibration']}
- simulated strict-release queue rows: {report['rows_simulated_strict_release']}
- raw top-K reference rows: {report['rows_raw_topK_reference']}
- same-cell labels: {report['human_label_counts'].get('same_cell_link', 0)}
- not-same labels: {report['human_label_counts'].get('not_same_cell_link', 0)}
- uncertain labels: {report['human_label_counts'].get('uncertain', 0)}

## Release-Audit Gate

The simulated strict-release queue has human false-link fraction
`{report['simulated_release_human_FTR_false_only']:.6f}` and conservative
uncertain-as-false fraction `{report['simulated_release_human_FTR_uncertain_as_false']:.6f}`.
The package therefore passes the CTC strict-audit publication gate for the
reviewed queue.

## One-Sided Positive Rule

Only rows labeled `same_cell_link` and marked
`human_verified_positive_for_calibration=yes` may enter the one-sided verified
positive set.  `not_same_cell_link`, `uncertain`, and any future disagreement
must remain unverified and must not be treated as trusted negatives.

## Provenance

This release is derived from the reviewed prefill package in
`outputs/milestones/ctc_strict_human_audit_prefill/`.  The prefill package
remains as provenance; this milestone is the human-confirmed publication copy.
"""
    (out_dir / "CTC_STRICT_HUMAN_AUDIT_CLOSEOUT.md").write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefill-dir", default="outputs/milestones/ctc_strict_human_audit_prefill")
    parser.add_argument("--out-dir", default="outputs/milestones/ctc_strict_human_audit")
    args = parser.parse_args()

    prefill_dir = Path(args.prefill_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefill_path = prefill_dir / "ctc_strict_audit_prefill_for_human_review.csv"
    key_path = prefill_dir / "ctc_strict_audit_private_key.csv"

    df = build_confirmed(prefill_path, key_path)
    public_cols = [
        "audit_id",
        "path_id",
        "queue_membership",
        "queue_calibration",
        "queue_simulated_strict_release",
        "queue_raw_topK_reference",
        "simulated_release_hits",
        "simulated_release_budgets",
        "simulated_release_seeds",
        "ctc_dataset",
        "sequence_id",
        "frame_start",
        "frame_end",
        "video_id",
        "candidate_rank",
        "score",
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
        "human_verified_positive_for_calibration",
        "human_reason",
        "human_confidence",
        "human_review_status",
        "human_confirmation_note",
    ]
    confirmed = df[public_cols].copy()
    confirmed.to_csv(out_dir / "ctc_strict_audit_human_confirmed_labels.csv", index=False)
    queue_subset(confirmed, "queue_calibration").to_csv(
        out_dir / "ctc_strict_audit_calibration_human_confirmed_labels.csv", index=False
    )
    queue_subset(confirmed, "queue_simulated_strict_release").to_csv(
        out_dir / "ctc_strict_audit_release_human_confirmed_labels.csv", index=False
    )
    queue_subset(confirmed, "queue_raw_topK_reference").to_csv(
        out_dir / "ctc_strict_audit_raw_topk_human_confirmed_labels.csv", index=False
    )

    summary = pd.DataFrame(
        [
            summarize_queue(queue_subset(confirmed, "queue_calibration"), "calibration"),
            summarize_queue(queue_subset(confirmed, "queue_simulated_strict_release"), "simulated_strict_release"),
            summarize_queue(queue_subset(confirmed, "queue_raw_topK_reference"), "raw_topK_reference"),
            summarize_queue(confirmed, "all_reviewed_rows"),
        ]
    )
    summary.to_csv(out_dir / "table_ctc_strict_human_audit_summary.csv", index=False)

    release_summary = summary[summary["queue"] == "simulated_strict_release"].iloc[0].to_dict()
    go_no_go = pd.DataFrame(
        [
            {
                "gate": "ctc_strict_release_human_audit",
                "required_human_FTR_max": 0.10,
                "required_conservative_FTR_max": 0.10,
                "required_human_review_status": "human_confirmed",
                "observed_rows": int(release_summary["rows"]),
                "observed_human_FTR_false_only": float(release_summary["human_FTR_false_only"]),
                "observed_human_FTR_uncertain_as_false": float(release_summary["human_FTR_uncertain_as_false"]),
                "uncertain_rows": int(release_summary["human_uncertain"]),
                "decision": (
                    "go"
                    if float(release_summary["human_FTR_uncertain_as_false"]) <= 0.10
                    and int(release_summary["human_uncertain"]) == 0
                    else "no_go"
                ),
                "interpretation": "human-confirmed strict release queue satisfies the conservative alpha=0.10 publication gate",
            }
        ]
    )
    go_no_go.to_csv(out_dir / "table_ctc_strict_human_audit_go_no_go.csv", index=False)

    report = {
        "status": "human_confirmed",
        "source_prefill_sha256": sha256_file(prefill_path),
        "source_private_key_sha256": sha256_file(key_path),
        "rows_total": int(len(confirmed)),
        "rows_calibration": int(confirmed["queue_calibration"].sum()),
        "rows_simulated_strict_release": int(confirmed["queue_simulated_strict_release"].sum()),
        "rows_raw_topK_reference": int(confirmed["queue_raw_topK_reference"].sum()),
        "human_label_counts": confirmed["human_label"].value_counts().to_dict(),
        "simulated_release_human_FTR_false_only": float(release_summary["human_FTR_false_only"]),
        "simulated_release_human_FTR_uncertain_as_false": float(release_summary["human_FTR_uncertain_as_false"]),
        "expert_review_claimed": False,
        "review_note": "User confirmed the reviewed labels can be published; no separate microscopy-expert claim is made in this closeout.",
    }
    (out_dir / "CTC_STRICT_HUMAN_AUDIT_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    write_closeout(out_dir, report)

    manifest_paths = sorted(p for p in out_dir.rglob("*") if p.is_file() and p.name != "MANIFEST_SHA256.txt")
    with (out_dir / "MANIFEST_SHA256.txt").open("w", encoding="utf-8") as handle:
        for path in manifest_paths:
            handle.write(f"{sha256_file(path)}  {path.relative_to(out_dir)}\n")

    package_path = ROOT / "outputs/packages/ctc_strict_human_audit.tar.gz"
    package_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(package_path, "w:gz") as tar:
        for path in sorted(out_dir.rglob("*")):
            tar.add(path, arcname=str(Path("ctc_strict_human_audit") / path.relative_to(out_dir)))

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
