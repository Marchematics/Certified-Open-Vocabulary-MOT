# Reproduce t1 Hull-Shift Audit Tables

Run:

```bash
make reproduce-materials-figures
make reproduce-materials-baseline-frontier
```

This regenerates the paper-facing Phase49/50 tables, including:

- `table_t1_ftr_by_k_and_policy.csv`
- `table_t1_stable_to_unstable_drift.csv`
- `figure_t1_hull_shift_inputs.csv`
- `table_t1_bootstrap_ci.csv`
- `table_t1_randomization_tests.csv`
- `table_version_shift_decomposition.csv`
- `table_t1_mlip_baseline_frontier.csv`

The audit evaluates frozen t0-selected K=300/500 queues under a current-MP
hull. No t1 label is used for release selection.
