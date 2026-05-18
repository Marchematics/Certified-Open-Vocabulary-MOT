# NMI Main-Evidence Hard Upgrade Plan

Status date: 2026-05-18

## Objective

Upgrade the PARC materials evidence from retrospective release-certification plus diagnostics to a completed prospective computational materials trial. The only candidate for a true main-evidence upgrade is A3-v4: MatterGen-generated public-label-free candidates, CHGNet + MACE conservative consensus scoring, frozen PARC selection before DFT outcomes, and complete DFT evaluation of the released set.

This document is an execution plan, not completed evidence.

## Current Evidence State

- CTC remains the strict methodological anchor: learned-hybrid, sequence-disjoint, strict alpha=0.10, with leakage/reverse/random-score controls.
- Materials retrospective WBM/Matbench rows are strong for release governance and downstream queue consequence, but they are still retrospective/public-label based.
- A2 OQMD independent validation is completed only as a low-coverage diagnostic; it must not be promoted to primary independent validation.
- A3-v2/v3 are no-go gates for PGCGM and near-hull substitution pools.
- A3-v4 currently has MatterGen/MACE/CHGNet environment and smoke diagnostics, but no completed main evidence until a nonempty public-label-free candidate universe, frozen PARC selection, and DFT manifest exist.

## Main Path

A3-v4 is the primary upgrade path.

1. Generate a real MatterGen candidate pool.
2. Parse CIFs into public-safe metadata and hashes.
3. Apply public-label exclusion.
4. Score retained candidates and calibration representatives with the same CHGNet + MACE conservative consensus rule.
5. Run PARC endpoints with frozen alpha/K/rho/block definitions.
6. If release gate passes, freeze selection_frozen_v4.csv and dft_job_manifest_v4.csv before any DFT outcome.
7. Run DFT on the complete PARC release set and matched raw comparator set.
8. Report completed prospective evidence only if DFT outcomes exist and the release satisfies the predeclared success criteria.

## Primary Gate Criteria

DFT export is allowed only if all conditions hold:

- public-label-free candidates >= 5,000 preferred, >= 2,000 minimum pilot threshold;
- valid CHGNet + MACE consensus scores >= 2,000 preferred, >= 1,000 minimum pilot threshold;
- at least one strict endpoint has PARC release size >= 30 for headline evidence, or >=25 for secondary support;
- raw-only tail size >= release size or >=25 minimum;
- evidence mass ratio >= 1.05 for DFT export;
- selection and DFT manifest are committed before DFT outcomes.

## Endpoint Priority

1. v4a strict exact stable, K=100, alpha=0.10, rho=0.10, composition-family blocks.
2. v4b strict exact stable, K=300, alpha=0.10, rho=0.10, composition-family blocks.
3. v4c near-hull <=25 meV/atom, K=300, alpha=0.10, rho=0.10. This is boundary/near-hull support, not an exact-stable strict headline.

## DFT Evidence Rule

Primary evidence requires full DFT evaluation of the complete PARC release set. A matched-volume raw top-R comparator is required for the primary empirical comparison. A raw-only rejected-tail arm is strongly preferred for downstream stopping/refusal interpretation.

DFT failures are reported and counted conservatively as not-certified-stable in the primary analysis unless a predeclared standard rerun succeeds.

## Current Execution Step

Run a MatterGen 5k pilot in tmux:

- private output: `/home/waas/paper_experiments/private/mattergen_v4_generation/pilot_5k_tmux`
- public-safe milestone: `outputs/milestones/mattergen_parc_prospective_dft_followup/`
- generator: `mattergen_base`
- generation target: 5,000 candidates
- runner: `scripts/run_mattergen_5k_pilot_tmux.sh`

The tmux job first waits for GPU compute contexts to clear, then runs MatterGen generation, parses metadata, and runs the existing public-label exclusion/scoring diagnostic. If any step fails, it writes logs and exits nonzero; no positive evidence is claimed.

## Claim Discipline

- Completed evidence: only rows with real candidate pool, frozen selection, DFT manifest, and DFT outcomes.
- Diagnostic: A2 OQMD low-coverage exact-structure matching; MatterGen smoke/pilot exclusion/scoring without DFT.
- Protocol-only: any endpoint with empty selection or no DFT manifest.

Do not describe MatterGen smoke, 5k generation, public-label exclusion, or consensus scoring alone as a prospective positive result.
