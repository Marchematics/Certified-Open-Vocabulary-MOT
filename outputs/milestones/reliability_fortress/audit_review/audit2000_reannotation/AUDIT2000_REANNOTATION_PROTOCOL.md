# Audit2000 Blind Reannotation Protocol

This template supports a genuine independent reannotation of the full Audit2000 benchmark. The purpose is to measure agreement, not to tune agreement into any target interval.

## Reviewer fields

Fill only these columns:

- `second_reviewer_label`: `actually_true`, `actually_false`, or `uncertain`.
- `second_reviewer_verified_positive_for_calibration`: `yes` only for high-confidence `actually_true`; `uncertain` must be `no`.
- `second_reviewer_reason`: short visual reason.
- `second_reviewer_confidence`: `high`, `medium`, or `low`.
- `review_status`: `human_confirmed` when complete.

## Reporting rule

After completion, compute label agreement, verified-positive agreement, and Cohen's kappa against the primary human-reviewed Audit2000 labels. Report the observed values exactly. Do not adjust labels to target any desired kappa range.

## Recommended paper framing

Audit2000 measures large-scale audit coverage. The boundary challenge measures hard-case ambiguity. The full reannotation template is provided for independent reproducibility and can be used to report a full-dataset agreement study once completed.
