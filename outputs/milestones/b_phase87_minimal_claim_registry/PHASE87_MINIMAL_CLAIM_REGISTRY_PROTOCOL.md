# Phase87 Minimal Claim Registry Protocol

Allowed current output:

- frozen two-source minimal claim registry;
- source-level ingest summary;
- current-reference query manifest with pending verdicts.

Forbidden current output:

- SCDR, TDB@100, EDMB, CAR, or any claim-decay metric;
- claim that public AI materials claims fail current references;
- exact structure matching completeness;
- redistribution of raw structures from third-party sources;
- A-paper main evidence;
- prospective discovery or new DFT evidence.

Next step:

Phase88 may query current MP/OQMD references using the frozen registry.  It
must not alter Phase87 claim ontology after seeing current-reference verdicts.

Evidence scope: `b_line_minimal_claim_registry;two_primary_sources;claim_registry_frozen;current_reference_verdicts_pending;not_completed_positive_evidence;not_A_paper_main_evidence;not_prospective_discovery;not_new_DFT_evidence`.
