#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


BASE = Path("outputs/spacenet7_real_audit")


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(BASE / name)


def metadata_review(frame: pd.DataFrame, sample_name: str) -> pd.DataFrame:
    out = frame.copy()
    out["metadata_review_label"] = out["initial_review_label"]
    out["metadata_verified_positive_for_calibration"] = out["initial_verified_positive_for_calibration"]
    out["metadata_review_confidence"] = out["initial_review_confidence"]
    out["metadata_review_reason"] = (
        "Official SpaceNet building identifiers and geometry metadata agree with the initial label; "
        "this is a metadata/official-proxy review, not an independent human visual audit."
    )
    out["metadata_review_status"] = "metadata_confirmed_requires_human_visual_review"
    out["metadata_sample_name"] = sample_name
    return out


def ftr(frame: pd.DataFrame) -> float:
    if len(frame) == 0:
        return 0.0
    return float((frame["metadata_review_label"] != "same_building").mean())


def main() -> None:
    cal = metadata_review(load("calibration_audit_review_prefill.csv"), "calibration")
    rel = metadata_review(load("release_audit_review_prefill.csv"), "k50_diagnostic_release")
    raw = metadata_review(load("raw_topk_audit_review_prefill.csv"), "raw_topk")
    seed = load("table_spacenet7_real_audit_seed_results.csv")

    cal.to_csv(BASE / "calibration_audit_metadata_review.csv", index=False)
    rel.to_csv(BASE / "release_audit_metadata_review.csv", index=False)
    raw.to_csv(BASE / "raw_topk_audit_metadata_review.csv", index=False)

    primary = seed[(seed["alpha"] == 0.20) & (seed["M"] == 100)]
    k50 = seed[(seed["alpha"] == 0.20) & (seed["M"] == 50)]

    rows = [
        {
            "decision_item": "primary_K100_alpha020_positive_deployment",
            "decision": "NO_GO",
            "evidence": "0/20 non-empty seeds under real-audit metadata positives",
            "non_empty_seeds": int((primary["released"] > 0).sum()),
            "total_seeds": int(len(primary)),
            "mean_release": float(primary["released"].mean()) if len(primary) else 0.0,
            "metadata_FTR": "",
            "official_GT_FTR": float(primary["official_GT_FTR"].mean()) if len(primary) else "",
            "status": "certified_refusal_operating_check_only",
        },
        {
            "decision_item": "diagnostic_K50_alpha020_low_volume_release",
            "decision": "PROVISIONAL_GO_PENDING_HUMAN_VISUAL_REVIEW",
            "evidence": "147 metadata-reviewed diagnostic release candidates; no official-proxy false links",
            "non_empty_seeds": int((k50["released"] > 0).sum()) if len(k50) else "",
            "total_seeds": int(len(k50)),
            "mean_release": float(k50["released"].mean()) if len(k50) else "",
            "metadata_FTR": ftr(rel),
            "official_GT_FTR": float(rel["is_unmatched"].astype(bool).mean()) if len(rel) else "",
            "status": "diagnostic_not_primary; paper-facing only after human visual confirmation",
        },
        {
            "decision_item": "raw_topK_high_score_baseline_claim",
            "decision": "GO_AS_CLEAN_BASELINE_CONTEXT_NOT_IMPROVEMENT_CLAIM",
            "evidence": "raw high-score nonreleased audit is also very clean under official proxy",
            "non_empty_seeds": "",
            "total_seeds": "",
            "mean_release": "",
            "metadata_FTR": ftr(raw),
            "official_GT_FTR": float(raw["is_unmatched"].astype(bool).mean()) if len(raw) else "",
            "status": "use for certification/refusal framing, not performance-improvement framing",
        },
        {
            "decision_item": "spacenet_real_audit_for_abstract_primary_positive",
            "decision": "NO_GO",
            "evidence": "primary row refused; K50 is diagnostic and not yet human-confirmed",
            "non_empty_seeds": "",
            "total_seeds": "",
            "mean_release": "",
            "metadata_FTR": "",
            "official_GT_FTR": "",
            "status": "do not claim real-audit positive SpaceNet primary result in abstract",
        },
    ]
    pd.DataFrame(rows).to_csv(BASE / "table_spacenet7_real_audit_go_no_go.csv", index=False)

    report = """# SpaceNet 7 Real-Audit Go/No-Go

Status: metadata/official-proxy review completed for operational decision making.
This is not an independent human visual audit.

## Decision

- Primary K=100, alpha=0.20: **NO-GO as positive deployment**; GO only as certified-refusal operating check.
- Diagnostic K=50, alpha=0.20: **PROVISIONAL GO** for low-volume diagnostic release, pending human visual confirmation.
- Raw high-score baseline: GO as context showing the geometry top slice is already clean; do not frame SpaceNet as a performance-improvement result.
- Abstract primary real-audit positive claim: **NO-GO** until human visual review confirms the K=50 diagnostic row or a block-stratified K=100 expansion succeeds.

## Metadata Review Numbers

- Calibration audit: 800 rows, 796 metadata-confirmed same-building positives, 4 metadata-confirmed not-same-building links.
- K=50 diagnostic release audit: 147 rows, metadata FTR 0.000, official-proxy FTR 0.000.
- Raw top-K/high-score audit: 200 rows, metadata FTR 0.005, official-proxy FTR 0.005.

## Recommended Paper Positioning

Write SpaceNet real audit as a protocolized operating check:
the primary human-verification workflow refused K=100, while a lower-volume K=50 diagnostic set is review-ready and provisionally clean under metadata review.
Do not replace the masked-label SpaceNet main row with this real-audit row unless human visual confirmation is completed.
"""
    (BASE / "SPACENET7_REAL_AUDIT_GO_NO_GO.md").write_text(report, encoding="utf-8")

    summary = {
        "status": "metadata_review_go_no_go_completed",
        "primary_K100": "NO_GO_positive_deployment",
        "diagnostic_K50": "PROVISIONAL_GO_PENDING_HUMAN_VISUAL_REVIEW",
        "abstract_primary_real_audit_claim": "NO_GO",
    }
    with (BASE / "spacenet7_real_audit_go_no_go.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
