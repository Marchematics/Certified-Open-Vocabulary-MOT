# Experimental Execution Plan

This plan records the experiment-only work for the NMI-oriented PARC package. It intentionally excludes manuscript rewriting, abstract compression, figure narrative, and cover-letter work.

## Evidence-State Rule

Every generated artifact must declare one of three evidence states:

- `completed_evidence`: the table is computed from completed labels, official ground truth, public DFT labels, or completed human audit.
- `diagnostic`: the artifact is a stress test, dry run, feasibility check, or scoped diagnostic. It may inform next steps but is not a primary positive claim.
- `protocol_only`: parameters or protocols are frozen, but the required candidate pool, labels, external index, or DFT outcomes are not available. These files cannot be promoted into result claims.

Protocol-only and diagnostic rows must never be reported as completed positive evidence.

## Overall Goal

Move the repository from a broad retrospective release-certification package to a harder NMI evidence chain:

- deepen the materials-discovery line;
- keep CTC as the strict alpha=0.10 methodological anchor;
- keep iWildCam and SpaceNet as real-audit and refusal-boundary support;
- package every new artifact with manifests, tests, and public-safe validation.

PARC is evaluated as a release decision for a fixed finite candidate universe. The core practical contribution is certified stopping, refusal, and downstream consequence control, not fixed-size reranking improvement.

## P0-1 Materials A1/A2 Validation

### A1: Temporal Public-Label Split

Goal: simulate a quasi-prospective materials release decision by using only labels visible at snapshot `t0` for calibration and evaluating against labels visible at later snapshot `t1`.

Required inputs:

- `materials_snapshot_candidates.csv`
- `materials_label_snapshot_t0.csv`
- `materials_label_snapshot_t1.csv`

If no auditable timestamp or version metadata exists, A1 is downgraded to `protocol_only` or `diagnostic`, not completed evidence.

Fixed protocol:

- sources: ALIGNN-FF and CGCNN, with ALIGNN-FF preferred;
- unit: WBM unique prototype;
- target: DFT stable, `e_above_hull <= 0 eV/atom`;
- calibration labels: `t0` visible positives only;
- evaluation labels: `t1` held-out labels;
- alpha: 0.10 primary, 0.20 auxiliary;
- K: 100, 300, 500, 1000, 5000;
- rho: 0.10 primary, 0.20 auxiliary;
- seeds: 0 to 19;
- blocks: composition-family primary, chemical-system and Wyckoff-family sensitivity.

Deliverable:

`outputs/milestones/materials_temporal_validation/`

Required tables:

- `README.md`
- `temporal_protocol_freeze.md`
- `table_materials_temporal_feasibility.csv`
- `table_materials_temporal_primary.csv`
- `table_materials_temporal_seed_rows.csv`
- `table_materials_temporal_raw_vs_parc.csv`
- `table_materials_temporal_block_sensitivity.csv`
- `table_materials_temporal_refusal_diagnostics.csv`
- `figure_materials_temporal_utility_source.csv`
- `MANIFEST_SHA256.txt`

### A2: Independent DFT-Source Cross-Validation

Goal: evaluate PARC released candidates against an external DFT or stability source when available, reducing same-source replay risk.

External sources may include Materials Project, OQMD, AFLOW, Alexandria, NOMAD, or a separately computed DFT set. Structure matching must be frozen before evaluation.

Primary matching rule:

1. exact composition match;
2. high-confidence structure match;
3. only exact or high-confidence structure matches enter the primary A2 result;
4. composition-only matches are sensitivity diagnostics only.

Deliverable:

`outputs/milestones/materials_independent_dft_validation/`

Required tables:

- `independent_source_inventory.md`
- `structure_matching_protocol.md`
- `table_independent_dft_join_summary.csv`
- `table_independent_dft_primary_results.csv`
- `table_independent_dft_seed_rows.csv`
- `table_independent_dft_discordance.csv`
- `table_independent_dft_match_confidence_sensitivity.csv`
- `MANIFEST_SHA256.txt`

## P0-2 Fixed-Budget Downstream Utility

Goal: answer whether PARC changes downstream scientific objects at requested budgets rather than merely lowering FTR by issuing smaller sets.

Primary domain:

- Materials: DFT follow-up queue, unstable follow-up count, DFT job cost proxy.

Support domains:

- CTC: lineage graph, false lineage edges and corruption proxy.
- SpaceNet: building-persistence map, false persistence links.
- iWildCam: ecology release list, human audit labor and false animal-present release.

Methods:

- raw top-K;
- raw top-R matched-volume diagnostic;
- fixed threshold;
- calibrated threshold;
- split conformal candidate threshold;
- post-filter e-value;
- e-BH-style rule;
- PARC;
- PU and selective-conformal different-target baselines when available.

Deliverable:

`outputs/milestones/fixed_budget_downstream_utility/`

Required tables:

- `README.md`
- `table_materials_budget_utility_primary.csv`
- `table_materials_budget_utility_seed_rows.csv`
- `table_materials_baseline_frontier.csv`
- `table_materials_cost_proxy.csv`
- `table_ctc_lineage_consequence.csv`
- `table_spacenet_persistence_consequence.csv`
- `figure_fixed_budget_utility_source.csv`
- `figure_consequence_translation_source.csv`
- `MANIFEST_SHA256.txt`

## P0-3 Primary Statistics

Goal: produce a reviewer-facing endpoint table with effect sizes, intervals, paired tests, and claim scope.

Primary comparisons:

- Materials ALIGNN-FF K=300/500, PARC versus raw top-K on false follow-ups prevented.
- Materials high-volume K=5000, unsafe request blocked.
- CTC learned strict alpha=0.10, non-empty 20/20 and FTR <= alpha.

Secondary comparisons:

- PARC versus threshold;
- PARC versus e-BH-style;
- PARC versus PU and selective conformal;
- A1/A2 only if completed;
- iWildCam and SpaceNet audit release/refusal rows.

Deliverable:

`outputs/milestones/primary_statistics/`

Required files:

- `statistical_analysis_plan.md`
- `table_primary_endpoints.csv`
- `table_secondary_endpoints.csv`
- `table_paired_bootstrap_seed_rows.csv`
- `table_holm_correction.csv`
- `table_audit_zero_ftr_intervals.csv`
- `MANIFEST_SHA256.txt`

## P0-4 Materials Robustness Triad

Goal: prevent the materials result from depending on a single threshold, block definition, or gamma choice.

R1 stability definitions:

- exact stable;
- tolerance +25 meV;
- margin-excluded +/-25 meV;
- conservative clear-stable.

R2 block definitions:

- composition-family primary;
- chemical-system;
- Wyckoff-family;
- size-matched block max;
- downsampled block max.

R3 calibrator sensitivity:

- finite-resolution gamma primary;
- fixed gamma grid from 0.05 to 0.50;
- conservative gamma diagnostic.

Deliverable:

`outputs/milestones/materials_robustness_triad/`

Required files:

- `table_stability_definition_robustness.csv`
- `table_block_definition_robustness.csv`
- `table_gamma_sensitivity.csv`
- `table_block_size_heterogeneity.csv`
- `figure_materials_robustness_triad_source.csv`
- `robustness_claim_scope.md`
- `MANIFEST_SHA256.txt`

## P1-1 CTC Strict Anchor

Goal: seal the strict CTC anchor against leakage, split, score, and selector concerns.

Required components:

- leakage audit finalization;
- reverse split and seed reproducibility;
- destroyed-ranking controls;
- unsafe high-volume refusal consequence.

Deliverable:

`outputs/milestones/ctc_strict_anchor/`

Required files:

- `table_ctc_leakage_audit_final.csv`
- `ctc_feature_provenance.md`
- `table_ctc_primary_reverse_split_summary.csv`
- `table_ctc_primary_reverse_split_seed_rows.csv`
- `table_ctc_destroyed_ranking_controls.csv`
- `table_ctc_high_volume_refusal_consequence.csv`
- `MANIFEST_SHA256.txt`

## P1-2 iWildCam and SpaceNet Real-Audit Finalization

iWildCam is an operational alpha=0.20 human-audited ecology positive, not a strict alpha=0.10 flagship.

Required iWildCam values:

- release subset: 167/167 animal-present;
- second review: n=1123, disagreements=110;
- label agreement: 0.902;
- Cohen's kappa: 0.804, 95% CI [0.768, 0.838];
- strict alpha=0.10 rows refused;
- species-level metadata is invalid for localized one-sided support.

Deliverable:

`outputs/milestones/iwildcam_audit_final/`

SpaceNet is a real-audit release/refusal boundary:

- K=100 alpha=0.20 pre-registered human-audit request refused;
- K=50 alpha=0.20 diagnostic lower-volume release;
- 147 unique released candidates confirmed same-building;
- randomized linker refused.

Deliverable:

`outputs/milestones/spacenet_real_audit_final/`

## P1-3 Baseline Matrix

Goal: make comparator target objects explicit and avoid tautological claims.

Required baselines:

- raw top-K;
- raw top-R;
- fixed threshold;
- calibrated threshold;
- split conformal candidate threshold;
- post-filter e-value;
- e-BH-style;
- nnPU classifier-release;
- Bao-style selective conformal;
- oracle prefix diagnostic.

Deliverable:

`outputs/milestones/baseline_matrix_final/`

Required files:

- `baseline_protocol.md`
- `table_baseline_target_objects.csv`
- `table_baseline_primary_results.csv`
- `table_baseline_seed_rows.csv`
- `table_baseline_risk_utility_frontier.csv`
- `table_baseline_certificate_properties.csv`
- `figure_baseline_frontier_source.csv`
- `MANIFEST_SHA256.txt`

## P1-4 Load-Bearing Ablations

Goal: show that core PARC components are not decorative.

Required ablations when candidate-level evidence exists:

- without verified-positive removal;
- random positive removal;
- post-filter only without SCS;
- conservative empty-block policy;
- coverage-conditional policy;
- global calibration only;
- wrong uncertain removal diagnostic.

Existing completed candidate-level ablations must be used where available. Missing candidate-level artifacts must be marked as status rows rather than fabricated.

## P2 A3 DFT Pilot

A3 is conditional. It is not a blocker.

DFT follow-up can start only if all gates pass:

- true generated candidate pool;
- novelty and public-label exclusion;
- finite CHGNet/MACE/ALIGNN-FF score;
- non-empty PARC selection under frozen alpha/K/rho;
- DFT resources available;
- CIF/POSCAR/job manifest frozen before DFT outcome.

Current MatterGen A3-v4 smoke is diagnostic only unless full candidate generation, public-label exclusion, consensus scoring, non-empty selection, and DFT job export are complete.

Deliverable if gated:

`outputs/milestones/materials_prospective_dft_pilot/`

## P2 Open-World Breadth

Open-world/LVIS/mask-path work remains scoped breadth evidence only:

- LVIS GroundingDINO official-support proxy: Extended Data;
- OWLv2 stress and annotation-alignment case: Supplement;
- mask-path proof-of-principle: Supplement only.

No new open-world experiment is required for the current NMI evidence chain.

## Reproducibility Freeze

Every milestone must contain:

- `README.md` or `PROTOCOL.md`;
- primary result tables;
- seed rows when available;
- diagnostics;
- figure source data when relevant;
- provenance or claim-scope note;
- `MANIFEST_SHA256.txt`.

Root files to update:

- `README.md`;
- `REPRODUCIBILITY.md`;
- `DATA_AVAILABILITY.md`;
- `CODE_AVAILABILITY.md`;
- `docs/claim_table.md`;
- `docs/reviewer_guide.md`;
- `outputs/artifact_index.csv`;
- root `MANIFEST_SHA256.txt`.

Validation commands:

```bash
pytest -q tests
make reproduce-main-tables
make reproduce-main-figures
make validate-public-bundle
make verify-manifest
```

If some commands are unavailable in the public-safe package, record the attempted command and fallback validation.

## Submission Go / No-Go for Experiments

Go when:

1. Materials A1 or A2 is completed, or the retrospective fixed-budget utility/refusal consequence is strong and honestly scoped.
2. Materials K=300/500 raw top-K versus PARC has seed rows, intervals, and paired comparisons.
3. Matched-volume raw top-R is reported and PARC is not described as fixed-size ranking improvement.
4. CTC strict alpha=0.10 anchor has leakage audit, reverse split, and random-score controls.
5. iWildCam and SpaceNet are scoped as human-audit operating evidence and refusal boundary evidence.
6. Public bundle validation, manifests, tests, and figure/table sources pass.

No-go if:

1. A1/A2/A3 remain protocol-only while text claims prospective discovery.
2. Fixed-budget utility cannot show downstream release-decision value.
3. Primary statistics lack seed-level uncertainty or paired comparisons.
4. Baseline target objects remain ambiguous.
5. New experiment artifacts are not in manifest and reproducibility checks.
