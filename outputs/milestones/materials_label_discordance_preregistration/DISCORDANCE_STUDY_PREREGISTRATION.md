# Discordance Study Preregistration

## Scope

This is a preregistration for a separate materials-label discordance paper.
The target is the reproducibility and downstream consequence of public DFT
binary stability labels used in ML crystal-stability discovery benchmarks.

The primary contribution is not PARC. PARC may be used later as a
release/refuse probe after source discordance has been quantified.

## Central Hypothesis

Public DFT source choice can change binary exact-stability labels on exactly
matched crystal structures, and that label discordance can change ML
materials-discovery conclusions.

## Frozen Week-One Tests

1. Data access: verify legal, versioned snapshots for at least two public DFT
   sources plus WBM/Matbench context.
2. Minimal discordance: compute pairwise binary exact-stability discordance
   only on exact/high-confidence structure matches.
3. Downstream consequence: test whether public-model rankings, discovered
   stable counts, or release/refuse decisions flip under source A versus B.

## Stop Rules

- Stop if data access cannot be established without private or untracked
  labels.
- Stop if the clean two-source discordance is small (`<=0.10`) or the exact
  match denominator is too small.
- Stop or downgrade if discordance does not change downstream conclusions.

## Claim Boundaries

Do not claim that external materials databases are interchangeable ground
truth. Do not claim prospective materials discovery. Do not claim that PARC
solves cross-source DFT disagreement. Do not use formula-only matches for the
headline discordance number.
