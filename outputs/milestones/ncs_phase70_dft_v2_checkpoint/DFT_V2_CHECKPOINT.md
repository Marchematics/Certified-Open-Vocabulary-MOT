# Phase70 DFT v2 Checkpoint

Status: `execution_checkpoint_no_stability_outcomes`.

The local VASP queue for the blinded Phase68 DFT v2 package is running under a
nonspin fixed-cell safe execution layer. This checkpoint records execution
progress and final energies where available. It does not compute
`e_above_hull_ev_per_atom` or `stable_exact`.

Current checkpoint:

- total manifest jobs: `360`
- completed jobs: `11`
- failed jobs: `2`
- running jobs inferred from local `VASP_RUNNING` markers: `3`
- finished-job failure rate: `0.15384615384615385`
- workflow gate threshold: `0.1`

Interpretation:

`VASP_DONE` / `completed` means a single-structure calculation has VASP output
and a final energy can be extracted. It is not a stability outcome. DFT v2
cannot support a prospective materials-discovery claim, release-vs-tail utility
claim, or alpha claim until the reference-hull outcome layer generates
`e_above_hull_ev_per_atom` and `stable_exact` and the numeric workflow gates pass.
