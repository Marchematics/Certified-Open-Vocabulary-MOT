# Phase90 Protocol: GNoME Raw-Structure Ingest

Inputs:

- frozen registry: `outputs/milestones/b_phase87_minimal_claim_registry/table_phase87_minimal_claim_registry.csv`;
- raw cache outside version control: `cache/b_phase89/gnome/by_id.zip`;
- Phase89 readiness plan: `outputs/milestones/b_phase89_exact_structure_audit_readiness/table_phase89_exact_match_execution_plan.csv`.

Procedure:

1. Select only `gnome_public_stable_materials` rows from the frozen registry.
2. For each material ID, read `by_id/<material_id>.CIF` from the local zip.
3. Hash the raw CIF bytes and parse with pymatgen.
4. Write only derived metadata and hashes.
5. Do not query Materials Project current-reference labels in this phase.

This phase is a necessary ingest step for B-line exact-structure claim-decay
auditing, but it is not claim-decay evidence.
