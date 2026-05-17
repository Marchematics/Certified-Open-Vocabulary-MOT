# PARC: Auditable Release-Time Certification under Partial Verification

[![Tests](https://github.com/Marchematics/PARC-Certified-Open-Vocabulary-MOT/actions/workflows/tests.yml/badge.svg)](https://github.com/Marchematics/PARC-Certified-Open-Vocabulary-MOT/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Package](https://img.shields.io/badge/package-public--safe-blue)
![Manifest](https://img.shields.io/badge/manifest-SHA256%20verified-green)
![Domains](https://img.shields.io/badge/domains-CTC%20%7C%20Materials%20%7C%20iWildCam%20%7C%20SpaceNet7-lightgrey)
![Benchmark](https://img.shields.io/badge/benchmark-PARC%20certification-blue)
![Audit](https://img.shields.io/badge/audit-human--confirmed-green)


PARC is a post-prediction certification layer for scientific and open-world AI systems operating under partial verification. Given a frozen candidate universe from an external detector, tracker, or linker, PARC calibrates against a null superset and either releases a self-consistent certified subset or refuses unsafe release requests with explicit diagnostics.

This repository is the public-safe reproducibility package for the final release of the project. It includes the original open-vocabulary MOT instantiation, scientific-domain link certification on Cell Tracking Challenge and SpaceNet 7, a learned-hybrid CTC proposal-source companion, a Matbench Discovery materials-candidate release milestone, open-world vision generality artifacts, audit benchmark CSVs, frozen configs, result tables, tiny fixtures, and documentation needed to reproduce the certification flow without redistributing raw benchmark videos, raw annotations, model weights, or local caches.

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
│   ├── milestones/scientific_domain_ctc_learned/
│   ├── milestones/ctc_strict_human_audit/
│   ├── milestones/scientific_domain_spacenet7/
│   ├── milestones/scientific_domain_iwildcam_human_audit/
│   ├── milestones/scientific_domain_materials/
│   ├── milestones/scientific_release_success_map/
│   ├── milestones/no_human_scientific_consequence/
│   └── benchmarks/parc_certification_benchmark/
├── tests/                            # pytest suite and tiny fixtures
├── scripts/                          # public-safe helper scripts
├── tools/                            # notes for external metric/export tooling
└── docs/                             # API, audit protocol, getting started
```

## What Is Included

- PARC certification code: null-superset block calibration, coverage-conditional empty-block handling, e-value generation, finite-resolution diagnostics, SCS-Greedy release, report builders, TrackEval export helpers, and adapter utilities.
- Audit benchmark: `outputs/benchmarks/parc_certification_benchmark/audit/` and the full frozen milestone under `outputs/milestones/reliability_fortress/`.
- Scientific-domain milestones for CTC cell-link certification, learned-hybrid CTC link certification, SpaceNet 7 building-link certification, a prospective iWildCam animal-present human-audit package, and Matbench Discovery stable-material candidate release.
- Result tables for OVT-B, TAO, BURST, black-box generators, published-tracker adapters, non-exchangeability stress tests, null-inflation sensitivity, LVIS/LVVIS/OVVIS generality checks, Mondrian/per-class/runtime/anytime diagnostics, and Prop. 5 high-evidence mass diagnostics.
- Tiny fixture for validating the full schema-to-certification path without downloading external datasets.

## What Is Not Included

This repository intentionally excludes raw videos, raw dataset annotations, raw satellite imagery, raw microscopy images, raw crystal structures, model weights, third-party detector/tracker repositories, Hugging Face caches, GPU caches, frame caches, and montage images. Please obtain OVT-B, TAO, BURST, CTC, SpaceNet 7, Matbench Discovery/WBM source data, detector weights, and published tracker weights from their original maintainers under their respective licenses.

## Quick Start

```bash
git clone https://github.com/Marchematics/PARC-Certified-Open-Vocabulary-MOT.git parc-track
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

## Reviewer Entry Points

- `docs/reviewer_guide.md`: what can be checked without raw datasets, what requires external data, and where the strict/operational rows live.
- `docs/claim_table.md`: claim-by-claim evidence map with paths, reproduction commands, and limitations.
- `docs/audit_protocol.md`: human-audit label definitions, verified-positive rules, second-review policy, and disagreement handling.
- `docs/benchmark_card.md`: PARC Certification Benchmark card for intended use, included fields, metrics, and caveats.
- `docs/limitations.md`: scope boundaries, refusal interpretation, and public-safe packaging limits.
- `docs/artifact_index.md`: milestone-level artifact map, including paper-ready materials figures, refusal diagnosis, success-domain predictor, and validity-assumption tables.

## Main Frozen Artifacts

- Final reliability milestone: `outputs/milestones/reliability_fortress/`
- Generality and stratified reliability milestone: `outputs/milestones/generality_reliability/`
- Release/refusal story milestone: `outputs/milestones/release_story/`
- Biomedical scientific-domain milestone: `outputs/milestones/scientific_domain_ctc/`
- Learned-hybrid CTC milestone: `outputs/milestones/scientific_domain_ctc_learned/` (strict `alpha=0.10` release, leakage audit, reverse split, and random-score negative control)
- CTC strict human-audit closeout: `outputs/milestones/ctc_strict_human_audit/` (2,564 human-confirmed link labels; strict release queue human FTR 0.0; no separate expert-audit claim)
- Earth-observation scientific-domain milestone: `outputs/milestones/scientific_domain_spacenet7/`
- Prospective SpaceNet 7 audit trial: `outputs/milestones/scientific_domain_spacenet7_prospective/`
- Prospective iWildCam animal-present audit trial: `outputs/milestones/scientific_domain_iwildcam_human_audit/` (operational `alpha=0.20, K=50` human-confirmed ecology release; strict `alpha=0.10` refusal)
- Materials discovery milestone: `outputs/milestones/scientific_domain_materials/` (Matbench Discovery / WBM stable-candidate release; CGCNN strict `alpha=0.10, K=100` flagship with controls; paper-ready threshold, gamma, and raw-vs-PARC figures)
- Scientific release success map: `outputs/milestones/scientific_release_success_map/` (cross-domain evidence matrix, success/refusal diagnostics, ILP/refusal diagnosis, verified-positive-removal load-bearing reruns, descriptive success-domain predictor, validity-assumption table, practical-value rows, and protocol-only flags for unfinished extensions)
- No-human scientific consequence milestone: `outputs/milestones/no_human_scientific_consequence/` (materials computational follow-up queue, materials model-zoo release frontier, CTC lineage consequence, and SpaceNet map-consequence diagnostics using public/official labels only)
- Community benchmark: `outputs/benchmarks/parc_certification_benchmark/`
- File integrity manifest: `MANIFEST_SHA256.txt`

## Citation

A formal citation will be added after archival release. Until then, cite the repository title and commit hash.
