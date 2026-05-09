# Certified Open-Vocabulary MOT under Partial Annotations

This repository contains the reproducibility package for **PARC-Track**:
**Partial-Annotation Robust Certification for Open-Vocabulary Tracking**.

The project studies certified open-vocabulary multi-object tracking under partial annotations. The main ingredients are null-superset video-block calibration, finite-resolution aware e-value tuning, and polynomial self-consistent greedy selection.

## What Is Included

This repository intentionally contains **code, configs, scripts, documentation, paper figures, and derived experiment tables/artifacts** needed for reproducibility and writing.

Included highlights:

- `code/parc_track/`: Python package and CLI implementation.
- `configs/`: smoke, Phase-2, OVT-B full, TAO full, and report-export configs.
- `scripts/`: dataset download/extract helpers and experiment runners.
- `docs/`: formal spec and result summaries.
- `outputs/milestones/ijcv_full_ovtb_v1/`: full OVT-B result tables.
- `outputs/milestones/ijcv_tao_full_v2_clean/`: clean TAO result tables.
- `outputs/milestones/ijcv_cross_dataset_v6/`: OVT-B + TAO cross-dataset tables.
- `outputs/milestones/ijcv_stability_v1/`: bootstrap CI, worst-case FTR, runtime, Mondrian, per-class, and Prop.5 diagnostics.
- `outputs/milestones/ijcv_stability_v2/`: anytime-release diagnostic and stability-v2 writing tables.
- `outputs/milestones/ijcv_burst_v2/`: BURST third-dataset scaffold, audit-200, certification, and Prop.5 tables.
- `outputs/milestones/ijcv_burst_owlv2_stress_v1/`: BURST OWLv2 cross-generator stress/failure analysis.
- `outputs/phase*_*/`: derived CSV/JSON artifacts used to reproduce tables.

## What Is Not Included

To avoid license, size, and credential contamination, this repository does **not** include:

- raw OVT-B / TAO image data,
- detector model weights,
- Hugging Face / GitHub tokens,
- `.venv`, package caches, temporary downloads, or third-party repos.

See `CLEANING_REPORT.md` and `SECRET_SCAN_REPORT.json` for the cleaning policy and final secret-scan status.

## Quick Start

```bash
cd Certified-Open-Vocabulary-MOT
source env.sh
python -m venv .venv
source .venv/bin/activate
pip install -e code/parc_track
pip install numpy scipy pandas opencv-python pyyaml tqdm pytest motmetrics pycocotools pillow matplotlib
pytest -q tests
```

## Reproduce Synthetic Smoke

```bash
source env.sh
source .venv/bin/activate
python -m parc_track.cli smoke --config configs/smoke.yaml
```

## Reproduce Existing Paper Tables From Derived Outputs

The latest paper-facing tables are already exported under:

```text
outputs/milestones/ijcv_full_ovtb_v1/
outputs/milestones/ijcv_tao_full_v2_clean/
outputs/milestones/ijcv_cross_dataset_v6/
outputs/milestones/ijcv_stability_v1/
outputs/milestones/ijcv_stability_v2/
outputs/milestones/ijcv_burst_v2/
outputs/milestones/ijcv_burst_owlv2_stress_v1/
```

For cross-dataset writing, start with:

```text
outputs/milestones/ijcv_cross_dataset_v6/table_cross_dataset_certification.csv
outputs/milestones/ijcv_cross_dataset_v6/table_cross_dataset_certification_meanstd.csv
outputs/milestones/ijcv_cross_dataset_v6/table_cross_dataset_audit.csv
```

For the late IJCV sprint additions, start with:

```text
docs/latest_experiment_delta.md
outputs/milestones/ijcv_stability_v1/table_main_bootstrap_ci.csv
outputs/milestones/ijcv_stability_v1/table_worst_case_cons_ftr.csv
outputs/milestones/ijcv_stability_v2/table_anytime_release.csv
outputs/milestones/ijcv_burst_v2/table_burst_certification_summary.csv
outputs/milestones/ijcv_burst_v2/table_burst_released_unsupported_audit_summary.csv
outputs/milestones/ijcv_burst_v2/table_burst_cross_generator_prop5.csv
outputs/milestones/ijcv_burst_owlv2_stress_v1/table_burst_owlv2_prop5_mass_ratio.csv
```

## Re-running Real Data Experiments

Real data experiments require the datasets and detector weights to be downloaded separately under `/home/waas/paper_experiments/data` or equivalent paths. Configs currently use the original experiment root paths and may need editing if you clone this repository elsewhere.

Representative commands:

```bash
source env.sh
source .venv/bin/activate
python -m parc_track.cli real ovtb-matrix --config configs/phase3_ovtb_full_matrix.yaml
python -m parc_track.cli real ovtb-matrix --config configs/phase3_tao_full_matrix.yaml
python -m parc_track.cli report tpami-core --config configs/phase3_paper_export_full.yaml
python -m parc_track.cli report tpami-core --config configs/phase3_paper_export_tao_full.yaml
```

Late-stage BURST and IJCV diagnostics:

```bash
# BURST GroundingDINO proposal universe, if data/weights are present.
python -m parc_track.cli phase2 propose --config configs/phase7_burst_audit.yaml
python -m parc_track.cli phase3 matrix --config configs/phase7_burst_matrix.yaml
python -m parc_track.cli phase7 burst-freeze --output-dir outputs/milestones/ijcv_burst_v2 --source-dir outputs/phase7_burst

# BURST OWLv2 stress test, if GPU/model access is present.
python -m parc_track.cli phase2 propose --config configs/phase7_burst_owlv2_audit.yaml
python -m parc_track.cli phase3 matrix --config configs/phase7_burst_owlv2_matrix.yaml

# Anytime diagnostic from existing OVT-B e-values.
python -m parc_track.cli phase7 anytime --output-dir outputs/phase7_anytime
```

## Current Result Milestones

- OVT-B full matrix and tables: `outputs/milestones/ijcv_full_ovtb_v1/`
- TAO full clean matrix and tables: `outputs/milestones/ijcv_tao_full_v2_clean/`
- OVT-B + TAO cross-dataset bundle: `outputs/milestones/ijcv_cross_dataset_v6/`
- IJCV stability v1: `outputs/milestones/ijcv_stability_v1/`
- IJCV stability v2: `outputs/milestones/ijcv_stability_v2/`
- BURST third-dataset evidence: `outputs/milestones/ijcv_burst_v2/`
- BURST OWLv2 cross-generator stress analysis: `outputs/milestones/ijcv_burst_owlv2_stress_v1/`

## External Writing Bundle

The latest local writing delta package is not tracked directly in Git:

```text
/home/waas/paper_experiments/outputs/packages/parc_track_post_phase4_delta_for_writing_20260510_013544.tar.gz
SHA256: 04ead85d895d274404c006ef8adad9473058a594c04700e7d7cee7dfcb14391f
```

It contains code/config/doc/script deltas and derived CSV/JSON/figures/tables created after
`phase4_third_generator_delta_from_ijcv_extra_cpu_v1_20260509_160838.tar.gz`.
It excludes raw datasets, raw annotations, model weights, HF/GroundingDINO caches, viewer media,
sharded intermediate duplicate candidates, and compiled extensions.

## Cleaning Notes

This repository was assembled from `parc_track_clean_results_bundle_20260508_184842`.
Final staged scan found no raw Hugging Face token patterns. Raw datasets and model weights are excluded by design.
