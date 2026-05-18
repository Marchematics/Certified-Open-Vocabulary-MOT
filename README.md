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
- Scientific-domain milestones for CTC cell-link certification, learned-hybrid CTC link certification, SpaceNet 7 building-link certification, a prospective iWildCam animal-present human-audit package, and Matbench Discovery stable-material candidate release.
- Release-certification benchmark cards that package completed CTC, materials, iWildCam, SpaceNet, and downstream-artifact evidence into a reusable scientific AI governance protocol.
- Block-heterogeneity robustness diagnostics for the current public artifact package: candidate-level size-stratified, size-matched, and downsampled block-max checks for materials, plus scoped aggregate/audit-sample diagnostics for CTC and SpaceNet where candidate-level universes are not included.
- Preregistered A1/A2 materials prospective-validation protocols and feasibility cards. These are explicitly protocol/feasibility artifacts and are not promoted as completed positive evidence.
- Completed A1/A2 external-source diagnostics for OQMD and alex-mp. The alex-mp exact-structure coverage is higher than OQMD but the labels are discordant and do not support a positive independent-validation claim; the package records this as a source-discordance stress test, not a materials rescue result.
- Phase30 main-evidence hard-upgrade tables that pivot away from A3 dependency: CTC decision utility, completed cross-domain human-audit release/refusal behavior, and materials external-source discordance diagnostics.
- Phase33 final NMI presubmission go/no-go package: compressed inquiry, final abstract, evidence table, forbidden claims, cold read, cover-letter positioning, and PASS checklist.
- Phase32 NMI presubmission package: editor-facing inquiry, abstract draft, one-page evidence table, desk-risk cold read, referee rationale, and positioning guardrails built from phase31-approved claims only.
- Phase31 protocol/claim-alignment guardrails: every candidate headline result is assigned an allowed manuscript role; primary-headline rows require completed artifacts, source SHA256 hashes, and exact manuscript sentences; `docs/abstract_claim_scope.md` forbids prospective materials-discovery language unless A3 DFT gates are met.
- A3 prospective in-silico DFT follow-up protocol gates. The ALIGNN-FF v1 package is a protocol-only blocked record; CHGNet v2 scores the PGCGM generated pool and CHGNet v3 scores a near-hull isovalent-substitution pool. Both CHGNet gates keep selection/job manifests empty when the predeclared release endpoints are unsupported. The MatterGen v4 gate records a locally smoke-tested MatterGen entrypoint and MACE-MP smoke test, but has not generated a candidate pool or exported DFT jobs. None of these A3 gates includes new DFT outcomes or a completed positive result.
- Experiment-finalization milestones for materials temporal/independent-source feasibility, fixed-budget downstream utility, primary statistics, materials robustness, baseline matrix, CTC strict-anchor finalization, iWildCam/SpaceNet audit finalization, and reproducibility freeze. These milestones preserve the completed/diagnostic/protocol-only evidence distinction.
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
- Phase31 claim alignment: `outputs/milestones/protocol_claim_alignment/`, `outputs/milestones/materials_fixed_budget_scientific_utility/`, `outputs/milestones/ctc_scientific_artifact_consequence/`, and `docs/abstract_claim_scope.md` (claim role audit, fixed-budget materials lead numbers, CTC artifact consequence tables, and abstract-scope guardrails)
- Reproducibility freeze: `outputs/milestones/reproducibility_freeze/` and `outputs/artifact_index.csv` (experiment-finalization milestone index and validation commands)
- Materials prospective CHGNet v2 gate: `outputs/milestones/materials_prospective_dft_followup_chgnet_v2/` (locally executable CHGNet scorer on PGCGM candidates; PARC release remained empty, so no DFT jobs were exported)
- Materials prospective CHGNet v3 near-hull gate: `outputs/milestones/materials_prospective_dft_followup_chgnet_v3/` (5,000 near-hull isovalent/chemically similar substitutions scored by CHGNet; strict and operational predeclared endpoints all refused, so no DFT jobs were exported)
- Materials prospective MatterGen v4 gate: `outputs/milestones/mattergen_parc_prospective_dft_followup/` (frontier-generator protocol using MatterGen plus CHGNet/MACE-MP consensus scoring; MatterGen and MACE smoke checks are recorded, but no generated candidate pool, frozen PARC selection, DFT manifest, DFT outcomes, or positive result is claimed)
- Community benchmark: `outputs/benchmarks/parc_certification_benchmark/`
- File integrity manifest: `MANIFEST_SHA256.txt`

## Citation

A formal citation will be added after archival release. Until then, cite the repository title and commit hash.
