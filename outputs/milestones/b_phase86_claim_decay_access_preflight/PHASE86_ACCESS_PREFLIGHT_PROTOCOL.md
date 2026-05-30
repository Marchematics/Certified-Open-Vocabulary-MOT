# Phase86 Access Preflight Protocol

Phase86 follows Phase85 and precedes any claim-decay computation.

Allowed outputs:

- source endpoint reachability smoke;
- local dependency inventory;
- Materials Project database version if query succeeds;
- empty claim-registry and current-reference query templates;
- ingest preflight plan.

Forbidden outputs:

- SCDR, TDB@100, EDMB, CAR or any source-specific claim-decay result;
- statement that a source's public AI claims fail current references;
- legal approval to redistribute third-party raw structures;
- A-paper main evidence;
- new DFT evidence.

Evidence scope: `b_line_claim_decay_access_preflight;source_access_smoke_only;claim_registry_empty;current_reference_verdicts_pending;not_completed_positive_evidence;not_A_paper_main_evidence;not_prospective_discovery;not_new_DFT_evidence`.
