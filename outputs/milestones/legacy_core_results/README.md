# Legacy Core Results Ledger v1

This public-safe ledger preserves early PARC-Track result assets that were useful for paper writing before the final journal/generality/LVVIS/OVIS milestones were frozen. It is intentionally derived-only: no raw videos, raw annotations, model weights, detector caches, or frame caches are included. Local absolute paths were sanitized to placeholders such as `<PARC_ROOT>`.

## Why This Exists

The repository tracks the final milestone packages, including `reliability_fortress`, `generality_reliability`, `ovis_certification_v1`, `lvvis_certification_v1`, `lvvis_mask_certification_v1`, and the public benchmark package. This ledger adds table-level coverage for earlier evidence points such as the first real non-empty OVT-B certification, release-core alpha/M/seed tables, TAO cross-dataset development tables, BURST development tables, and OWLv2/OWL-ViT diagnostic assets.

## Included Source Milestones

- `phase2h_first_real_nonempty`: first real non-empty OVT-B certification milestone
- `core_results`: early OVT-B alpha/seed/M/baseline release-core tables
- `reliability_fortress_draft`: pre-v2 reliability fortress design/results scaffold
- `ijcv_tao_full_v2_clean`: clean TAO full matrix tables
- `cross_dataset`: OVT-B/TAO cross-dataset certification and audit tables
- `stability`: stability evidence: anytime, bootstrap CI, Mondrian, per-class, worst-case FTR
- `burst`: BURST third-dataset certification and audit tables
- `ijcv_burst_cv60_v1`: BURST 60-path cross-validation audit agreement
- `ijcv_burst_owlv2_stress_v1`: BURST OWLv2 stress-test tables
- `owlv2_diagnostic_v1`: OWLv2 failure/small-M/rerank diagnostics
- `phase4_prop5_three_generator_v1`: Proposition 5 three-generator validation
- `phase4_third_generator_and_owlv2_audit`: OWL-ViT/OWLv2 audit support assets
- `phase4_third_generator_matrix`: OWL-ViT third-generator fixed-M matrix
- `cross_generator`: early cross-generator table and configs
- `ovtrack_adapter`: published tracker adapter scaffold/status
- `phase4_sprint`: phase-4 sprint manifest and report bundle
- `extra_cpu`: extra CPU experiment manifest bundle
- `trackeval_v1`: TrackEval export status manifest and derived metrics tables

## Inventory

- Copied public-safe files: `344`
- Local milestone coverage table: `table_local_milestone_cloud_coverage.csv`
- Per-file manifest: `table_legacy_resource_manifest.csv`
- SHA256 manifest: `MANIFEST_SHA256.txt`
- Safety report: `NO_RAW_DATA_SAFETY_REPORT.json`

## Main Early Evidence Preserved

- First real non-empty OVT-B certification: `phase2h_first_real_nonempty/table_real_first_nonempty.csv` and related release/audit tables.
- Early OVT-B fixed-M, alpha, seed, baseline, and best-M diagnostic tables: `core_results/`.
- TAO and OVT-B cross-dataset certification summaries: `cross_dataset/`.
- BURST third-dataset development and audit summaries: `burst/`.
- Stability assets: anytime release, bootstrap CI, Mondrian, per-class, and worst-case FTR tables from `stability/`.
- OWLv2, OWL-ViT, and published-tracker adapter diagnostics.

## Superseded Local Milestones

Earlier local milestones such as `core_results`, `ijcv_cross_dataset_v1`-`v5`, `ijcv_tao_full_v1`, `stability`, and `burst` are represented by later cleaned/frozen versions in this ledger or by primary tracked milestones.
