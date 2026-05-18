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

Regenerate the phase31 protocol/claim-alignment guardrails:

```bash
python scripts/build_phase31_protocol_claim_alignment.py
```

This command builds:

```text
outputs/milestones/protocol_claim_alignment/
outputs/milestones/materials_fixed_budget_scientific_utility/
outputs/milestones/ctc_scientific_artifact_consequence/
docs/abstract_claim_scope.md
```

The phase31 tables assign each candidate headline result exactly one manuscript
role, require source SHA256 hashes for primary-headline rows, keep CGCNN K=100
as calibration/validity support, and forbid prospective materials-discovery
language unless A3 has a frozen nonempty release, at least 25 completed DFT
outcomes, and primary FTR within the target alpha.

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
