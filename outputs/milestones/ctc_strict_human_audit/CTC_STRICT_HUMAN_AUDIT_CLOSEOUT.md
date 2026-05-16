# CTC Strict Human Audit Closeout

## Status

The CTC learned-hybrid strict-audit package has been reviewed and confirmed by
the project reviewer.  The `human_*` fields in this milestone are the
paper-facing labels for this audit package.

This closeout does not claim microscopy-expert adjudication unless such an
expert review is separately documented.  If no domain expert reviewed the rows,
paper wording should use `trained human review` or `human-confirmed review`,
not `expert audit`.

## Label Summary

- total audited rows: 2564
- calibration queue rows: 1500
- simulated strict-release queue rows: 1064
- raw top-K reference rows: 300
- same-cell labels: 2519
- not-same labels: 45
- uncertain labels: 0

## Release-Audit Gate

The simulated strict-release queue has human false-link fraction
`0.000000` and conservative
uncertain-as-false fraction `0.000000`.
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
