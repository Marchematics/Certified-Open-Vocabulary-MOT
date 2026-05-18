# Data Availability

This repository provides derived, public-safe PARC-Track artifacts: audit labels, certification result tables, schemas, tiny fixtures, and frozen configuration files.

The guiding rule is that the repository should let reviewers reproduce the
certification flow and verify reported tables without redistributing data owned
by the original benchmark maintainers.

## Included Data

- `outputs/benchmarks/parc_certification_benchmark/audit/audit_labels_2000_human_reviewed.csv`: human-reviewed audit labels for 2,000 candidate paths.
- `outputs/benchmarks/parc_certification_benchmark/audit/audit_error_taxonomy.csv`: false-tracklet taxonomy.
- `outputs/benchmarks/parc_certification_benchmark/results/`: paper-facing certification and stress-test result tables.
- `outputs/benchmarks/parc_certification_benchmark/tiny_fixture/`: synthetic tiny fixture for validating code paths.
- `outputs/milestones/scientific_domain_ctc/`: public-safe CTC cell-link certification result tables, figures, and sanitized provenance.
- `outputs/milestones/ctc_strict_human_audit/`: human-confirmed CTC strict-audit labels and release-queue summary.
- `outputs/milestones/scientific_domain_spacenet7/`: public-safe SpaceNet 7 building-link certification result tables, figures, and sanitized provenance.
- `outputs/milestones/scientific_domain_materials/`: public-safe Matbench Discovery / WBM materials-candidate release tables, source hashes, leakage checks, and controls.
- `outputs/milestones/scientific_release_success_map/`: consolidated cross-domain release/refusal evidence matrix.
- `outputs/milestones/fixed_budget_downstream_utility/`, `outputs/milestones/primary_statistics/`, `outputs/milestones/materials_robustness_triad/`, `outputs/milestones/baseline_matrix_final/`, `outputs/milestones/ctc_strict_anchor/`, `outputs/milestones/iwildcam_audit_final/`, and `outputs/milestones/spacenet_real_audit_final/`: experiment-finalization tables derived from completed public-safe evidence.
- `outputs/milestones/materials_temporal_validation/` and `outputs/milestones/materials_independent_dft_validation/`: A1/A2 protocol-only status packages. They contain feasibility and blocked-status rows, not completed prospective validation results.
- `outputs/milestones/reproducibility_freeze/` and `outputs/artifact_index.csv`: milestone index and validation commands for the experiment-finalization package.

## Excluded Data

We do not redistribute raw OVT-B, TAO, BURST, LV-VIS/BURST frames, CTC microscopy images/annotations, SpaceNet imagery/GeoJSON labels, raw WBM crystal structures, raw annotation JSON files, detector outputs containing raw frame crops, model weights, or caches. These assets must be obtained from the original dataset/model maintainers. The materials milestone uses public Matbench Discovery / WBM summary and prediction CSVs; the public package includes only derived result tables and SHA256 hashes.

## Reconstructing Full Experiments

1. Download the original datasets and weights under their licenses.
2. Materialize sanitized configs with local paths using `scripts/materialize_configs.py`.
3. Convert detector/tracker outputs into the PARC candidate schema described in `docs/API.md`.
4. Run the PARC certification CLI as documented in `REPRODUCIBILITY.md`.

The published result tables are sufficient to reproduce the paper tables without raw videos.

## Integrity Checks

All public files are listed in `MANIFEST_SHA256.txt`.  Verify the package with:

```bash
sha256sum -c MANIFEST_SHA256.txt
```

Public-bundle safety can be checked with:

```bash
python scripts/validate_public_bundle.py outputs/milestones/reliability_fortress
python scripts/validate_public_bundle.py outputs/milestones/scientific_release_success_map
```
