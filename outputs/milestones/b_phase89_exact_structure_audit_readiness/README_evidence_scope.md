# Phase89 Exact-Structure Audit Readiness

Status: `readiness_and_protocol_only_current_verdicts_pending`.

Phase89 prepares the B-line exact-structure audit. The default command performs
readiness checks and writes ingestion/matching/adjudication plans. It does not
download raw structures unless `--download-gnome-zip` is explicitly provided.

Raw GNoME structures are intentionally cached under `cache/` and excluded from
git. Public artifacts contain only manifests, derived hashes when available,
and guardrails.

Evidence scope: `b_line_exact_structure_audit_readiness;readiness_and_protocol_only;raw_structure_cache_not_versioned;current_reference_verdicts_pending;not_completed_positive_evidence;not_A_paper_main_evidence;not_prospective_discovery;not_new_DFT_evidence`.
