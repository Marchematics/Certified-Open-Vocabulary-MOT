# Data Availability

This repository provides derived, public-safe PARC-Track artifacts: audit labels, certification result tables, schemas, tiny fixtures, and frozen configuration files.

## Included Data

- `outputs/benchmarks/parc_certification_benchmark_v1/audit/audit_labels_2000_human_reviewed_v1.csv`: human-reviewed audit labels for 2,000 candidate paths.
- `outputs/benchmarks/parc_certification_benchmark_v1/audit/audit_error_taxonomy.csv`: false-tracklet taxonomy.
- `outputs/benchmarks/parc_certification_benchmark_v1/results/`: paper-facing certification and stress-test result tables.
- `outputs/benchmarks/parc_certification_benchmark_v1/tiny_fixture/`: synthetic tiny fixture for validating code paths.

## Excluded Data

We do not redistribute raw OVT-B, TAO, BURST, LV-VIS/BURST frames, raw annotation JSON files, detector outputs containing raw frame crops, model weights, or caches. These assets must be obtained from the original dataset/model maintainers.

## Reconstructing Full Experiments

1. Download the original datasets and weights under their licenses.
2. Materialize sanitized configs with local paths using `scripts/materialize_configs.py`.
3. Convert detector/tracker outputs into the PARC candidate schema described in `docs/API.md`.
4. Run the PARC certification CLI as documented in `REPRODUCIBILITY.md`.

The published result tables are sufficient to reproduce the paper tables without raw videos.
