# Boundary-Challenge Audit Protocol

This 500-row challenge is designed to measure annotation ambiguity in hard cases, not to tune agreement to a target value.

## Sampling principle

The template oversamples visually difficult and decision-boundary paths from the Audit2000 pool: previous uncertain/false neighborhoods, low/medium-confidence rows, small/tiny objects, partial boxes, category-boundary cases, temporal fragments, and released-unsupported boundary examples. The blind template intentionally omits primary labels and source reasons.

## Label fields

The independent reviewer should fill:

- `second_reviewer_label`: `actually_true`, `actually_false`, or `uncertain`.
- `second_reviewer_verified_positive_for_calibration`: `yes` only for high-confidence actually-true paths; `uncertain` must be `no`.
- `second_reviewer_reason`: short visual reason.
- `second_reviewer_confidence`: `high`, `medium`, or `low`.
- `review_status`: `human_confirmed` once complete.

## Reporting rule

Report the observed agreement and Cohen's kappa as measured. Do not alter labels to target a desired kappa range. If kappa is high, explain that the protocol remains deterministic even on hard cases; if moderate, report the ambiguity honestly.
