# Phase81 CTC External Blind One-Sided Audit Mini-Study Protocol

Status: `packet_frozen_pending_independent_labels`.

Objective: convert the PARC-A CTC active-verification result from masked-label
emulation toward a real verification-workflow mini-study.  Two independent
auditors receive blinded link-pair review templates and label each row as:

- `same_cell_supported`;
- `unsupported`;
- `uncertain`.

Only `same_cell_supported` can be used as one-sided verified support.  Unsupported
or uncertain labels are not trusted negatives for PARC calibration.

Frozen packet:

- packet rows: 600;
- randomized item IDs: `CTC-PHASE81-0001` ... `CTC-PHASE81-0600`;
- templates: `external_blind_auditor_A_template.csv` and
  `external_blind_auditor_B_template.csv`;
- adjudication template: `external_blind_adjudication_template.csv`.

Important limitation: the current tracked Phase78 source package does not
contain a true raw-only top-K arm.  All tracked raw-topK reference rows overlap
the simulated strict-release queue.  Therefore this packet includes a
raw-topK-overlap reference control and records true raw-only as a blocker until
the full CTC candidate universe is restored or regenerated.

Current evidence boundary:

- this is not completed positive evidence;
- do not claim expert microscopy adjudication;
- do not claim raw-only comparator success;
- do not claim a new CTC ground-truth benchmark;
- do not use this as materials or DFT evidence.
