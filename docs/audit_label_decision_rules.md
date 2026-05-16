# Audit Label Decision Rules

This document gives compact label rules for human audit files. It complements `docs/audit_protocol.md`.

## Core labels

- `actually_true`: the candidate satisfies the release target under the task-specific visual or scientific definition.
- `actually_false`: the candidate does not satisfy the release target.
- `uncertain`: the evidence is insufficient, ambiguous, or outside the audit protocol.

## Verified-positive status

Only high-confidence positives may receive verified-positive status.

- `actually_true` can be verified only when the reviewer can support the target claim directly.
- `actually_false` is never verified positive.
- `uncertain` is never verified positive.
- Disagreements are not verified positive unless a documented adjudication resolves them as positive.

## One-sided rule

PARC uses audit positives as one-sided evidence. The intended invariant is:

```text
verified_positive = true implies target_true = true
```

The repository therefore treats false, uncertain, and unresolved rows as unverified rather than as trusted negatives.

## Task-specific examples

- **Cell link:** same cell or valid lineage link across adjacent frames.
- **Building link:** same building identity across adjacent months.
- **Animal detection:** bounding box contains an animal under the animal-present target.
- **Materials candidate:** candidate is stable under the documented DFT-derived target.
- **Open-vocabulary path:** candidate path is a valid object trajectory under the audit protocol.

## Conservative reporting

When reporting release FTR, uncertain rows should be reported separately and, when needed, counted conservatively as false in a companion diagnostic.
