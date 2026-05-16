# Audit Disagreement Policy

This policy describes how disagreements are handled in audit-derived public artifacts.

## Reviewer independence

When a second review is used, the reviewer should not see the first-review label, release status, score, seed, or method condition. If a review is not independent, the artifact must say so.

## Disagreement categories

- `confirmed_disagreement`: reviewers assign incompatible labels after review.
- `confirmed_no_disagreement`: reviewers agree after independent review or adjudication.
- `pending_human_review`: the row has not yet completed the required review stage.
- `adjudicated_positive`: disagreement was resolved as a verified positive by documented adjudication.
- `adjudicated_unverified`: disagreement remains false, uncertain, or unresolved for PARC purposes.

## PARC input rule

Disagreement rows must not enter the verified-positive set unless they are explicitly adjudicated as positive. This protects the one-sided reliability assumption.

## Reporting

Public tables should report:

- reviewed row count;
- number and fraction of disagreements;
- Cohen's kappa or an explanation when kappa is not meaningful;
- uncertain count;
- verified-positive count after disagreement handling;
- whether the review is full, stratified, or release-subset-only.

## Release-audit rows

Release-audit rows are used to estimate audited FTR and must not be fed back into calibration unless a new predeclared run explicitly treats them as calibration audit positives.

## Conservative defaults

If disagreement status is missing, the row is treated as unverified. If uncertainty is material to the result, report both false-only FTR and uncertain-as-false FTR.
