# PARC Certification Benchmark Card

## Intended Use

The PARC Certification Benchmark is a public-safe package for testing
release-time certification workflows under incomplete annotations.  It is meant
for:

- validating PARC candidate schemas and CLI workflows;
- comparing release/refusal policies on frozen candidate universes;
- studying audit labels and false-tracklet taxonomy;
- building new candidate-release experiments without redistributing raw
  datasets.

## Included Assets

- Audit benchmark CSVs:
  `outputs/benchmarks/parc_certification_benchmark/audit/`
- Tiny fixture:
  `outputs/benchmarks/parc_certification_benchmark/tiny_fixture/`
- Public result tables:
  `outputs/benchmarks/parc_certification_benchmark/results/`
- API/schema documentation:
  `outputs/benchmarks/parc_certification_benchmark/schema/`
- Frozen scientific-domain milestones:
  `outputs/milestones/scientific_domain_*`,
  `outputs/milestones/ctc_strict_human_audit/`, and
  `outputs/milestones/scientific_release_success_map/`

## Excluded Assets

The benchmark does not include raw videos, raw microscopy images, raw satellite
imagery, raw dataset annotations, raw crystal structures, model weights,
detector/tracker caches, or montage images.  Users must obtain original data
from the maintainers of each dataset.

## Core Fields

Candidate-universe files generally contain:

- `path_id` or candidate ID;
- dataset/source identifiers;
- score fields from the frozen proposal source;
- frame/image/time indices;
- optional block identifiers;
- release/audit metadata in derived tables.

Audit files contain:

- label fields;
- verified-positive flags;
- confidence/reason fields when available;
- review status and disagreement/adjudication columns when applicable.

## Metrics

Common reported quantities:

- `PARC_release_size`;
- `PARC_FTR` or `human_FTR`;
- conservative uncertain-as-false FTR;
- raw top-K FTR;
- unsupported-track rate / UTR for visual benchmarks;
- evidence-mass and e-value diagnostics;
- block coverage and empty/refusal reasons.

## Caveats

- Tiny fixtures test code paths, not paper-scale statistical conclusions.
- Controlled partial-verification rows use held-out labels for evaluation and
  masked positives for PARC input.
- Human-audit rows should be interpreted according to their closeout documents;
  not every human-confirmed row is an expert-adjudicated row.
- Refusal rows are useful benchmark outcomes, not missing results.
