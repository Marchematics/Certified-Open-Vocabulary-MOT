# Verified-Positive Removal Load-Bearing Closeout

This closeout is completed evidence from candidate-level reruns. It is not derived from summary-only tables.

- Target rows rerun: 6
- Seed-level rows: 360
- Target rows showing lower release under no-removal or random-removal controls: 6
- ALIGNN margin-excluded 25meV K=100 full-PARC FTR: 0.111; this remains a boundary sensitivity row, not a strict pass.

## Removal modes

- `full_parc`: remove top-score observed true positives from the calibration null superset.
- `no_verified_positive_removal`: keep observed positives inside the calibration null superset.
- `random_positive_removal`: remove the same number of calibration candidates at random as a negative control.

## Artifacts

- Seed rows: `table_verified_positive_removal_load_bearing_seed_rows.csv`
- Summary rows: `table_verified_positive_removal_load_bearing.csv`
