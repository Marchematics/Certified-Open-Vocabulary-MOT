# Materials Independent DFT Validation Closeout

Evidence status: `completed_independent_oqmd_exact_structure_diagnostic_low_coverage`.

This milestone attempts A2 independent DFT-source validation with a real public
OQMD query and exact-structure matching. It does not fabricate an independent
join table and does not use OQMD labels for PARC selection.

## Completed Actions

- Reconstructed the frozen ALIGNN-FF `alpha=0.10, K=300` PARC rows from
  public WBM/Matbench labels and public ALIGNN-FF predictions.
- Loaded private WBM raw ComputedStructureEntry files only to recover candidate
  structures for matching.
- Queried OQMD by chemical system after release reconstruction.
- Counted independent FTR only for exact reduced-formula plus StructureMatcher
  matches. Formula-only hits are reported as diagnostics only.

## Headline Diagnostics

- Unique raw top-K candidates evaluated for matching: `701`.
- Unique exact OQMD structure matches: `5`.
- Mean released exact-match coverage: `0.004`.
- Mean raw top-K exact-match coverage: `0.009`.
- Mean OQMD independent FTR on matched released candidates: `1.000`.
- Mean OQMD independent FTR on matched raw top-K candidates: `0.860`.

## Interpretation

If coverage is low, this is a completed independent-source diagnostic rather
than a primary independent validation result. The A2 gate is promoted to
completed evidence only when exact-match coverage is high enough under the
predeclared threshold. This package therefore hardens provenance and identifies
the remaining independent-source coverage gap without overstating the result.
