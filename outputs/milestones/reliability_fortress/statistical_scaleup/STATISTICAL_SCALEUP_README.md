# Statistical Scale-Up Protocol Closeout

This folder records the gap between the current frozen evidence and the requested
journal-scale evidence standard. It intentionally does not relabel current 3-seed
experiments as 30-seed experiments.

## Targets

- Main real-data seed target: **30+ seeds** (`0-29`).
- Main dataset target: OVT-B, TAO, BURST, LVIS, plus one scientific-domain dataset.
- Main protocol: `M=150`, `alpha=0.1`, with sensitivity `M=[50, 100, 150, 300]` and `alpha=[0.05, 0.1, 0.2]`.
- Statistical reporting: bootstrap 95% confidence intervals with explicit seed-count status.

## Current Machine-Generated Tables

- `table_statistical_scaleup_protocol.csv`: target requirements, current status, and next actions.
- `table_seed_coverage.csv`: completed seed counts for each available dataset/generator/policy cell.
- `table_main_bootstrap_ci.csv`: bootstrap CIs over completed seeds; rows with fewer than 30 seeds are marked as preliminary.
- `table_dataset_scope_journal.csv`: dataset/task coverage and the missing scientific-domain anchor.
- `table_baseline_family_mapping.csv`: implemented and mapped baseline families, including CRC/e-value families.

## Status

Current completed seed groups: 64.
Groups already meeting the 30-seed target: 0.
Groups requiring 30-seed reruns: 64.

The scientific-domain dataset row is deliberately marked as missing until a real
domain case study is run and frozen.
