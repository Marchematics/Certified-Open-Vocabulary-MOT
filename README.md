# PARC-Track: Certified Open-Vocabulary MOT under Partial Annotations

PARC-Track is a post-hoc certification layer for open-vocabulary multi-object tracking (OVMOT) proposal generators. It takes candidate tracklets from an external detector/tracker, calibrates against a null-superset under partial annotations, and releases only a self-consistent certified subset.

This repository is the public-safe reproducibility package for the  reliability-fortress version of the project. It contains the certification code, frozen configs, audit benchmark CSVs, result tables, tiny fixtures, and documentation needed to reproduce the certification flow without redistributing raw benchmark videos, raw annotations, model weights, or local caches.

## Repository Layout

```text
parc-track/
├── README.md
├── LICENSE
├── DATA_AVAILABILITY.md
├── CODE_AVAILABILITY.md
├── REPRODUCIBILITY.md
├── MANIFEST_SHA256.txt
├── code/parc_track/                  # Python package and CLI
├── configs/                          # Frozen experiment configs, sanitized paths
├── outputs/
│   ├── milestones/tpami_reliability_fortress_v2/
│   └── benchmarks/parc_certification_benchmark_v1/
├── tests/                            # pytest suite and tiny fixtures
├── scripts/                          # public-safe helper scripts
├── tools/                            # notes for external metric/export tooling
└── docs/                             # API, audit protocol, getting started
```

## What Is Included

- PARC-Track certification code: null-superset block calibration, coverage-conditional empty-block handling, e-value generation, finite-resolution diagnostics, SCS-Greedy release, report builders, TrackEval export helpers, and adapter utilities.
- Audit benchmark: `outputs/benchmarks/parc_certification_benchmark_v1/audit/` and the full frozen milestone under `outputs/milestones/tpami_reliability_fortress_v2/`.
- Result tables for OVT-B, TAO, BURST, black-box generators, published-tracker adapters, non-exchangeability stress tests, null-inflation sensitivity, OVVIS mask-path scaffold, Mondrian/per-class/runtime/anytime diagnostics, and Prop. 5 high-evidence mass diagnostics.
- Tiny fixture for validating the full schema-to-certification path without downloading external datasets.

## What Is Not Included

This repository intentionally excludes raw videos, raw dataset annotations, model weights, third-party detector/tracker repositories, Hugging Face caches, GPU caches, frame caches, and montage images. Please obtain OVT-B, TAO, BURST, detector weights, and published tracker weights from their original maintainers under their respective licenses.

## Quick Start

```bash
git clone https://github.com/Marchematics/Certified-Open-Vocabulary-MOT.git parc-track
cd parc-track
python -m venv .venv
source .venv/bin/activate
pip install -e code/parc_track
pip install numpy scipy pandas opencv-python pyyaml tqdm pytest motmetrics pycocotools pillow matplotlib
pytest -q tests
```

Run the tiny fixture through the public API path:

```bash
python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api
```

For full benchmark reproduction, see `REPRODUCIBILITY.md`.

## Main Frozen Artifacts

- Final reliability milestone: `outputs/milestones/tpami_reliability_fortress_v2/`
- Community benchmark: `outputs/benchmarks/parc_certification_benchmark_v1/`
- File integrity manifest: `MANIFEST_SHA256.txt`

## Citation

A formal citation will be added after archival release. Until then, cite the repository title and commit hash.
