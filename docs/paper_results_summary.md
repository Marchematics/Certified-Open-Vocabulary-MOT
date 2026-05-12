# PARC-Track Paper Results Summary

This summary freezes the current release-core evidence bundle. GroundingDINO proposals are treated as a scaffold generator, not a final OVMOT backbone claim.

## Frozen Files
- `table_real_first_nonempty.csv`
- `table_m_sweep_parc_full_with_audit.csv`
- `table_baseline_three_methods_M150.csv`
- `table_seed_stability_M150.csv`
- `audit_summary_after_uncertain_recheck.csv`
- `table_baseline_expanded.csv`
- `table_alpha_sweep.csv`
- `table_main_fixed_m.csv`
- `table_main_tuned_m.csv`
- `table_best_m_diagnostic.csv`
- `table_seed_empty_diagnostics.csv`
- `table_alpha_sweep_meanstd.csv`
- `table_baseline_expanded_meanstd.csv`

## Next Required Evidence
- OVT-B alpha/M/seed matrix.
- TAO/OV-TAO transfer audit/certification. Current data status: official TAO annotations are downloaded, and a one-video TAO AVA mini subset passes strict tracking-layout inspection (`tracking_layout_ok`, 1 video / 40 frames / 6 tracks / 201 boxes). Full TAO certification remains pending larger frame access.
- CLEAR-MOT IDSW real evaluator table.
