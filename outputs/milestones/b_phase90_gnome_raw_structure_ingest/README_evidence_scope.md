# Phase90 GNoME Raw-Structure Ingest

Status: `derived_structure_ingest_completed_current_verdicts_pending`.

Phase90 reads the local GNoME `by_id.zip` cache and extracts only derived,
public-safe structure metadata for the frozen B-line 150-row GNoME registry.
It does not write raw CIF files into git-tracked artifacts.

Summary:

- registry rows: `150`;
- raw CIF members present in local cache: `150`;
- pymatgen-parsed structures: `150`;
- current-reference verdicts: pending;
- exact MP structure matching: pending.

Allowed current claim:

Phase90 completes derived raw-structure ingest for the frozen GNoME registry and
prepares the next exact-matching stage.

This is not claim-decay evidence.

Forbidden current claims:

- completed exact-structure matching;
- source-level claim decay;
- GNoME current-reference instability;
- A-paper evidence;
- prospective discovery;
- new DFT evidence.

Evidence scope: `b_line_gnome_raw_structure_ingest;derived_metadata_only;raw_cif_not_versioned;exact_matching_pending;current_reference_verdicts_pending;not_claim_decay_evidence;not_A_paper_main_evidence;not_prospective_discovery;not_new_DFT_evidence`.
