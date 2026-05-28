# NCS Week 0 Protocol Freeze

Freeze timestamp: `2026-05-28T18:43:21+08:00`

Repository commit at freeze build time: `25aa6fa`

## Status

This milestone is a preregistration/protocol-freeze package only. It creates no
new scientific evidence, no DFT outcome, no prospective materials-discovery
claim, and no positive independent materials validation claim. OSF/Zenodo upload
is prepared but not represented as completed in this repository.

Boundary summary: no DFT outcome; no prospective materials-discovery claim; no
positive independent materials validation claim.

## Frozen Objects

- Candidate universes and release selections are frozen in
  `table_frozen_candidate_universe.csv`.
- Model scores are frozen in `table_frozen_model_scores.csv`.
- PARC parameters, K/alpha grid, and block definitions are frozen in
  `table_frozen_parc_parameters.csv`, `table_k_alpha_grid.csv`, and
  `table_block_definitions.csv`.
- DFT audit arms are frozen in `table_dft_audit_sampling_scheme.csv`; they use
  only pre-DFT score, rank, selection status, and public-label exclusion status.
- t0/t1 hull definitions and MLIP audit models are frozen before any new
  outcome-dependent interpretation.
- CTC human-audit guidelines remain blind/conservative and are tied to existing
  source artifacts by SHA256.

## Go / No-Go

The primary anti-p-hacking guardrail is that DFT comparator arms, hull
definitions, score sources, and manuscript claim boundaries are fixed before
outcomes. If any DFT outcome is observed before comparator-arm freeze, that arm
cannot support a primary raw-vs-PARC claim. If A3 gates fail, A3 remains a
diagnostic or failed-gate vignette.

## External Registration

`table_external_registration_plan.csv` records OSF and Zenodo as
ready-for-upload targets. No DOI or registration URL is fabricated here.
