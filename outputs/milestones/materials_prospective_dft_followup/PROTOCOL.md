# Prospective In-Silico DFT Follow-Up Protocol

This milestone freezes the A3 protocol before any new DFT outcomes are known.
It is a protocol and selection-freeze package, not a completed DFT result.

## Primary Operating Point

- Model: `ALIGNN-FF`
- Alpha: `0.1`
- Rho: `0.1`
- Requested K: `500`
- Block definition: `composition-family`
- Primary arm size: `40` candidates per arm
- Minimum analyzable arm size: `25` candidates

## Required Arms

1. `PARC-release`: top candidates from the certified release set.
2. `raw-only rejected tail`: raw top-K candidates not released by PARC.
3. `raw top-R matched`: raw prefix matched to the PARC release size when nonredundant.

## No-Leakage Rules

- Candidate selection must be frozen before new DFT outcomes are computed.
- Candidates with public WBM, Materials Project, OQMD, Alexandria or GNoME
  stability labels are excluded from the prospective follow-up pool.
- Structure-level public duplicate filtering must be documented before DFT.
- K, alpha, rho, gamma, block definition and selection arms must not be changed
  after DFT outcomes are observed.
- Failed DFT jobs are counted as not-certified-stable in the conservative
  primary analysis after one standard rerun.

## Current Freeze Status

- Candidate-pool status: `not_supplied`
- Candidate-pool gate: `blocked_missing_unlabeled_candidate_pool`

If the candidate-pool gate is not `ready_for_selection`, this milestone must
not be described as a completed prospective DFT follow-up result.
