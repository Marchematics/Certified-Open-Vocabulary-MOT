# SpaceNet 7 Real-Audit Closeout

This closeout completes the three immediate diagnostics requested after the real-audit loop.

## 1. K=50 Diagnostic Release Audit

`table_spacenet7_real_audit_k50_completed_summary.csv` summarizes the 147 diagnostic release candidates. The current label source is metadata/official-proxy review and remains pending human visual confirmation.

## 2. Calibration Block Coverage and Reliability Status

`table_spacenet7_real_audit_block_coverage.csv` and `table_spacenet7_real_audit_block_coverage_summary.csv` report calibration coverage over AOI-time blocks. Second-review reliability is explicitly marked as requiring independent human review; metadata agreement is not reported as human kappa.

## 3. K=100 Refusal Diagnostics

`table_spacenet7_real_audit_k100_evalue_failure_by_seed.csv` and `table_spacenet7_real_audit_k100_failure_summary.csv` show that primary K=100 refuses because high-evidence mass is below the SCS threshold in every seed.

## Go/No-Go

- K=100 primary SpaceNet real-audit positive deployment: **NO-GO**.
- K=100 as certified-refusal operating check: **GO**.
- K=50 diagnostic low-volume release: **PROVISIONAL GO**, pending human visual confirmation.
- Block-stratified audit expansion: only needed if human review invalidates K=50 or if a K=100 positive real-audit row is required.
