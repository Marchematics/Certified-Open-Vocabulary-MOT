# Data Availability

This repository provides derived, public-safe PARC-Track artifacts: audit labels, certification result tables, schemas, tiny fixtures, and frozen configuration files.

## Included Data

- `outputs/benchmarks/parc_certification_benchmark/audit/audit_labels_2000_human_reviewed.csv`: human-reviewed audit labels for 2,000 candidate paths.
- `outputs/benchmarks/parc_certification_benchmark/audit/audit_error_taxonomy.csv`: false-tracklet taxonomy.
- `outputs/benchmarks/parc_certification_benchmark/results/`: paper-facing certification and stress-test result tables.
- `outputs/benchmarks/parc_certification_benchmark/tiny_fixture/`: synthetic tiny fixture for validating code paths.
- `outputs/milestones/scientific_domain_ctc/`: public-safe CTC cell-link certification result tables, figures, and sanitized provenance.
- `outputs/milestones/scientific_domain_spacenet7/`: public-safe SpaceNet 7 building-link certification result tables, figures, and sanitized provenance.

## Excluded Data

We do not redistribute raw OVT-B, TAO, BURST, LV-VIS/BURST frames, CTC microscopy images/annotations, SpaceNet imagery/GeoJSON labels, raw annotation JSON files, detector outputs containing raw frame crops, model weights, or caches. These assets must be obtained from the original dataset/model maintainers.

## Reconstructing Full Experiments

1. Download the original datasets and weights under their licenses.
2. Materialize sanitized configs with local paths using `scripts/materialize_configs.py`.
3. Convert detector/tracker outputs into the PARC candidate schema described in `docs/API.md`.
4. Run the PARC certification CLI as documented in `REPRODUCIBILITY.md`.

The published result tables are sufficient to reproduce the paper tables without raw videos.
