# Reproducibility Guide

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e code/parc_track
pip install numpy scipy pandas opencv-python pyyaml tqdm pytest motmetrics pycocotools pillow matplotlib shapely tifffile imagecodecs
pytest -q tests
```

Equivalent Makefile entry:

```bash
make test PYTHON=python
```

## 2. Verify Tiny Fixture

```bash
python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api
```

Expected outputs include candidate schema files, an audit-label fixture, and API documentation.

## 3. Verify Frozen Tables

The core public milestones are:

```text
outputs/milestones/reliability_fortress/
outputs/milestones/scientific_domain_ctc/
outputs/milestones/scientific_domain_ctc_learned/
outputs/milestones/ctc_strict_human_audit/
outputs/milestones/scientific_domain_spacenet7/
outputs/milestones/scientific_domain_spacenet7_prospective/
outputs/milestones/scientific_domain_materials/
outputs/milestones/scientific_release_success_map/
outputs/milestones/no_human_scientific_consequence/
outputs/milestones/materials_computational_followup_trial/
outputs/milestones/official_downstream_consequence/
outputs/milestones/release_certification_benchmark/
outputs/milestones/block_heterogeneity_robustness/
outputs/milestones/materials_prospective_validation_protocols/
outputs/milestones/materials_prospective_dft_followup/
outputs/milestones/fixed_budget_downstream_utility/
outputs/milestones/primary_statistics/
outputs/milestones/materials_robustness_triad/
outputs/milestones/baseline_matrix_final/
outputs/milestones/ctc_strict_anchor/
outputs/milestones/iwildcam_audit_final/
outputs/milestones/spacenet_real_audit_final/
outputs/milestones/materials_temporal_validation/
outputs/milestones/materials_independent_dft_validation/
outputs/milestones/materials_alex_mp_a1_a2_validation/
outputs/milestones/main_evidence_hard_upgrade_phase30/
outputs/milestones/materials_source_discordance_stress_test/
outputs/milestones/ctc_decision_utility_main_evidence/
outputs/milestones/cross_domain_blind_audit_main_evidence/
outputs/milestones/protocol_claim_alignment/
outputs/milestones/materials_fixed_budget_scientific_utility/
outputs/milestones/ctc_scientific_artifact_consequence/
outputs/milestones/nmi_presubmission_package/
outputs/milestones/nmi_presubmission_final/
outputs/milestones/materials_label_discordance_preregistration/
outputs/milestones/materials_selection_conditional_discordance/
outputs/milestones/ncs_week0_protocol_freeze/
outputs/milestones/materials_temporal_mlip_audit/
outputs/milestones/pre_release_repository_cleanup/
outputs/milestones/reproducibility_freeze/
outputs/milestones/generality_reliability/
outputs/milestones/release_story/
outputs/benchmarks/parc_certification_benchmark/
```

Check file integrity with:

```bash
sha256sum -c MANIFEST_SHA256.txt
```

Public-bundle safety checks:

```bash
make validate-public-bundle PYTHON=python
make verify-manifest
```

The learned-hybrid CTC milestone includes public-safe leakage and robustness checks:

```text
outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_leakage_audit.csv
outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_reverse_split.csv
outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_negative_control.csv
```

The materials-discovery milestone can be regenerated from the public WBM summary
and public Matbench Discovery prediction CSVs once those files are available
locally:

```bash
python scripts/run_materials_discovery_parc_flagship.py
```

The script writes only public-safe tables to
`outputs/milestones/scientific_domain_materials/`; raw crystal structures and
model weights are not needed.

Regenerate the current paper-facing release/refusal tables:

```bash
make reproduce-main-tables PYTHON=python
```

Regenerate the experiment-finalization milestones:

```bash
python scripts/build_experimental_finalization_milestones.py
```

This command builds the fixed-budget downstream utility tables, primary
statistics, materials robustness triad, final baseline matrix, strict CTC anchor
tables, final iWildCam/SpaceNet audit tables, A1/A2 protocol-only status
packages, `outputs/artifact_index.csv`, and the reproducibility-freeze index.
It does not promote protocol-only A1/A2/A3 rows into completed evidence.

Regenerate the phase30 non-A3 main-evidence pivot:

```bash
python scripts/build_phase30_main_evidence_hard_upgrade.py
```

This command builds:

```text
outputs/milestones/main_evidence_hard_upgrade_phase30/
outputs/milestones/materials_source_discordance_stress_test/
outputs/milestones/ctc_decision_utility_main_evidence/
outputs/milestones/cross_domain_blind_audit_main_evidence/
```

The phase30 matrix explicitly keeps OQMD/alex-mp rows as completed negative
diagnostics and keeps A3 as a high-risk bonus track unless a nonempty frozen
selection and DFT outcomes exist.

Verify the pre-release cleanup guardrails:

```bash
python scripts/validate_public_bundle.py outputs/milestones/pre_release_repository_cleanup
pytest -q tests/test_pre_release_repository_cleanup.py
```

The cleanup milestone records which obsolete legacy, prefill, draft, archive,
and runtime artifacts were removed. It does not alter completed evidence and
does not promote any A3 row to positive evidence.

Regenerate the phase31 protocol/claim-alignment guardrails:

```bash
python scripts/build_phase31_protocol_claim_alignment.py
```

This command builds:

```text
outputs/milestones/protocol_claim_alignment/
outputs/milestones/materials_fixed_budget_scientific_utility/
outputs/milestones/ctc_scientific_artifact_consequence/
outputs/milestones/nmi_presubmission_package/
outputs/milestones/nmi_presubmission_final/
docs/abstract_claim_scope.md
```

The phase31 tables assign each candidate headline result exactly one manuscript
role, require source SHA256 hashes for primary-headline rows, keep CGCNN K=100
as calibration/validity support, and forbid prospective materials-discovery
language unless A3 has a frozen nonempty release, at least 25 completed DFT
outcomes, and primary FTR within the target alpha.



Regenerate the phase33 NMI presubmission final package:

```bash
python scripts/build_phase33_nmi_presubmission_final.py
```

This command builds the compressed final inquiry, final evidence table, final
abstract, editor cold read, forbidden-claims list, cover-letter positioning,
and go/no-go checklist. All go-required checks must be `PASS`.

Regenerate the NCS/NMI Week 0 protocol-freeze package:

```bash
python scripts/build_ncs_week0_protocol_freeze.py
pytest -q tests/test_ncs_week0_protocol_freeze.py
```

This package freezes the next candidate universes, scores, PARC parameters,
K/alpha grid, block definitions, DFT audit arms, t0/t1 hull definitions, MLIP
audit models, CTC audit guidelines, and go/no-go rules. It is preregistration
infrastructure only: it records OSF/Zenodo targets as ready for upload, not as
completed external registrations, and it creates no new outcome evidence.

Regenerate the Week 1-4 materials temporal + MLIP audit package:

```bash
python scripts/build_materials_temporal_mlip_audit.py
pytest -q tests/test_materials_temporal_mlip_audit.py
```

This package reports a split outcome: timestamped t0/t1 temporal hull-shift
validation remains no-go in the public bundle, while frozen CHGNet, MACE-MP,
and ALIGNN-FF pre-outcome score tables provide directional release-vs-tail MLIP
support. It does not modify A3 selection/manifests and does not create DFT
evidence.

Pre-release archive policy: `outputs/packages/*.tar.gz` files are generated
artifacts, not source artifacts. They are ignored in Git and can be recreated
with `make package-release` when a release archive is needed.

A3 runtime policy: local Quantum ESPRESSO outcome files under
`outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/qe_outputs/`
are ignored until a post-outcome analysis milestone is created under the
predeclared conservative failure policy.
Third-party Quantum ESPRESSO pseudopotential payload files under
`A3_QE_LOCAL_RUN/pseudos/` are also ignored in Git; the tracked artifact is the
pseudopotential map with source filenames and SHA256 hashes.

Regenerate the phase32 NMI presubmission package:

```bash
python scripts/build_phase32_nmi_presubmission_package.py
```

This command builds the editor-facing inquiry, one-page evidence table,
abstract draft, desk-risk cold read, referee rationale, and positioning
document from phase31-approved evidence only. It excludes pending A3 rows and
external-source diagnostics from positive claims.

The cross-domain success/refusal map can also be regenerated directly:

```bash
python -m parc_track.cli phase19 success-domain
```

This command also regenerates:

- paper-ready materials robustness/gamma/raw-vs-PARC figure sources and PDFs;
- `table_refusal_diagnosis_ilp.csv`, using only aggregate infeasibility checks unless a candidate graph is available;
- `table_success_domain_predictor.csv` and `figure_success_domain_map.pdf`;
- `table_validity_assumptions_by_domain.csv`.

Rows marked protocol-only remain protocol-only and are not promoted to completed evidence.

The verified-positive-removal load-bearing ablation uses candidate-level CTC
learned and materials artifacts rather than summary tables. It reruns the six
preselected CTC/materials main or boundary rows under full PARC, no
verified-positive removal, and random positive removal:

```bash
python scripts/run_verified_positive_removal_load_bearing_ablation.py
```

The outputs are:

```text
outputs/milestones/scientific_release_success_map/table_verified_positive_removal_load_bearing.csv
outputs/milestones/scientific_release_success_map/table_verified_positive_removal_load_bearing_seed_rows.csv
outputs/milestones/scientific_release_success_map/VERIFIED_POSITIVE_REMOVAL_LOAD_BEARING_CLOSEOUT.md
```

The ALIGNN margin-excluded 25meV K=100 row remains a boundary sensitivity row,
not a strict pass, even though it is included in this load-bearing diagnostic.

The no-human scientific consequence package uses public/official labels only
and adds no new human review:

```bash
python scripts/build_no_human_scientific_consequence.py
python scripts/build_no_human_paper_integration.py
```

The outputs live under:

```text
outputs/milestones/no_human_scientific_consequence/
```

This package reports materials computational follow-up queues, a materials
model-zoo release frontier for locally available prediction files, CTC
official-GT lineage consequence diagnostics, and SpaceNet official-GT
building-persistence map-consequence diagnostics. The paper integration script
then writes `table_no_human_consequence_summary.csv`,
`figure_no_human_consequence_main.{csv,pdf}`,
`figure_materials_model_zoo_frontier.{csv,pdf}`, and
`NO_HUMAN_PAPER_INTEGRATION.md` for Figure 6 and impact-first submission text.
Rows for unavailable modern materials prediction files are recorded as not-run
availability rows, not completed evidence.

The materials computational follow-up trial freezes model-ranked public WBM
candidate queues, composition-family splits, requested budgets, alpha levels,
and the one-sided observed-positive rule before evaluating held-out public DFT
labels in the follow-up partition:

```bash
python scripts/build_materials_computational_trial.py
```

Outputs live under:

```text
outputs/milestones/materials_computational_followup_trial/
```

This is a quasi-prospective public-label replay. It does not run new DFT,
does not claim experimental synthesis, and should not be described as a true
prospective materials-discovery deployment.

Official-label downstream artifact metrics can be regenerated with:

```bash
python scripts/build_official_downstream_consequence.py
```

Outputs live under:

```text
outputs/milestones/official_downstream_consequence/
```

This package uses CTC official/held-out lineage identities and SpaceNet 7
official building identities to quantify downstream artifacts: CTC
lineage-edge false-link, conflict, component-corruption and TRA/AOGM-style
edit-burden proxies; and SpaceNet building-persistence false-link, chain, and
map-edit proxies. It introduces no new human labels. The CTC edit-burden
values are not official challenge leaderboard scores.

The release-certification benchmark cards can be regenerated with:

```bash
python scripts/build_release_certification_benchmark_cards.py
```

Outputs live under:

```text
outputs/milestones/release_certification_benchmark/
```

This package is a governance wrapper over completed evidence: release cards,
track registry, field schema, checklist, benchmark index, and figure sources.
It does not introduce new experiments or new human labels, and protocol-only
ideas are kept in the schema/checklist rather than promoted to completed
evidence.

Phase25 block-size heterogeneity diagnostics can be regenerated with:

```bash
python scripts/build_block_heterogeneity_robustness.py
```

Outputs live under:

```text
outputs/milestones/block_heterogeneity_robustness/
```

This package reports size-stratified p-value diagnostics, candidate-level
materials size-matched reruns, candidate-level materials downsampled
block-max stress tests, and scoped aggregate/audit-sample diagnostics for CTC
and SpaceNet. Candidate-level reruns are not fabricated when a full candidate
universe is absent from the public package.

The A1/A2 materials prospective-validation preregistration and feasibility
cards can be regenerated with:

```bash
python scripts/build_materials_prospective_validation_protocols.py
```

Outputs live under:

```text
outputs/milestones/materials_prospective_validation_protocols/
```

These artifacts freeze temporal-split and independent-DFT validation protocols
and record local feasibility. They are protocol/feasibility artifacts only:
they do not report a completed prospective computational trial, new DFT labels,
or an independent-DFT cross-validation result.

The A3 prospective in-silico DFT follow-up protocol can be frozen with:

```bash
python scripts/build_materials_prospective_dft_followup_protocol.py
```

Outputs live under:

```text
outputs/milestones/materials_prospective_dft_followup/
```

This package freezes the ALIGNN-FF `alpha=0.10, K=500` DFT follow-up design,
40/40/40 arm plan, public-label exclusion schema, novelty-crossmatch schema,
selection/job schemas, and DFT failure policy before any new DFT outcomes are
known. In the current public package no unlabeled generated crystal pool is
supplied, so candidate selection and DFT job export remain empty by design. It
must not be reported as completed new-DFT evidence until a public-safe
unlabeled candidate pool, crossmatch report, frozen selection, and DFT outcomes
are supplied.

## 4. Re-run with External Datasets

The configs are sanitized and may contain `${PARC_TRACK_ROOT}` placeholders. Materialize a local runnable copy:

```bash
python scripts/materialize_configs.py --root /path/to/local/parc-track --out configs_local
```

Then place or symlink external datasets and candidate universes according to the target config. Example commands:

```bash
python -m parc_track.cli phase3 matrix --config configs_local/phase3_ovtb_full_matrix.yaml
python -m parc_track.cli phase9 reliability-bundle --output-dir outputs/milestones/reliability_fortress_rerun
```

## 5. External Proposal Generators

PARC-Track expects candidate-path CSV/JSON tables, not raw model internals. Use official detector/tracker repositories for inference, then convert predictions into the schema in `docs/API.md`.

## 6. Parallel Certification Safety

Candidate universes should be treated as immutable inputs. During the iWildCam
parallel deployment we identified that an earlier certification path normalized
split/audit state and wrote it back to the input `candidate_universe.csv`, which
is unsafe when multiple risk levels or budgets share the same file in parallel.
The current code writes that normalized state to a per-run
`normalized_candidate_universe.csv` sidecar and leaves the input file unchanged.
The regression test `test_real_certify_does_not_write_back_to_input_candidate_universe`
checks this behavior.

## 7. Public Safety

Do not commit raw videos, raw annotations, weights, cache directories, or private credentials. The included `scripts/validate_public_bundle.py` checks common leakage patterns.

## A3-v4 formal selection gate

Run `make reproduce-a3-v4-formal-selection-gate` to rebuild the available-source MatterGen formal selection gate. This requires the private MatterGen generated CIF zip and alex-mp local public snapshot; it is not completed DFT evidence.

## A3-v4 DFT manifest addendum

Run `make reproduce-a3-v4-dft-manifest-addendum` after the formal selection gate to rebuild the pre-outcome comparator manifest addendum. The addendum does not modify `selection_frozen_v4.csv` and is not completed DFT evidence.

## A3-v4 Phase29c extra-tail manifest

Run `make reproduce-a3-v4-phase29c-extra-tail-manifest` after the Phase29b addendum to rebuild the pre-outcome formal raw-top100 extra-tail manifest. This does not modify `selection_frozen_v4.csv` and is not completed DFT evidence.

## A3 DFT run package

Run `make reproduce-a3-dft-run-package` after Phase29c to rebuild the DFT execution package. The package contains CIF inputs and frozen manifests only; it does not modify `selection_frozen_v4.csv` and includes no DFT outcomes.

## A3 local Quantum ESPRESSO execution layer

Run `make reproduce-a3-qe-local-run` after `make reproduce-a3-dft-run-package` to derive local QE input decks from the frozen A3 CIF package. This target does not modify `selection_frozen_v4.csv`, does not contain outcomes, and must not be cited as prospective DFT evidence.

## Materials queue source-uncertainty overlay

Run `make reproduce-materials-queue-source-uncertainty-overlay` to rebuild the candidate-level ALIGNN-FF K=300/500 materials queue overlay against the alex-mp A2 exact-structure diagnostic table. Formula-only matches are retained only as tags and are excluded from alex-mp FTR denominators. This target is a source-discordance stress diagnostic, not a positive independent-validation result and not prospective materials discovery.

## Materials t0/t1 current-MP hull-shift snapshot

Run `make reproduce-materials-t0-t1-snapshot-acquisition` after the current MP entry table has been acquired once. The target reuses the frozen `table_t1_current_mp_entries_by_chemsys.csv` cache and rebuilds the t0/t1 join, FTR summaries, drift diagnostics, gate assessment, manifests, and closeout. A fresh acquisition requires `MP_API_KEY` in the environment:

```bash
python scripts/acquire_materials_t0_t1_snapshots.py
```

The milestone is a current-MP hull-shift utility diagnostic. It is not new DFT, not a strict `alpha=0.10` temporal certificate, and not a prospective materials-discovery claim.

## NCS Phase50/51 materials paperization

Run `make reproduce-ncs-phase50-51-materials-paperization` after the Phase49 t0/t1 snapshot exists. The builder creates paper-facing current-MP version-shift figure inputs, evidence-status tables, a six-display-item NCS plan, a 150-word abstract draft, and a candidate-level t1 explanation table for the frozen K=300/500 WBM queues.

The Phase51 candidate-level table includes ALIGNN-FF, CGCNN and MEGNet model-zoo predictions available in the local Matbench Discovery cache. It does not itself claim CHGNet/MACE consensus validation.

## NCS Phase53 CHGNet/MACE candidate-level audit

Run `make reproduce-ncs-phase53-chgnet-mace-candidate-audit` after the local private WBM raw-structure cache is available. The builder scores the 1,191 frozen K=300/500 WBM queue candidates with CHGNet and MACE-MP and writes:

- `outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit/table_materials_candidate_level_chgnet_mace_audit.csv`
- `outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit/table_chgnet_mace_support_by_policy.csv`
- `outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit/table_chgnet_mace_disagreement_by_t1_status.csv`
- `outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit/figure_chgnet_mace_release_vs_tail_inputs.csv`

The score cache is public-safe: it records structure hashes and score proxies, not raw CIFs or private structure files. The allowed claim is queue-level CHGNet/MACE score-support contrast for PARC release versus raw-only extra-tail. The forbidden claim remains CHGNet/MACE reference-hull validation, DFT evidence, strict t1 alpha control, or prospective materials discovery.

## NCS Phase56/57 version-shift accounting and t1/MLIP baselines

Run:

```bash
make reproduce-materials-baseline-frontier
```

This creates:

- `outputs/milestones/ncs_phase56_version_shift_accounting/supplement_version_shift_accounting.tex`
- `outputs/milestones/ncs_phase56_version_shift_accounting/table_version_shift_decomposition.csv`
- `outputs/milestones/ncs_phase57_t1_mlip_baseline_frontier/table_t1_mlip_baseline_frontier.csv`
- `outputs/milestones/ncs_phase57_t1_mlip_baseline_frontier/table_baseline_capability_t1_mlip.csv`

Phase56 is a deterministic accounting identity for a fixed release set across
two truth versions. It is not a new PARC guarantee. Phase57 extends the baseline
capability table to current-MP t1 labels and Phase53 CHGNet/MACE score-support
proxies. The correct interpretation is that some matched-volume baselines can
match PARC on t1 FTR, but they do not identify that volume with a one-sided
release certificate or return certified refusal when high-volume release is
unsupported.

## NCS Phase60 PARC-V support-gate audit

Run:

```bash
make reproduce-ncs-phase60-parc-v-version-aware-release
```

This regenerates:

- `outputs/milestones/ncs_phase60_parc_v_version_aware_release/table_parc_v_candidate_level.csv`
- `outputs/milestones/ncs_phase60_parc_v_version_aware_release/table_parc_v_primary_results.csv`
- `outputs/milestones/ncs_phase60_parc_v_version_aware_release/table_parc_v_gate_audit.csv`
- `outputs/milestones/ncs_phase60_parc_v_version_aware_release/figure_parc_v_version_aware_release_inputs.csv`

The result is a no-go for the simple PARC-V headline route: the frozen
CHGNet/MACE support-gated subset is non-empty, but it does not materially lower
current-MP t1 FTR and does not meet the predeclared <=0.15 or <=0.10 empirical
thresholds. It is not a full SCS rerun, not a new theorem-grade certificate, not
DFT evidence, and not prospective materials discovery.

## NCS Phase61 PARC-M multi-evidence fusion audit

Run:

```bash
make reproduce-ncs-phase61-parc-m-multi-evidence-fusion
```

This regenerates:

- `outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion/table_parc_m_primary_results.csv`
- `outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion/table_parc_m_candidate_level.csv`
- `outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion/table_parc_m_gate_audit.csv`
- `outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion/table_parc_m_source_evalue_audit.csv`

Phase61 is a medium empirical feasibility signal, not a claim-ready theorem.
Fixed mixtures of original PARC evidence and ALIGNN/CHGNet/MACE score-derived
e-proxies lower current-MP t1 FTR by about 0.03-0.04 while keeping nontrivial
release sizes. The theorem-grade gate fails because CHGNet/MACE are available
only as queue-level score proxies, not full null-superset calibration e-values.

## NCS Phase62 full-calibration CHGNet/MACE e-values

Run:

```bash
make reproduce-ncs-phase62-full-calibration-mlip-evalues
```

This regenerates:

- `outputs/milestones/ncs_phase62_full_calibration_mlip_evalues/table_full_calibration_score_inventory.csv`
- `outputs/milestones/ncs_phase62_full_calibration_mlip_evalues/table_parc_m_full_calibration_results.csv`
- `outputs/milestones/ncs_phase62_full_calibration_mlip_evalues/table_parc_m_full_calibration_candidate_level.csv`
- `outputs/milestones/ncs_phase62_full_calibration_mlip_evalues/table_parc_m_full_calibration_gate_audit.csv`

Phase62 resolves the Phase61 auxiliary-source availability blocker by converting
CHGNet and MACE-MP scores into full-calibration e-values over the frozen WBM
one-per-composition-family calibration denominator, excluding target-overlap
rows before block maxima are computed. It remains a scoped t0/t1 queue audit:
the headline method-upgrade gate fails, and the milestone must not be described
as DFT evidence, current-MP t1 alpha control, or prospective materials
discovery.

## NCS Phase52/58 materials uncertainty and evidence ledger

Run the compact materials-paperization targets:

```bash
make reproduce-materials-t0-t1
make reproduce-materials-mlip-audit
make reproduce-materials-baseline-frontier
make reproduce-materials-figures
make validate-evidence-ledger
```

`reproduce-materials-figures` regenerates the Phase50/51 paper-facing tables and
the Phase52 chemical-system bootstrap / rank-bin randomization diagnostics.
`reproduce-materials-mlip-audit` regenerates both the Phase51 model-zoo
candidate explanation and the Phase53 CHGNet/MACE score-support audit. The
Phase53 labels are raw-energy score-support proxies, not reference-hull
stability labels. Phase58 writes
`outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv`,
where every materials claim has a source artifact, SHA256 hash, validation
command, status, and overclaim guardrail.

## Submission scope lock

Run `make reproduce-phase37-submission-scope-lock` to rebuild the two-anchor evidence hierarchy, release/refuse contract comparator, and forbidden-claim replacement table used for the narrow release-governance submission framing. This target creates no new experiment and does not promote A3, alex-mp/OQMD, Route C, or pending external blind audit rows to positive evidence.
