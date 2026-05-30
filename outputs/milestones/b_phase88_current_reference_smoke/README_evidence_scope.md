# Phase88 Current-Reference Smoke

Status: `low_cost_smoke_completed_not_claim_decay`.

Phase88 is a low-cost B-line smoke test. It reuses the frozen Phase87 registry
and the existing WBM t0/t1 local join. It does not perform live MP/OQMD queries,
does not ingest GNoME raw structures, and does not perform exact-structure
matching.

Allowed claim:

- WBM registry rows have existing-snapshot current-reference smoke verdicts.
- GNoME rows remain pending until raw structure ingest or a permitted exact
  matching route is implemented.

Forbidden claims:

- exact-structure claim decay;
- source-level SCDR/TDB/EDMB/CAR;
- GNoME or OQMD current-reference verdicts;
- A-paper evidence;
- prospective discovery or new DFT evidence.

Evidence scope: `b_line_current_reference_smoke;low_cost_existing_snapshot_join;formula_or_id_level_only;not_exact_structure_claim_decay;not_completed_positive_evidence;not_A_paper_main_evidence;not_prospective_discovery;not_new_DFT_evidence`.
