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
│   ├── milestones/materials_computational_followup_trial/
│   ├── milestones/official_downstream_consequence/
│   ├── milestones/release_certification_benchmark/
│   ├── milestones/block_heterogeneity_robustness/
│   ├── milestones/materials_prospective_validation_protocols/
│   ├── milestones/materials_prospective_dft_followup/
│   ├── milestones/materials_prospective_dft_followup_chgnet_v2/
│   ├── milestones/materials_prospective_dft_followup_chgnet_v3/
│   ├── milestones/mattergen_parc_prospective_dft_followup/
│   ├── milestones/fixed_budget_downstream_utility/
│   ├── milestones/primary_statistics/
│   ├── milestones/materials_robustness_triad/
│   ├── milestones/baseline_matrix_final/
│   ├── milestones/ctc_strict_anchor/
│   ├── milestones/iwildcam_audit_final/
│   ├── milestones/spacenet_real_audit_final/
│   ├── milestones/materials_temporal_validation/
│   ├── milestones/materials_independent_dft_validation/
│   ├── milestones/materials_alex_mp_a1_a2_validation/
│   ├── milestones/main_evidence_hard_upgrade_phase30/
│   ├── milestones/materials_source_discordance_stress_test/
│   ├── milestones/ctc_decision_utility_main_evidence/
│   ├── milestones/cross_domain_blind_audit_main_evidence/
│   ├── milestones/protocol_claim_alignment/
│   ├── milestones/materials_fixed_budget_scientific_utility/
│   ├── milestones/ctc_scientific_artifact_consequence/
│   ├── milestones/nmi_presubmission_package/
│   ├── milestones/nmi_presubmission_final/
│   ├── milestones/materials_label_discordance_preregistration/
│   ├── milestones/materials_selection_conditional_discordance/
│   ├── milestones/ncs_week0_protocol_freeze/
│   ├── milestones/materials_temporal_mlip_audit/
│   ├── milestones/pre_release_repository_cleanup/
│   ├── milestones/reproducibility_freeze/
│   └── benchmarks/parc_certification_benchmark/
├── tests/                            # pytest suite and tiny fixtures
├── scripts/                          # public-safe helper scripts
├── tools/                            # notes for external metric/export tooling
└── docs/                             # API, audit protocol, getting started
```

## What Is Included

- PARC certification code: null-superset block calibration, coverage-conditional empty-block handling, e-value generation, finite-resolution diagnostics, SCS-Greedy release, report builders, TrackEval export helpers, and adapter utilities.
- Audit benchmark: `outputs/benchmarks/parc_certification_benchmark/audit/` and the full frozen milestone under `outputs/milestones/reliability_fortress/`.
- Materials-label discordance preregistration: `outputs/milestones/materials_label_discordance_preregistration/` defines a separate go/no-go route for testing public DFT label reproducibility. It is protocol-only and contains no API keys, no new positive evidence, and no prospective-discovery claim.
- Selection-conditional discordance go/no-go: `outputs/milestones/materials_selection_conditional_discordance/` tests whether MP-vs-alex discordance is amplified in the high-confidence score strata of ALIGNN-FF, CHGNet, and MACE-MP. It is a completed negative diagnostic, not a new materials-discovery claim.
- Scientific-domain milestones for CTC cell-link certification, learned-hybrid CTC link certification, SpaceNet 7 building-link certification, a prospective iWildCam animal-present human-audit package, and Matbench Discovery stable-material candidate release.
- Release-certification benchmark cards that package completed CTC, materials, iWildCam, SpaceNet, and downstream-artifact evidence into a reusable scientific AI governance protocol.
- Block-heterogeneity robustness diagnostics for the current public artifact package: candidate-level size-stratified, size-matched, and downsampled block-max checks for materials, plus scoped aggregate/audit-sample diagnostics for CTC and SpaceNet where candidate-level universes are not included.
- Preregistered A1/A2 materials prospective-validation protocols and feasibility cards. These are explicitly protocol/feasibility artifacts and are not promoted as completed positive evidence.
- Completed A1/A2 external-source diagnostics for OQMD and alex-mp. The alex-mp exact-structure coverage is higher than OQMD but the labels are discordant and do not support a positive independent-validation claim; the package records this as a source-discordance stress test, not a materials rescue result.
- Phase30 main-evidence hard-upgrade tables that pivot away from A3 dependency: CTC decision utility, completed cross-domain human-audit release/refusal behavior, and materials external-source discordance diagnostics.
- Phase33 final NMI presubmission go/no-go package: compressed inquiry, final abstract, evidence table, forbidden claims, cold read, cover-letter positioning, and PASS checklist.
- Phase32 NMI presubmission package: editor-facing inquiry, abstract draft, one-page evidence table, desk-risk cold read, referee rationale, and positioning guardrails built from phase31-approved claims only.
- Phase31 protocol/claim-alignment guardrails: every candidate headline result is assigned an allowed manuscript role; primary-headline rows require completed artifacts, source SHA256 hashes, and exact manuscript sentences; `docs/abstract_claim_scope.md` forbids prospective materials-discovery language unless A3 DFT gates are met.
- A3 prospective in-silico DFT follow-up gates. Earlier ALIGNN-FF/CHGNet gates are retained only as scoped no-go diagnostics. The current MatterGen v4 gate has a frozen public-label-excluded selection, DFT run package, and local Quantum ESPRESSO input layer, but it still contains no DFT outcomes and no completed prospective materials-discovery result.
- Pre-release repository cleanup records under `outputs/milestones/pre_release_repository_cleanup/`. These document the removal of obsolete legacy dumps, prefill/draft label aids, generated archive packages, and local runtime scratch files while preserving final evidence and claim-boundary guardrails.
- Experiment-finalization milestones for materials temporal/independent-source feasibility, fixed-budget downstream utility, primary statistics, materials robustness, baseline matrix, CTC strict-anchor finalization, iWildCam/SpaceNet audit finalization, and reproducibility freeze. These milestones preserve the completed/diagnostic/protocol-only evidence distinction.
- Paper-facing result tables for the retained OVT-B/TAO/BURST, black-box generator, published-tracker, LVIS/LVVIS/OVIS, stress-test, and success-domain evidence. Obsolete internal legacy dumps are removed from the pre-release tree; regenerated packages should be created with `make package-release` rather than tracked as tarballs.
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
- No-human scientific consequence milestone: `outputs/milestones/no_human_scientific_consequence/` (materials computational follow-up queue, materials model-zoo release frontier, CTC lineage consequence, SpaceNet map-consequence diagnostics, paper-facing Figure 6 source, and impact-first cover-letter text using public/official labels only)
- Materials computational follow-up trial: `outputs/milestones/materials_computational_followup_trial/` (quasi-prospective public-DFT replay with frozen queues/rules, release cards, and follow-up efficiency figures; no new DFT or synthesis claim)
- Official downstream consequence milestone: `outputs/milestones/official_downstream_consequence/` (CTC official-GT lineage-edge edit-burden proxies and SpaceNet 7 official-identity building-persistence map metrics; no new human labels and no official challenge leaderboard-score claim)
- Release certification benchmark cards: `outputs/milestones/release_certification_benchmark/` (community-facing release cards, track registry, field schema, governance checklist, and benchmark map; only completed evidence/diagnostics are promoted, while protocol-only ideas remain schema/checklist items)
- Block heterogeneity robustness: `outputs/milestones/block_heterogeneity_robustness/` (Phase25 size-stratified p-value diagnostics, candidate-level materials size-matched and downsampled block-max stress, scoped CTC/SpaceNet diagnostics, and an approximate e-value validity lemma)
- Materials prospective validation protocols: `outputs/milestones/materials_prospective_validation_protocols/` (A1 temporal-split and A2 independent-DFT preregistration protocols plus feasibility/go-no-go cards; protocol-only, not completed evidence)
- Materials prospective DFT follow-up protocol: `outputs/milestones/materials_prospective_dft_followup/` (A3 in-silico DFT follow-up protocol freeze, arm plan, failure policy, empty candidate/selection/job schemas, and input-gate closeout; no new DFT outcomes and no completed positive result)
- Experimental execution plan: `docs/experimental_execution_plan.md` (experiment-only P0/P1/P2 execution map and evidence-state rules)
- Fixed-budget downstream utility: `outputs/milestones/fixed_budget_downstream_utility/` (completed public-label and official-GT consequence tables for materials follow-up queues, CTC lineage graph consequences, SpaceNet persistence-map consequences, and baseline frontier source data)
- Primary statistics: `outputs/milestones/primary_statistics/` (paired seed-level materials effect sizes, bootstrap intervals, descriptive sign tests, Holm correction, and zero-FTR audit intervals)
- Materials robustness triad: `outputs/milestones/materials_robustness_triad/` (stability-definition, block-definition, gamma, and block-size heterogeneity source tables)
- Baseline matrix final: `outputs/milestones/baseline_matrix_final/` (target-object properties, PU/selective-conformal/e-BH/raw/threshold baseline tables, and load-bearing ablation references)
- CTC strict anchor final: `outputs/milestones/ctc_strict_anchor/` (leakage audit, reverse split, completed random-score control, protocol-only extra destroyed-ranking controls, and high-volume refusal consequence)
- iWildCam and SpaceNet final audit packages: `outputs/milestones/iwildcam_audit_final/` and `outputs/milestones/spacenet_real_audit_final/` (human-audit operational ecology row, SpaceNet K=100 refusal and K=50 diagnostic release)
- Materials A1/A2 finalization packages: `outputs/milestones/materials_temporal_validation/` and `outputs/milestones/materials_independent_dft_validation/` (A1 remains protocol-only; A2 now contains a completed low-coverage OQMD exact-structure diagnostic, not a primary independent validation result)
- Materials queue source-uncertainty overlay: `outputs/milestones/materials_queue_source_uncertainty_overlay/` (candidate-level ALIGNN-FF K=300/500 queue overlay against alex-mp exact-structure diagnostics; diagnostic only, not positive independent validation or prospective discovery)
- Submission scope lock: `outputs/milestones/submission_scope_lock_phase37/` (two-anchor evidence hierarchy, release/refuse contract comparator, and forbidden-claim replacements; no new experiment)
- NCS/NMI Week 0 protocol freeze: `outputs/milestones/ncs_week0_protocol_freeze/` (timestamped protocol PDF, frozen candidate universes, model scores, PARC parameters, K/alpha grid, block definitions, DFT audit sampling scheme, t0/t1 hull definitions, MLIP audit models, CTC audit guidelines, and go/no-go rules; protocol-freeze only, no new evidence)
- Materials temporal + MLIP audit: `outputs/milestones/materials_temporal_mlip_audit/` (Week 1-4 follow-up from the frozen protocol; frozen CHGNet/MACE-MP/ALIGNN-FF scores give pre-outcome release-vs-tail directional support without creating DFT evidence; its original missing-snapshot temporal no-go is superseded by the current-MP hull-shift snapshot below)
- Materials t0/t1 snapshot acquisition: `outputs/milestones/materials_t0_t1_snapshot_acquisition/` (current Materials Project `2025.09.25` hull-shift audit for the frozen K=300/500 WBM queues; PARC release has lower conservative t1-hull FTR than raw top-K and stable-to-unstable drift is not more concentrated in PARC, but this is not a strict `alpha=0.10` temporal certificate and not prospective materials discovery)
- NCS Phase50/51 materials paperization: `outputs/milestones/ncs_phase50_materials_version_shift_paperization/` and `outputs/milestones/ncs_phase51_materials_t1_candidate_explanation/` (paper-facing current-MP version-shift figure inputs, six-display-item NCS plan, 150-word abstract draft, and candidate-level t1 explanation tables; Phase51 remains an ALIGNN/model-zoo explanation rather than a CHGNet/MACE consensus claim)
- NCS Phase53 CHGNet/MACE candidate audit: `outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit/` (real candidate-level CHGNet and MACE-MP score audit for 1,191 frozen WBM queue candidates; queue-level score-support proxies favor PARC release over raw-only extra-tail at K=300/500, while t1 false-case explanation remains only partial; raw MLIP energies are not reference-hull `e_above_hull`, DFT evidence, or prospective discovery)
- NCS Phase56/57 version-shift and baseline frontier: `outputs/milestones/ncs_phase56_version_shift_accounting/` and `outputs/milestones/ncs_phase57_t1_mlip_baseline_frontier/` (deterministic t0-to-t1 false-release accounting lemma plus t1/CHGNet-MACE baseline capability table; this explains current-label burden as t0 error plus reference-hull drift and preserves the boundary that PARC is certified stopping/refusal, not matched-volume ranking improvement)
- NCS Phase60 PARC-V support-gate audit: `outputs/milestones/ncs_phase60_parc_v_version_aware_release/` (a simple CHGNet/MACE version-aware support gate is non-empty but fails the predeclared headline threshold; it is a completed no-go/feasibility result, not a full SCS rerun, DFT result, t1 alpha certificate, or prospective materials discovery claim)
- NCS Phase61 PARC-M fusion audit: `outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion/` (fixed mixtures of original PARC evidence and ALIGNN/CHGNet/MACE score-derived e-proxies show a medium empirical t1 improvement, about 0.03-0.04 FTR, but fail theorem-grade/headline gates because auxiliary scores are queue-level proxies without full null-superset calibration)
- NCS Phase62 full-calibration MLIP e-values: `outputs/milestones/ncs_phase62_full_calibration_mlip_evalues/` (CHGNet and MACE-MP auxiliary scores are converted into full-calibration e-values over the frozen WBM one-per-composition-family calibration denominator, with target-overlap rows excluded; the source-availability blocker is resolved, but the headline method-upgrade gate still fails, so this remains a scoped diagnostic rather than DFT evidence, t1 alpha control, or prospective materials discovery)
- NCS Phase63 PARC-A active verification: `outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification/` (certificate-directed one-sided verification becomes a primary CTC method result: 0.5% score-targeted audit gives 20/20 safe nonempty K=100 release and 2,000 total released links with zero observed false releases, while matched-budget random audit remains empty; CTC K=300 is secondary support and materials active-audit rows remain boundary/calibration evidence, not prospective materials discovery)
- NCS Phase52/58 materials hardening: `outputs/milestones/ncs_phase52_materials_t1_uncertainty/` and `outputs/milestones/ncs_phase58_reproducibility_hardening/` (chemical-system bootstrap intervals, rank-bin randomization tests, reproduction cards, and an evidence-scope ledger with SHA256-backed overclaim guardrails, including the Phase53 CHGNet/MACE score-support boundary)
- Phase31 claim alignment: `outputs/milestones/protocol_claim_alignment/`, `outputs/milestones/materials_fixed_budget_scientific_utility/`, `outputs/milestones/ctc_scientific_artifact_consequence/`, and `docs/abstract_claim_scope.md` (claim role audit, fixed-budget materials lead numbers, CTC artifact consequence tables, and abstract-scope guardrails)
- Reproducibility freeze: `outputs/milestones/reproducibility_freeze/` and `outputs/artifact_index.csv` (experiment-finalization milestone index and validation commands)
- Materials prospective CHGNet v2 gate: `outputs/milestones/materials_prospective_dft_followup_chgnet_v2/` (locally executable CHGNet scorer on PGCGM candidates; PARC release remained empty, so no DFT jobs were exported)
- Materials prospective CHGNet v3 near-hull gate: `outputs/milestones/materials_prospective_dft_followup_chgnet_v3/` (5,000 near-hull isovalent/chemically similar substitutions scored by CHGNet; strict and operational predeclared endpoints all refused, so no DFT jobs were exported)
- Materials prospective MatterGen v4 gate: `outputs/milestones/mattergen_parc_prospective_dft_followup/` (formal public-label exclusion tables, CHGNet/MACE-MP consensus score tables, frozen pre-DFT release and extra-tail manifests, DFT run package, and local Quantum ESPRESSO input layer are recorded; raw generation/smoke intermediates are not tracked; no DFT outcomes are committed and no positive prospective materials result is claimed)
- Pre-release cleanup: `outputs/milestones/pre_release_repository_cleanup/` (records removed legacy/prefill/draft/package artifacts and kept formal evidence)
- Community benchmark: `outputs/benchmarks/parc_certification_benchmark/`
- File integrity manifest: `MANIFEST_SHA256.txt`

## Citation

A formal citation will be added after archival release. Until then, cite the repository title and commit hash.


- A3-v4 formal selection gate: MatterGen 5k generation/scoring is completed as a diagnostic, and an available-source pre-DFT release-only selection gate is frozen without claiming prospective materials discovery.

- A3-v4 Phase29b manifest addendum: a pre-outcome DFT manifest addendum exports the full PARC release arm and a matched raw_topR arm. The matched arm is identical to the release set here and no DFT outcome or positive prospective materials claim is made.

- A3-v4 Phase29c extra-tail manifest: 25 formal raw-top100 extra-tail candidates are frozen before DFT outcomes; no DFT outcome or prospective materials claim is made.

- A3 DFT run package: `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_DFT_RUN_PACKAGE/` contains 75 PARC-release CIFs, 25 raw-top100 extra-tail CIFs, frozen manifests, protocol/settings templates, and package hashes. It contains no DFT outcomes and no prospective materials claim.

- A3 QE local run layer: `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/` contains Quantum ESPRESSO input decks, a pseudopotential mapping/hash table, and tmux launch scripts for the frozen A3 package. Third-party pseudopotential payload files and runtime `qe_outputs/` are intentionally ignored until outcomes are formally analyzed. It contains no committed DFT outcomes and no prospective materials claim.

- NCS Phase64 PARC-R versioned recertification: queue-limited current-MP recertification refuses unsafe old materials releases rather than inheriting them.

- NCS Phase65 PARC-A certificate-directed policy: compares random, score-targeted, block-max-gain, mass-gain, and diversity-mass-gain audit acquisition on the CTC primary row.
