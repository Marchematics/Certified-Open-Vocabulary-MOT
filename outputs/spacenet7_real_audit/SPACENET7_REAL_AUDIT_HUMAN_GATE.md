# SpaceNet 7 K=50 Human-Audit Gate

Human labels complete: `False`.

Human gate decision: **NO_GO_REQUIRES_HUMAN_VISUAL_CONFIRMATION**.

Metadata-proxy gate decision: **PROVISIONAL_GO**.

The diagnostic K=50 release set has 147 candidates. The metadata/official-proxy review has FTR 0.000, but the `human_*` fields are not yet completed, so this row remains provisional and cannot be reported as a paper-facing human-audited FTR.

To close the gate, fill `human_label`, `human_verified_positive_for_calibration`, `human_reason`, `human_confidence`, and `human_review_status=human_confirmed` in `release_audit_review_prefill.csv`, then rerun `python scripts/evaluate_spacenet7_human_audit_gate.py`.
