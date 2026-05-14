# PARC: Auditable Release-Time Certification under Partial Verification

PARC is a post-prediction certification layer for scientific and open-world AI systems operating under partial verification. Given a frozen candidate universe from an external detector, tracker, or linker, PARC calibrates against a null superset and either releases a self-consistent certified subset or refuses unsafe release requests with explicit diagnostics.

This repository is the public-safe reproducibility package for the final release of the project. It includes the original open-vocabulary MOT instantiation, scientific-domain link certification on Cell Tracking Challenge and SpaceNet 7, open-world vision generality artifacts, audit benchmark CSVs, frozen configs, result tables, tiny fixtures, and documentation needed to reproduce the certification flow without redistributing raw benchmark videos, raw annotations, model weights, or local caches.

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
│   ├── milestones/reliability_fortress/
│   ├── milestones/generality_reliability/
│   ├── milestones/release_story/
│   ├── milestones/scientific_domain_ctc/
│   ├── milestones/scientific_domain_spacenet7/
│   └── benchmarks/parc_certification_benchmark/
├── tests/                            # pytest suite and tiny fixtures
├── scripts/                          # public-safe helper scripts
├── tools/                            # notes for external metric/export tooling
└── docs/                             # API, audit protocol, getting started
```

## What Is Included

- PARC certification code: null-superset block calibration, coverage-conditional empty-block handling, e-value generation, finite-resolution diagnostics, SCS-Greedy release, report builders, TrackEval export helpers, and adapter utilities.
- Audit benchmark: `outputs/benchmarks/parc_certification_benchmark/audit/` and the full frozen milestone under `outputs/milestones/reliability_fortress/`.
- Scientific-domain milestones for CTC cell-link certification and SpaceNet 7 building-link certification.
- Result tables for OVT-B, TAO, BURST, black-box generators, published-tracker adapters, non-exchangeability stress tests, null-inflation sensitivity, LVIS/LVVIS/OVVIS generality checks, Mondrian/per-class/runtime/anytime diagnostics, and Prop. 5 high-evidence mass diagnostics.
- Tiny fixture for validating the full schema-to-certification path without downloading external datasets.

## What Is Not Included

This repository intentionally excludes raw videos, raw dataset annotations, raw satellite imagery, raw microscopy images, model weights, third-party detector/tracker repositories, Hugging Face caches, GPU caches, frame caches, and montage images. Please obtain OVT-B, TAO, BURST, CTC, SpaceNet 7, detector weights, and published tracker weights from their original maintainers under their respective licenses.

## Quick Start

```bash
git clone https://github.com/Marchematics/Certified-Open-Vocabulary-MOT.git parc-track
cd parc-track
python -m venv .venv
source .venv/bin/activate
pip install -e code/parc_track
pip install numpy scipy pandas opencv-python pyyaml tqdm pytest motmetrics pycocotools pillow matplotlib shapely tifffile imagecodecs
pytest -q tests
```

Run the tiny fixture through the public API path:

```bash
python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api
```

For full benchmark reproduction, see `REPRODUCIBILITY.md`.

## Main Frozen Artifacts

- Final reliability milestone: `outputs/milestones/reliability_fortress/`
- Generality and stratified reliability milestone: `outputs/milestones/generality_reliability/`
- Release/refusal story milestone: `outputs/milestones/release_story/`
- Biomedical scientific-domain milestone: `outputs/milestones/scientific_domain_ctc/`
- Earth-observation scientific-domain milestone: `outputs/milestones/scientific_domain_spacenet7/`
- Community benchmark: `outputs/benchmarks/parc_certification_benchmark/`
- File integrity manifest: `MANIFEST_SHA256.txt`

## Citation

A formal citation will be added after archival release. Until then, cite the repository title and commit hash.
