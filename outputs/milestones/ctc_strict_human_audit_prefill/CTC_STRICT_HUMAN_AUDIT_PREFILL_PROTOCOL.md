# CTC Strict Human Audit Prefill Protocol

## Status

This package prepares a CTC learned-hybrid strict-audit review queue.  It is a
prefill package, not a completed human audit.  Paper-facing `human_*` fields
must remain empty until a reviewer confirms or edits the labels.

## Review Task

For each row, inspect the source crop at frame `t` and target crop at frame
`t+1` and label the candidate link as:

- `same_cell_link`: the source and target boxes correspond to the same cell
  identity across adjacent frames.
- `not_same_cell_link`: the target box corresponds to a different cell,
  background/artifact, or an impossible continuation.
- `uncertain`: the pair is too ambiguous because of overlap, mitosis,
  low contrast, crop truncation, or insufficient visual evidence.

Only confirmed `same_cell_link` rows may be used as one-sided verified
positives.  `not_same_cell_link`, `uncertain`, and disagreements remain
unverified and must never be used as trusted negatives.

## Files

- `ctc_strict_audit_blind_template.csv`: blinded review sheet. It omits path
  IDs, scores, release/calibration strata, and GT-derived screening labels.
- `ctc_strict_audit_prefill_for_human_review.csv`: review sheet with screening
  suggestions and traceability fields for rapid confirmation.
- `ctc_strict_audit_private_key.csv`: audit ID to path ID mapping and queue
  membership. Keep separate from a strict blind reviewer.
- `table_ctc_strict_audit_prefill_summary.csv`: package counts.

## Expert Requirement

Expert microscopy review is strongly recommended for a NMI flagship claim, but
it is not logically mandatory for every row.  A trained independent reviewer can
review ordinary same-cell continuation cases if the protocol uses conservative
rules and held-out official CTC ground truth remains available only for final
evaluation.  However, expert or microscopy-experienced adjudication should be
used for mitosis, dense overlaps, low-contrast cells, segmentation ambiguity,
and any row marked `uncertain` or disputed by reviewers.

If expert review is not completed, phrase the result as `trained independent
human review`, not `expert audit`.

## Package Counts

- total rows: 2564
- calibration queue rows: 1500
- simulated strict-release queue rows: 1064
- raw top-K reference rows: 300
- screening label counts: `{"not_same_cell_link": 45, "same_cell_link": 2519}`

## Predeclared Simulation Context

- learned-hybrid source: sequence-disjoint CTC appearance/geometry scorer
- release simulation used only to define candidate queues
- alpha: 0.1
- rho: 0.1
- release budgets: 100,300
- seeds: 0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19

The real-audit release trial must rerun PARC using confirmed human positives;
release-audit labels must not be fed back into calibration.
