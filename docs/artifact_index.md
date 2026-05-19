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

- `outputs/milestones/ctc_strict_human_audit/`
  Human-confirmed CTC strict audit closeout derived from the learned-hybrid CTC audit queue. It contains 2,564 reviewed adjacent-frame cell-link labels, including 1,500 calibration candidates, 1,064 simulated strict-release candidates, and 300 raw top-K reference candidates. The strict-release queue has human FTR 0.0 and conservative uncertain-as-false FTR 0.0. This milestone does not claim microscopy-expert adjudication unless a separate expert review is documented.

- `outputs/milestones/scientific_domain_spacenet7/`
  Earth-observation building-link certification milestone on SpaceNet 7. This contains the geometry-linker positive result and randomized-linker safe-refusal stress result; raw SpaceNet labels, imagery, and large candidate universes are excluded.

- `outputs/milestones/scientific_domain_spacenet7_prospective/`
  Prospective SpaceNet 7 audit-trial package. This freezes the predeclared human-audit endpoint hierarchy and provides candidate-disjoint blind audit sheets plus proxy planning diagnostics. The closeout marks the trial as no-go for second-flagship promotion unless future human labels satisfy the predeclared gate.

- `outputs/milestones/scientific_domain_iwildcam_human_audit/`
  Prospective iWildCam animal-present audit-trial package. This freezes a camera-trap ecology trial with location-by-time blocks, human-confirmed calibration/release audit sheets, proxy diagnostics, and a random-score control. The closeout supports an operational `alpha=0.20, K=50` ecology release with human FTR 0.0; strict `alpha=0.10` remains certified refusal.

- `outputs/milestones/scientific_domain_materials/`
  Materials-discovery candidate-release milestone on public Matbench Discovery / WBM tables. A CGCNN learned materials model proposes stable-crystal candidates, PARC observes only masked DFT-stable positives, and the milestone reports strict `alpha=0.10` release at `K=100` plus weak-model, random-score, high-volume, block-sensitivity, and leakage diagnostics. It now also includes paper-ready figure source/PDF artifacts: `materials_threshold_robustness_figure.*`, `materials_gamma_sensitivity_heatmap.*`, and `materials_raw_vs_parc_ftr_panel.*`.

- `outputs/milestones/scientific_release_success_map/`
  Cross-domain evidence matrix and domain-of-success diagnostics. This milestone consolidates completed CTC, materials, iWildCam, SpaceNet, near-boundary, audit-contamination, and verified-positive-removal load-bearing rows into a paper-facing success/refusal map, while marking strict real-audit extensions and new candidate domains as protocol-only when they have not been run. It includes `table_refusal_diagnosis_ilp.csv`, `table_verified_positive_removal_load_bearing.csv`, `table_success_domain_predictor.csv`, `table_success_domain_rules.csv`, `figure_success_domain_map.*`, and `table_validity_assumptions_by_domain.csv`.

- `outputs/milestones/no_human_scientific_consequence/`
  No-human scientific consequence diagnostics. This milestone uses public WBM/Matbench labels, public model prediction CSVs, CTC official GT labels, and SpaceNet 7 official building identities to quantify downstream follow-up consequences without adding human labels. It includes materials computational follow-up queues, a materials model-zoo release frontier, CTC lineage-edge consequence diagnostics, SpaceNet building-persistence map-consequence diagnostics, a paper-facing no-human consequence summary, Figure 6 source/PDF, and impact-first Results/cover-letter text. Missing CHGNet/MACE/M3GNet/ORB/SevenNet/EquiformerV2/MatterSim prediction files are recorded as not-run availability rows, not completed evidence.

- `outputs/milestones/materials_computational_followup_trial/`
  Quasi-prospective public-DFT materials computational follow-up replay. This milestone freezes model-ranked WBM candidate queues, composition-family block splits, one-sided pre-release DFT-positive verification, requested budgets, and PARC release/refusal rules before evaluating held-out follow-up labels. It includes `table_materials_computational_trial_summary.csv`, seed-level results, release cards, a protocol JSON, and `figure_materials_computational_trial_main.{csv,pdf}`. It explicitly does not claim new DFT, experimental synthesis, or true prospective discovery.

- `outputs/milestones/official_downstream_consequence/`
  Official-label downstream artifact metrics for CTC and SpaceNet 7. This milestone translates release/refusal decisions into the artifacts a downstream workflow would consume: CTC lineage graphs and SpaceNet building-persistence maps. It includes `table_ctc_official_lineage_metric_summary.csv`, `table_spacenet_map_metric_summary.csv`, `table_official_downstream_consequence_summary.csv`, and `figure_official_downstream_consequence.{csv,pdf}`. CTC TRA/AOGM-style values are edge-edit burden proxies and should not be described as official challenge leaderboard scores.

- `outputs/milestones/release_certification_benchmark/`
  Community-facing scientific AI release-certification benchmark cards. This milestone packages completed release/refusal evidence into `table_release_certification_cards.csv`, `table_release_certification_track_registry.csv`, `table_release_card_field_schema.csv`, `table_release_governance_checklist.csv`, `table_release_certification_benchmark_index.csv`, and `figure_release_certification_benchmark_map.{csv,pdf}`. It is a reusable governance protocol for future candidate-release tasks and does not promote protocol-only ideas as completed evidence.

- `outputs/milestones/block_heterogeneity_robustness/`
  Phase25 block-size heterogeneity robustness milestone. It contains `table_block_size_heterogeneity_summary.csv`, `figure_block_size_superuniformity.{csv,pdf}`, `table_size_matched_rerun.csv`, `table_downsampled_blockmax_stress.csv`, `BLOCK_HETEROGENEITY_ROBUSTNESS_CLOSEOUT.md`, and `B2_APPROXIMATE_EVALUE_VALIDITY_LEMMA.md`. Candidate-level size-matched and downsampled reruns are completed for materials, where block/score/label artifacts are public-safe; CTC and SpaceNet are explicitly scoped as aggregate/audit-sample diagnostics rather than fabricated candidate-level reruns.

- `outputs/milestones/materials_prospective_validation_protocols/`
  A1/A2 materials prospective-validation preregistration and feasibility package. It contains temporal-split and independent-DFT protocols, feasibility tables, release-card stubs, and go/no-go decisions. These artifacts are protocol/feasibility evidence only: they do not claim a completed prospective computational trial, new DFT labels, or an independent-DFT cross-validation result.

- `outputs/milestones/materials_independent_dft_validation/`
  A2 independent-source diagnostic package. It reconstructs the frozen ALIGNN-FF `alpha=0.10, K=300` WBM release row, queries OQMD after release reconstruction, and reports only exact reduced-formula plus `StructureMatcher` matches as independent FTR evidence. Coverage is low, so this is a completed diagnostic and source-coverage audit, not a primary independent validation result.

- `outputs/milestones/materials_prospective_dft_followup/`
  A3 prospective in-silico DFT follow-up protocol freeze. It contains `PROTOCOL.md`, `protocol.yaml`, `candidate_universe_frozen.csv`, `selection_frozen.csv`, `dft_job_manifest.csv`, public-label and novelty-crossmatch schemas, the DFT failure policy, and `MATERIALS_PROSPECTIVE_DFT_FOLLOWUP_CLOSEOUT.md`. In the current public package the unlabeled generated crystal pool is not supplied, so candidate selection and DFT job export are intentionally empty and must not be reported as a completed DFT follow-up result.

- `outputs/milestones/materials_prospective_dft_followup_chgnet_v2/`
  A3-v2 locally executable CHGNet prospective scorer gate. It records the blocked ALIGNN-FF status, scores WBM calibration representatives and PGCGM generated candidates with `CHGNet.load()`, and keeps `selection_frozen_chgnet_v2.csv` / `dft_job_manifest_chgnet_v2.csv` empty because the predeclared release arm is unsupported. This is a no-go diagnostic, not DFT evidence.

- `outputs/milestones/materials_prospective_dft_followup_chgnet_v3/`
  A3-v3 near-hull parent-prototype substitution gate. It contains `protocol_v3_chgnet_near_hull.yaml`, `candidate_universe_chgnet_v3.csv`, `candidate_scores_chgnet_v3.csv`, `table_chgnet_v3_endpoint_diagnostics.csv`, `selection_frozen_chgnet_v3.csv`, `dft_job_manifest_chgnet_v3.csv`, and `CHGNET_V3_CLOSEOUT.md`. It generates 5,000 public-label-excluded near-hull candidates and scores them with CHGNet, but strict and operational endpoints all refuse, so no DFT jobs are exported.

- `outputs/milestones/mattergen_parc_prospective_dft_followup/`
  A3-v4 frontier-generator prospective DFT gate. It contains `PROTOCOL.md`, `protocol_v4_mattergen.yaml`, formal public-label exclusion tables, CHGNet/MACE-MP consensus score tables, frozen `selection_frozen_v4.csv`, frozen DFT manifests, `A3_DFT_RUN_PACKAGE/`, and `A3_QE_LOCAL_RUN/`. Raw generation/smoke intermediates and third-party QE pseudopotential payloads are not tracked in the pre-release Git tree. It is a pre-outcome execution package: no DFT outcome is committed and no positive prospective materials result is claimed.

- `outputs/milestones/pre_release_repository_cleanup/`
  Pre-release repository-normalization record. It documents removed legacy dumps, prefill/draft label aids, generated archive packages, and runtime scratch files while recording the formal artifacts that remain claim-bearing. This is a hygiene milestone, not new scientific evidence.

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

Generated tarball packages under `outputs/packages/` are not tracked in the
pre-release tree. Recreate them with `make package-release` only when a release
archive is needed.
