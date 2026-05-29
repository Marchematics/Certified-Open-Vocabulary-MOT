# Phase78 CTC Real One-Sided Audit Integration

Status: `completed_CTC_real_one_sided_audit_integration`.

This milestone integrates the existing CTC strict human-confirmed audit package
into the NCS release-card lifecycle story. It does not create new labels.

Evidence boundary:

- supports PARC-A as the primary empirical positive;
- use `trained human review` or `human-confirmed one-sided audit`;
- do not claim microscopy-expert adjudication unless separately documented;
- do not claim a new CTC benchmark, materials evidence or DFT evidence;
- `same_cell_link` rows may enter the one-sided positive set;
- `not_same_cell_link`, `uncertain` and any future disagreement must remain
  unverified and must not be treated as trusted negatives.

Source package:

- `outputs/milestones/ctc_strict_human_audit/ctc_strict_audit_human_confirmed_labels.csv`;
- source status: `human_confirmed`;
- expert review claimed: `False`.
