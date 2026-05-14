# SpaceNet 7 Real-Audit Go/No-Go

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
