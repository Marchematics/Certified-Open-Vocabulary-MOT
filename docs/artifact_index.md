# Artifact Index

This repository uses neutral public artifact names. Older internal experiment labels are retained only in raw provenance tables when needed to trace history; paper-facing documentation and tables should use the paths below.

## Main Public Artifacts

- `outputs/milestones/reliability_fortress/`
  Frozen reliability experiment bundle: Audit2000, second-review evidence, core OVT-B/TAO/BURST certification results, stress tests, diagnostics, and sanitized paper-facing closeout tables.

- `outputs/benchmarks/parc_certification_benchmark/`
  Public-safe community benchmark package with schemas, tiny fixtures, audit protocol, and reproducibility metadata.

- `outputs/milestones/generality_reliability/`
  Generality and stratified reliability artifacts for non-tracking and visual-difficulty analyses.

- `outputs/milestones/release_story/`
  Compact release/refusal story tables and qualitative-example manifest used to explain deployment value.

- `outputs/milestones/scientific_domain_ctc/`
  Biomedical cell-link certification milestone on Cell Tracking Challenge data. This is a scientific-domain positive anchor for link-level release certification under partial verification.

- `outputs/milestones/scientific_domain_ctc_learned/`
  Learned-hybrid CTC companion milestone. A sequence-disjoint, appearance-assisted link scorer is trained on CTC sequence 01, frozen, and certified on held-out sequence 02; only compact tables and model/provenance summaries are included. The milestone also includes leakage checks, reverse split sensitivity, and a random-score negative control.

- `outputs/milestones/scientific_domain_spacenet7/`
  Earth-observation building-link certification milestone on SpaceNet 7. This contains the geometry-linker positive result and randomized-linker safe-refusal stress result; raw SpaceNet labels, imagery, and large candidate universes are excluded.

- `outputs/milestones/scientific_domain_spacenet7_prospective/`
  Prospective SpaceNet 7 audit-trial package. This freezes the predeclared human-audit endpoint hierarchy and provides candidate-disjoint blind audit sheets plus proxy planning diagnostics. The closeout marks the trial as no-go for second-flagship promotion unless future human labels satisfy the predeclared gate.

- `outputs/milestones/scientific_domain_iwildcam_human_audit/`
  Prospective iWildCam animal-present audit-trial package. This freezes a camera-trap ecology trial with location-by-time blocks, blind calibration/release audit sheets, proxy-only planning diagnostics, and a random-score control. It is pending human audit and must not be treated as a human-audited flagship result until the `human_*` fields are confirmed.

- `outputs/milestones/release_story/paper_diagnostics/`
  Paper-facing diagnostic tables for assumptions, seed variability/interval summaries, verification budgets, and prevented false releases.

## Paper-Facing Tables

The cleaned main tables live under:

```text
outputs/milestones/reliability_fortress/paper_tables/
```

These tables are derived from raw provenance tables and intentionally omit internal status tags, local temporary paths, and published-tracker rows that do not have complete official prediction provenance.

## Safety Policy

Public packages do not include raw videos, raw annotations, detector/tracker weights, Hugging Face caches, GPU caches, frame caches, or montage image files. Visual examples are represented by public-safe manifests only.
