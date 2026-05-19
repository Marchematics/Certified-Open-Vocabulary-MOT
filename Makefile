PYTHON ?= python
PYTHONPATH ?= code/parc_track

.PHONY: test tiny-fixture reproduce-main-tables reproduce-main-figures reproduce-no-human-consequence reproduce-materials-computational-trial reproduce-official-downstream-consequence reproduce-release-certification-benchmark reproduce-block-heterogeneity-robustness reproduce-materials-prospective-validation reproduce-materials-alex-mp-a1-a2 reproduce-phase30-main-evidence reproduce-phase31-claim-alignment reproduce-phase32-presubmission reproduce-phase33-presubmission-final reproduce-a3-v4-formal-selection-gate reproduce-a3-v4-dft-manifest-addendum reproduce-a3-v4-phase29c-extra-tail-manifest reproduce-a3-dft-run-package reproduce-a3-qe-local-run reproduce-experimental-finalization phase24-freeze-dft-followup phase24-build-unlabeled-pool phase24-filter-public-labels phase24-score-unlabeled-pool phase24-select-dft-arms phase24-export-dft-jobs validate-public-bundle verify-manifest pre-release-check package-release package-release-story package-scientific-release

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest -q tests

tiny-fixture:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api

reproduce-main-tables:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase13 release-story
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase14 closeout
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase15 full-experiments
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase16 generality-closeout
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase17 reviewer-closeout
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase19 success-domain
	$(PYTHON) scripts/build_no_human_paper_integration.py
	$(PYTHON) scripts/build_materials_computational_trial.py
	$(PYTHON) scripts/build_official_downstream_consequence.py
	$(PYTHON) scripts/build_release_certification_benchmark_cards.py
	$(PYTHON) scripts/build_block_heterogeneity_robustness.py
	$(PYTHON) scripts/build_materials_prospective_validation_protocols.py
	$(PYTHON) scripts/build_materials_prospective_dft_followup_protocol.py

reproduce-main-figures:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase16 generality-closeout

reproduce-no-human-consequence:
	$(PYTHON) scripts/build_no_human_scientific_consequence.py
	$(PYTHON) scripts/build_no_human_paper_integration.py

reproduce-materials-computational-trial:
	$(PYTHON) scripts/build_materials_computational_trial.py

reproduce-official-downstream-consequence:
	$(PYTHON) scripts/build_official_downstream_consequence.py

reproduce-release-certification-benchmark:
	$(PYTHON) scripts/build_release_certification_benchmark_cards.py

reproduce-block-heterogeneity-robustness:
	$(PYTHON) scripts/build_block_heterogeneity_robustness.py

reproduce-materials-prospective-validation:
	$(PYTHON) scripts/build_materials_prospective_validation_protocols.py

reproduce-materials-alex-mp-a1-a2:
	$(PYTHON) scripts/build_materials_alex_mp_a1_a2_validation.py

reproduce-phase30-main-evidence:
	$(PYTHON) scripts/build_phase30_main_evidence_hard_upgrade.py

reproduce-phase31-claim-alignment:
	$(PYTHON) scripts/build_phase31_protocol_claim_alignment.py

reproduce-phase32-presubmission:
	$(PYTHON) scripts/build_phase32_nmi_presubmission_package.py

reproduce-phase33-presubmission-final:
	$(PYTHON) scripts/build_phase33_nmi_presubmission_final.py

reproduce-a3-v4-formal-selection-gate:
	$(PYTHON) scripts/build_a3_v4_formal_selection_gate.py

reproduce-a3-v4-dft-manifest-addendum:
	$(PYTHON) scripts/build_a3_v4_dft_manifest_addendum.py

reproduce-a3-v4-phase29c-extra-tail-manifest:
	$(PYTHON) scripts/build_a3_v4_phase29c_extra_tail_manifest.py

reproduce-a3-dft-run-package:
	$(PYTHON) scripts/build_a3_dft_run_package.py

reproduce-a3-qe-local-run:
	$(PYTHON) scripts/build_a3_qe_local_run_package.py

reproduce-experimental-finalization:
	$(PYTHON) scripts/build_experimental_finalization_milestones.py

phase24-freeze-dft-followup:
	$(PYTHON) scripts/build_materials_prospective_dft_followup_protocol.py

phase24-build-unlabeled-pool:
	$(PYTHON) scripts/build_unlabeled_materials_candidate_pool.py

phase24-filter-public-labels:
	$(PYTHON) scripts/filter_public_labeled_materials_candidates.py

phase24-score-unlabeled-pool:
	$(PYTHON) scripts/score_unlabeled_pool_alignnff.py

phase24-select-dft-arms:
	$(PYTHON) scripts/select_prospective_dft_arms_from_pool.py

phase24-export-dft-jobs:
	$(PYTHON) scripts/export_prospective_dft_jobs.py

validate-public-bundle:
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/reliability_fortress
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/release_story
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_ctc_learned
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_spacenet7_prospective
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_iwildcam_human_audit
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_materials
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_release_success_map
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/no_human_scientific_consequence
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_computational_followup_trial
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/official_downstream_consequence
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/release_certification_benchmark
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/block_heterogeneity_robustness
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_prospective_validation_protocols
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_prospective_dft_followup
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/release_story/paper_diagnostics
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_temporal_validation
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_independent_dft_validation
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/fixed_budget_downstream_utility
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/primary_statistics
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_robustness_triad
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/baseline_matrix_final
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ctc_strict_anchor
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/iwildcam_audit_final
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/spacenet_real_audit_final
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/reproducibility_freeze
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_temporal_replay_completed
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_alex_mp_a1_a2_validation
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/fixed_budget_scientific_utility_trial
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/adversarial_release_stress_trial
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/selector_optimality_diagnostics
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/main_evidence_hard_upgrade_phase30
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_source_discordance_stress_test
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ctc_decision_utility_main_evidence
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/cross_domain_blind_audit_main_evidence
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/protocol_claim_alignment
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_fixed_budget_scientific_utility
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ctc_scientific_artifact_consequence
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/nmi_presubmission_package
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/nmi_presubmission_final
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/pre_release_repository_cleanup

verify-manifest:
	sha256sum -c MANIFEST_SHA256.txt

pre-release-check:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest -q tests/test_pre_release_repository_cleanup.py
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/pre_release_repository_cleanup

package-release:
	mkdir -p outputs/packages
	tar -czf outputs/packages/reliability_fortress.tar.gz -C outputs/milestones reliability_fortress
	tar -czf outputs/packages/release_story.tar.gz -C outputs/milestones release_story
	tar -czf outputs/packages/generality_reliability.tar.gz -C outputs/milestones generality_reliability
	tar -czf outputs/packages/scientific_domain_ctc_learned.tar.gz -C outputs/milestones scientific_domain_ctc_learned
	tar -czf outputs/packages/scientific_domain_spacenet7_prospective.tar.gz -C outputs/milestones scientific_domain_spacenet7_prospective
	tar -czf outputs/packages/scientific_domain_iwildcam_human_audit.tar.gz -C outputs/milestones scientific_domain_iwildcam_human_audit
	tar -czf outputs/packages/scientific_domain_materials.tar.gz -C outputs/milestones scientific_domain_materials
	tar -czf outputs/packages/scientific_release_success_map.tar.gz -C outputs/milestones scientific_release_success_map
	tar -czf outputs/packages/no_human_scientific_consequence.tar.gz -C outputs/milestones no_human_scientific_consequence
	tar -czf outputs/packages/materials_computational_followup_trial.tar.gz -C outputs/milestones materials_computational_followup_trial
	tar -czf outputs/packages/official_downstream_consequence.tar.gz -C outputs/milestones official_downstream_consequence
	tar -czf outputs/packages/release_certification_benchmark.tar.gz -C outputs/milestones release_certification_benchmark
	tar -czf outputs/packages/block_heterogeneity_robustness.tar.gz -C outputs/milestones block_heterogeneity_robustness
	tar -czf outputs/packages/materials_prospective_validation_protocols.tar.gz -C outputs/milestones materials_prospective_validation_protocols
	tar -czf outputs/packages/materials_prospective_dft_followup.tar.gz -C outputs/milestones materials_prospective_dft_followup

package-release-story:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase13 release-story

package-scientific-release: package-release
