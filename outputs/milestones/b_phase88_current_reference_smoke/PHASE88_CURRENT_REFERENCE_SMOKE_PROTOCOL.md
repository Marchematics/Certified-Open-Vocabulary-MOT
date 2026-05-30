# Phase88 Low-Cost Current-Reference Smoke Protocol

Input registry:

- `outputs/milestones/b_phase87_minimal_claim_registry/table_phase87_minimal_claim_registry.csv`

Reference smoke route:

- WBM rows are joined to `outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t0_t1_label_join.csv` by WBM material id.
- GNoME rows are not queried in this low-cost phase because summary rows do not
  provide raw structures for exact matching.
- OQMD is not queried in this phase.

Decision boundary:

This phase is designed only to decide whether B should proceed to a stronger
exact-structure audit. It is not a paper-facing claim-decay result.
