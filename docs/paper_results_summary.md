# PARC-Track Release Results Summary

This is the release-facing index for the public repository. Earlier phase
summaries are preserved only as historical provenance; the authoritative
artifacts are the final release directories below.

## Authoritative Public Artifacts

- Reliability fortress milestone:
  `outputs/milestones/reliability_fortress/`
- Generality and reliability milestone:
  `outputs/milestones/generality_reliability/`
- Community benchmark package:
  `outputs/benchmarks/parc_certification_benchmark/`
- Legacy evidence ledger:
  `outputs/milestones/legacy_core_results/`
- Root integrity manifest:
  `MANIFEST_SHA256.txt`

## Main Evidence Blocks

1. **Audit2000 benchmark.**
   The release contains 2,000 human-reviewed audit rows:
   `1,927 actually_true`, `33 actually_false`, and `40 uncertain`.
   The independent second-review file contains 300 rows with Cohen's kappa
   `0.9917` and verified-positive agreement `1.0000`.

2. **Certified OVMOT release results.**
   OVT-B, TAO, and BURST certification and refusal results are frozen in
   `table_blackbox_generator_certification.csv`, `table_published_tracker_certification.csv`,
   and the legacy cross-dataset tables under `legacy_core_results/`.

3. **Reliability stress tests.**
   Non-exchangeability and null-inflation reruns are frozen in:
   `table_nonexchangeability_severe_actual_results.csv`,
   `table_nonexchangeability_stress_results.csv`,
   `table_null_inflation_empirical.csv`, and
   `table_null_inflation_verified_removal_actual_results.csv`.

4. **Generality evidence.**
   LVIS detection certification, OVVIS box-to-mask certification, and
   stratified reliability tables are frozen under
   `outputs/milestones/generality_reliability/`.

5. **System diagnostics.**
   Runtime, anytime release, Mondrian granularity, per-class breakdown, and
   Prop. 5 high-evidence mass diagnostics are frozen under
   `outputs/milestones/reliability_fortress/`.

## Tracking Metrics And IDSW Scope

The release includes empirical TrackEval/HOTA/IDF1/MOTA-style metric exports
and metric-scope diagnostics in the legacy ledger. CLEAR-MOT IDSW certificate
derivations remain a theoretical/API extension and are not presented as the
main empirical certification claim in this release.

## Reproduction Notes

The public repository intentionally excludes raw videos, raw annotations,
model weights, frame caches, montage images, and detector caches. Use
`REPRODUCIBILITY.md`, `DATA_AVAILABILITY.md`, and `CODE_AVAILABILITY.md` for
the end-to-end public workflow.
