# DFT v2 Pilot Protocol

The DFT executor should receive only:

- `dft_v2_blinded_transfer_manifest.csv`
- the `cifs/` directory
- `SETTINGS_TEMPLATE_MP_COMPATIBLE.yaml`
- `DFT_OUTCOME_TEMPLATE.csv`

The executor should not receive `dft_v2_analysis_arm_key.csv` until all outcomes are frozen.

Conservative analysis policy:

1. `completed && stable_exact` counts as certified stable.
2. `completed && !stable_exact` counts as false.
3. failed, missing, invalid, duplicate or unconverged jobs count as not-certified-stable / false in the primary conservative FTR.
4. completed-only FTR may be reported only as a secondary diagnostic.
5. 25/50 meV near-hull thresholds may be reported only as sensitivity.
