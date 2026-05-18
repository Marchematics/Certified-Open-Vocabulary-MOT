# A3-v4 DFT Run Protocol

Status: pre-outcome DFT execution package. This is not DFT evidence.

## Frozen inputs

- `selection_frozen_v4.csv` is not modified by this package.
- PARC release source: `dft_job_manifest_v4_addendum.csv`, arm `PARC-release-full`.
- Extra-tail source: `dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv`, arm `raw_top100_extra_tail`.
- Package composition: 75 PARC-release CIFs and 25 raw-top100 extra-tail CIFs.

## Execution

Run all candidates with the same DFT engine and settings. The settings template is `SETTINGS_TEMPLATE.yaml`.
All jobs must use the same relaxation, static calculation and correction policy across arms.

## Conservative outcome policy

Failed, unconverged or missing jobs are counted as not-certified-stable / false for FTR in the conservative primary analysis.
Completed-only summaries may be reported only as secondary diagnostics.

## Claim boundary

No prospective DFT evidence or prospective materials discovery claim is allowed until outcome files are returned and analyzed.
The package hash must be recorded before DFT execution.
