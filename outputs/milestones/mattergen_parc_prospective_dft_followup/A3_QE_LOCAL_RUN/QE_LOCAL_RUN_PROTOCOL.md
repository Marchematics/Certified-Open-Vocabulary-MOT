# A3-v4 Local Quantum ESPRESSO Run Layer

Status: local execution environment and QE input decks prepared; no DFT outcomes are included.

## Frozen source

Inputs are derived from `A3_DFT_RUN_PACKAGE/package_job_manifest.csv`.
This script does not modify `selection_frozen_v4.csv`, `dft_job_manifest_v4_addendum.csv`, or `dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv`.

## Local engine

- QE executable: `pw.x`
- MPI launcher: `mpirun.openmpi`
- Pseudopotential library: copied SSSP efficiency v1.1 UPF files under `pseudos/`
- Required elements covered: 70 / 70
- Jobs prepared: 100 total (75 release, 25 extra-tail)

## Local settings

Generated input decks use QE `vc-relax`, PBE, SSSP UPF pseudopotentials, `ecutwfc=60 Ry`, `ecutrho=480 Ry`, Methfessel-Paxton smearing, and a fixed deterministic k-point grid derived from lattice lengths.

These settings are a local executable DFT route, not a Materials Project compatibility claim. Any manuscript DFT claim must report this engine/settings scope.

## Claim boundary

This layer is not DFT evidence. It only records that local QE input decks and launch scripts were prepared before outcomes. Prospective materials discovery claims remain forbidden until DFT outcomes are returned and analyzed under the conservative failure policy.

## Launch

Start the full PARC-release arm in tmux:

```bash
NP=4 MAX_PARALLEL=3 bash outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/launch_parc_release_tmux.sh
```

Run the extra-tail arm only after the release arm policy decision:

```bash
NP=4 MAX_PARALLEL=3 bash outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/run_qe_batch_tmux.sh raw_top100_extra_tail
```
