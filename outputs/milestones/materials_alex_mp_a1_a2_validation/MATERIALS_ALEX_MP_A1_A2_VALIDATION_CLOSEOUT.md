# Materials alex-mp A1/A2 Validation Closeout

Evidence status: `completed_independent_alex_mp_exact_structure_diagnostic`.

This milestone completes a local alex-mp exact-structure validation pass for the
materials flagship. It is not a new DFT calculation and it is not experimental
synthesis evidence.

## What Is Completed

- Reconstructed the frozen ALIGNN-FF `K=300`, `alpha=0.1` PARC
  row from the public WBM/Matbench labels and public model-prediction files.
- Used the later `alex_mp_20` local public snapshot as an external DFT label
  source for exact-structure matched candidates.
- Counted independent FTR only for exact reduced-formula plus StructureMatcher
  matches.
- Reported formula-only and no-formula rows as coverage diagnostics only.

## Headline Numbers

- Unique raw/PARC candidates considered: `701`.
- Unique exact alex-mp structure matches: `270`.
- Mean released exact-match coverage: `0.245`.
- Mean raw top-K exact-match coverage: `0.359`.
- Mean independent FTR on matched PARC releases: `0.745`.
- Mean independent FTR on matched raw top-K candidates: `0.734`.
- Mean PARC-vs-raw FTR delta on matched rows: `-0.012`.

## Interpretation

This is completed A2 evidence for the exact-match subset and a completed A1
quasi-temporal external-snapshot replay because the evaluation labels come from
the later alex-mp public snapshot rather than the WBM label table used to define
PARC calibration. The claim remains scoped to the exact-structure matched
subset; it must not be described as full-coverage independent validation.
