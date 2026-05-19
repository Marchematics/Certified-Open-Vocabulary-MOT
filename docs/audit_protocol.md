# Human Audit Protocol

This document gives the repository-level audit rules used by the public PARC
release package.  Domain-specific protocols live beside their corresponding
milestones and should be treated as the source of truth for row-level details.

## Label Vocabulary

Use three labels unless a domain protocol states otherwise:

- `actually_true` / `same_cell_link` / domain-positive label: the candidate is
  a valid target under the domain definition.
- `actually_false` / `not_same_cell_link` / domain-negative label: the
  candidate is background, wrong identity, wrong semantic target, or otherwise
  invalid.
- `uncertain`: the evidence is insufficient, ambiguous, heavily occluded, or
  outside the reviewer competence boundary.

Uncertain is a first-class label.  Do not force binary decisions when the visual
or domain evidence is weak.

## Verified-Positive Rule

PARC uses one-sided verified positives.  A row can enter the verified-positive
set only when it is confirmed positive under the domain protocol.

- Positive and high-confidence: `verified_positive_for_calibration=yes`.
- False, uncertain, or disputed: `verified_positive_for_calibration=no`.
- Negative rows must not be treated as trusted negatives unless a separate
  experiment explicitly has full labels.

This rule preserves the one-sided assumption `A=1 => Y=1`.

## Second Review and Disagreement Handling

When a second reviewer is used:

1. Reviewers should be blind to method, score, release status, seed, and first
   reviewer label whenever possible.
2. Disagreements are not overwritten silently.
3. Positive status requires consensus or documented adjudication.
4. Disagreement, uncertainty, and adjudication tables should be retained in the
   milestone.

For expert-sensitive domains, such as microscopy mitosis or dense-overlap
cases, domain-expert adjudication is recommended before claiming expert review.

## Release-Audit Subsets

Release-audit labels evaluate released candidates.  They must not be fed back
into calibration unless a new prospective protocol explicitly predeclares that
workflow.  Calibration audit labels and release audit labels should be stored in
separate files.

## Public-Safe Anonymization

Public audit CSVs may include candidate IDs, dataset names, frame indices, box
coordinates, and derived scores.  They must not include raw videos, raw images,
raw annotation files, private local paths, model weights, caches, or montage
images.  If visual inspection assets are required, provide a manifest rather
than redistributing the underlying raw data.

## Current Audit Milestones

- `outputs/milestones/reliability_fortress/audit_review/`
- `outputs/milestones/ctc_strict_human_audit/`
- `outputs/milestones/scientific_domain_iwildcam_human_audit/`
- `outputs/milestones/spacenet_real_audit_final/`
