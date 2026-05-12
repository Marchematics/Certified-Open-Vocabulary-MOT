# Legacy Core Results Ledger v1

This public-safe ledger preserves early PARC-Track result assets that were useful for paper writing before the final TPAMI/NMI/LVVIS/OVIS milestones were frozen. It is intentionally derived-only: no raw videos, raw annotations, model weights, detector caches, or frame caches are included. Local absolute paths were sanitized to placeholders such as `<PARC_ROOT>`.

## Why This Exists

The repository tracks the final milestone packages, including `tpami_reliability_fortress_v2`, `nmi_generality_reliability_v1`, `ovis_certification_v1`, `lvvis_certification_v1`, `lvvis_mask_certification_v1`, and the public benchmark package. This ledger adds table-level coverage for earlier evidence points such as the first real non-empty OVT-B certification, TPAMI-core alpha/M/seed tables, TAO cross-dataset development tables, BURST development tables, and OWLv2/OWL-ViT diagnostic assets.

## Included Source Milestones

- `phase2h_first_real_nonempty`: first real non-empty OVT-B certification milestone
- `tpami_core_v2`: early OVT-B alpha/seed/M/baseline TPAMI-core tables
- `tpami_reliability_fortress_v1`: pre-v2 reliability fortress design/results scaffold
- `ijcv_tao_full_v2_clean`: clean TAO full matrix tables
- `ijcv_cross_dataset_v6`: OVT-B/TAO cross-dataset certification and audit tables
- `ijcv_stability_v2`: stability evidence: anytime, bootstrap CI, Mondrian, per-class, worst-case FTR
- `ijcv_burst_v2`: BURST third-dataset certification and audit tables
- `ijcv_burst_cv60_v1`: BURST 60-path cross-validation audit agreement
- `ijcv_burst_owlv2_stress_v1`: BURST OWLv2 stress-test tables
- `owlv2_diagnostic_v1`: OWLv2 failure/small-M/rerank diagnostics
- `phase4_prop5_three_generator_v1`: Proposition 5 three-generator validation
- `phase4_third_generator_and_owlv2_audit_v1`: OWL-ViT/OWLv2 audit support assets
- `phase4_third_generator_matrix_v1`: OWL-ViT third-generator fixed-M matrix
- `ijcv_cross_generator_v1`: early cross-generator table and configs
- `ijcv_ovtrack_adapter_v1`: published tracker adapter scaffold/status
- `ijcv_phase4_sprint_v1`: phase-4 sprint manifest and report bundle
- `ijcv_extra_cpu_v1`: extra CPU experiment manifest bundle
- `trackeval_v1`: TrackEval export status manifest and derived metrics tables

## Inventory

- Copied public-safe files: `344`
- Local milestone coverage table: `table_local_milestone_cloud_coverage.csv`
- Per-file manifest: `table_legacy_resource_manifest.csv`
- SHA256 manifest: `MANIFEST_SHA256.txt`
- Safety report: `NO_RAW_DATA_SAFETY_REPORT.json`

## Main Early Evidence Preserved

- First real non-empty OVT-B certification: `phase2h_first_real_nonempty/table_real_first_nonempty.csv` and related release/audit tables.
- Early OVT-B fixed-M, alpha, seed, baseline, and best-M diagnostic tables: `tpami_core_v2/`.
- TAO and OVT-B cross-dataset certification summaries: `ijcv_cross_dataset_v6/`.
- BURST third-dataset development and audit summaries: `ijcv_burst_v2/`.
- Stability assets: anytime release, bootstrap CI, Mondrian, per-class, and worst-case FTR tables from `ijcv_stability_v2/`.
- OWLv2, OWL-ViT, and published-tracker adapter diagnostics.

## Superseded Local Milestones

Earlier local milestones such as `tpami_core_v1`, `ijcv_cross_dataset_v1`-`v5`, `ijcv_tao_full_v1`, `ijcv_stability_v1`, and `ijcv_burst_v1` are represented by later cleaned/frozen versions in this ledger or by primary tracked milestones.
