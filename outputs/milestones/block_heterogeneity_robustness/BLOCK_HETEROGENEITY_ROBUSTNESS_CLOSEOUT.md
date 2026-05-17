# Block Heterogeneity Robustness Closeout

Evidence status: mixed completed diagnostic.

This milestone addresses whether heterogeneous block sizes could make block
maxima incomparable. It does not modify the manuscript text. It separates
candidate-level reruns from aggregate or audit-sample diagnostics.

## Completed Candidate-Level Evidence

- Materials/WBM has public-safe candidate IDs, block assignments, scores and
  DFT labels available locally, so Phase25 runs actual candidate-level
  size-matched and downsampled block-max stress tests for CGCNN/ALIGNN rows.
- `table_size_matched_rerun.csv` reports strict/medium/loose log-size matched
  calibration variants plus the original global calibration on 10 diagnostic
  seeds.
- `table_downsampled_blockmax_stress.csv` reports fixed-size null-superset
  downsampling at m in {10, 25, 50, 100} with 20 repeats on 5 representative
  diagnostic seeds.

## Scoped Diagnostics

- SpaceNet contributes an audit-sample p-value screen and completed real-audit
  K=100 refusal diagnostics. The audit sample contains few false links, so the
  p-value screen is explicitly underpowered.
- CTC public artifacts contain aggregate learned-source release tables but not
  candidate-level block-max artifacts. The CTC row is therefore marked as
  aggregate-only in this milestone; no size-matched rerun is fabricated.

## Interpretation

The materials candidate-level stresses show that block-size comparability can
change power near the boundary, but the diagnostics do not create a hidden
unsafe release claim. Rows either retain their qualitative release/refusal
pattern or are marked as boundary/power-loss diagnostics. Where candidate-level
artifacts are absent, the milestone records that limitation directly.

## Main Artifacts

- `table_block_size_heterogeneity_summary.csv`
- `figure_block_size_superuniformity.csv`
- `figure_block_size_superuniformity.pdf`
- `table_size_matched_rerun.csv`
- `table_size_matched_rerun_seed_rows.csv`
- `table_downsampled_blockmax_stress.csv`
- `table_downsampled_blockmax_stress_seed_rows.csv`
- `B2_APPROXIMATE_EVALUE_VALIDITY_LEMMA.md`

## Domain Summary

| domain                   |   superuniformity_rows |   size_matched_rows |   downsampled_rows | evidence_status                       | primary_conclusion                                                                                                                   |
|:-------------------------|-----------------------:|--------------------:|-------------------:|:--------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------|
| materials_discovery      |                      3 |                  12 |                  8 | candidate_level_completed             | size-matched and downsampled reruns retain release/refusal pattern or expose conservative power changes                              |
| biomedical_cell_tracking |                      0 |                   1 |                  0 | aggregate_only_public_package         | CTC learned strict row remains stable in completed aggregate evidence; candidate-level size-matched rerun requires raw link universe |
| earth_observation        |                      1 |                   1 |                  0 | audit_sample_and_aggregate_diagnostic | real-audit K100 remains refusal; audit-sample superuniformity screen is underpowered and not a release claim                         |
