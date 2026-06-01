PYTHON ?= python
PYTHONPATH ?= code/parc_track

.PHONY: reproduce-ncs-phase80-finding-first-submission-package
.PHONY: reproduce-ncs-phase81-ctc-external-blind-audit-mini-study
.PHONY: reproduce-ncs-phase82-ctc-ai-preannotation-for-human-review
.PHONY: reproduce-ncs-phase83-necessity-and-prevented-harm
.PHONY: reproduce-ncs-phase84-real-audit-parc-a-replication
.PHONY: reproduce-ncs-phase91-ctc-strong-model-annotation
.PHONY: reproduce-ncs-phase92-ctc-model-surrogate-gate-replay
.PHONY: reproduce-b-phase85-external-ai-materials-claim-decay-pilot
.PHONY: reproduce-b-phase86-claim-decay-access-preflight
.PHONY: reproduce-b-phase87-minimal-claim-registry
.PHONY: reproduce-b-phase88-current-reference-smoke
.PHONY: reproduce-ncs-phase88-low-cost-editorial-hardening
.PHONY: reproduce-b-phase89-exact-structure-audit-readiness
.PHONY: reproduce-b-phase90-gnome-raw-structure-ingest
.PHONY: reproduce-b-phase91-gnome-mp-formula-prefilter
.PHONY: reproduce-b-phase92-gnome-mp-neighbor-gap-analysis
.PHONY: reproduce-ncs-phase89-submission-integration-map
.PHONY: reproduce-ncs-phase67d-durability-risk-headline-hardening

.PHONY: test tiny-fixture reproduce-ncs-phase66-certificate-durability reproduce-ncs-phase67-margin-stable-certification reproduce-ncs-phase67b-hard-margin-eligibility reproduce-ncs-phase67c-durability-risk-prediction reproduce-main-tables reproduce-main-figures reproduce-no-human-consequence reproduce-materials-computational-trial reproduce-official-downstream-consequence reproduce-release-certification-benchmark reproduce-block-heterogeneity-robustness reproduce-materials-prospective-validation reproduce-materials-alex-mp-a1-a2 reproduce-materials-label-discordance-preregistration reproduce-materials-label-discordance-experiment reproduce-materials-selection-conditional-discordance reproduce-materials-queue-source-uncertainty-overlay reproduce-phase30-main-evidence reproduce-phase31-claim-alignment reproduce-phase32-presubmission reproduce-phase33-presubmission-final reproduce-phase37-submission-scope-lock reproduce-ncs-week0-protocol-freeze reproduce-materials-temporal-mlip-audit reproduce-materials-t0-t1-snapshot-acquisition reproduce-ncs-phase50-51-materials-paperization reproduce-ncs-phase52-materials-t1-uncertainty reproduce-ncs-phase53-chgnet-mace-candidate-audit reproduce-ncs-phase56-version-shift-accounting reproduce-ncs-phase57-t1-mlip-baseline-frontier reproduce-ncs-phase58-reproducibility-hardening reproduce-ncs-phase60-parc-v-version-aware-release reproduce-ncs-phase61-parc-m-multi-evidence-fusion reproduce-ncs-phase62-full-calibration-mlip-evalues reproduce-ncs-phase63-parc-a-active-verification reproduce-materials-t0-t1 reproduce-materials-mlip-audit reproduce-materials-baseline-frontier reproduce-materials-figures validate-evidence-ledger reproduce-a3-v4-formal-selection-gate reproduce-a3-v4-dft-manifest-addendum reproduce-a3-v4-phase29c-extra-tail-manifest reproduce-a3-dft-run-package reproduce-a3-qe-local-run reproduce-experimental-finalization phase24-freeze-dft-followup phase24-build-unlabeled-pool phase24-filter-public-labels phase24-score-unlabeled-pool phase24-select-dft-arms phase24-export-dft-jobs validate-public-bundle verify-manifest pre-release-check package-release package-release-story package-scientific-release reproduce-ncs-phase77-architecture-freeze reproduce-ncs-phase78-ctc-real-one-sided-audit reproduce-ncs-phase79-controlled-evolving-reference-simulation

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

reproduce-materials-label-discordance-preregistration:
	$(PYTHON) scripts/build_materials_label_discordance_preregistration.py

reproduce-materials-label-discordance-experiment:
	$(PYTHON) scripts/score_materials_label_discordance_frontier_models.py
	$(PYTHON) scripts/build_materials_label_discordance_experiment.py

reproduce-materials-selection-conditional-discordance:
	$(PYTHON) scripts/build_materials_selection_conditional_discordance.py

reproduce-materials-queue-source-uncertainty-overlay:
	$(PYTHON) scripts/build_materials_queue_source_uncertainty_overlay.py

reproduce-phase30-main-evidence:
	$(PYTHON) scripts/build_phase30_main_evidence_hard_upgrade.py

reproduce-phase31-claim-alignment:
	$(PYTHON) scripts/build_phase31_protocol_claim_alignment.py

reproduce-phase32-presubmission:
	$(PYTHON) scripts/build_phase32_nmi_presubmission_package.py

reproduce-phase33-presubmission-final:
	$(PYTHON) scripts/build_phase33_nmi_presubmission_final.py

reproduce-phase37-submission-scope-lock:
	$(PYTHON) scripts/build_phase37_submission_scope_lock.py

reproduce-ncs-week0-protocol-freeze:
	$(PYTHON) scripts/build_ncs_week0_protocol_freeze.py

reproduce-materials-temporal-mlip-audit:
	$(PYTHON) scripts/build_materials_temporal_mlip_audit.py

reproduce-materials-t0-t1-snapshot-acquisition:
	$(PYTHON) scripts/acquire_materials_t0_t1_snapshots.py --reuse-mp-entries

reproduce-ncs-phase50-51-materials-paperization:
	$(PYTHON) scripts/build_ncs_phase50_51_materials_paperization.py

reproduce-ncs-phase52-materials-t1-uncertainty:
	$(PYTHON) scripts/build_ncs_phase52_materials_t1_uncertainty.py

reproduce-ncs-phase53-chgnet-mace-candidate-audit:
	$(PYTHON) scripts/build_ncs_phase53_chgnet_mace_candidate_audit.py

reproduce-ncs-phase56-version-shift-accounting:
	$(PYTHON) scripts/build_ncs_phase56_version_shift_accounting.py

reproduce-ncs-phase57-t1-mlip-baseline-frontier: reproduce-ncs-phase53-chgnet-mace-candidate-audit
	$(PYTHON) scripts/build_ncs_phase57_t1_mlip_baseline_frontier.py

reproduce-ncs-phase58-reproducibility-hardening: reproduce-ncs-phase60-parc-v-version-aware-release reproduce-ncs-phase61-parc-m-multi-evidence-fusion
	$(PYTHON) scripts/build_ncs_phase58_reproducibility_hardening.py

reproduce-ncs-phase60-parc-v-version-aware-release: reproduce-ncs-phase53-chgnet-mace-candidate-audit
	$(PYTHON) scripts/build_ncs_phase60_parc_v_version_aware_release.py

reproduce-ncs-phase61-parc-m-multi-evidence-fusion: reproduce-ncs-phase53-chgnet-mace-candidate-audit
	$(PYTHON) scripts/build_ncs_phase61_parc_m_multi_evidence_fusion.py

reproduce-ncs-phase62-full-calibration-mlip-evalues: reproduce-ncs-phase53-chgnet-mace-candidate-audit
	$(PYTHON) scripts/build_ncs_phase62_full_calibration_mlip_evalues.py

reproduce-ncs-phase63-parc-a-active-verification:
	$(PYTHON) scripts/build_ncs_phase63_parc_a_certificate_directed_active_verification.py

reproduce-materials-t0-t1: reproduce-materials-t0-t1-snapshot-acquisition reproduce-ncs-phase50-51-materials-paperization

reproduce-materials-mlip-audit: reproduce-ncs-phase50-51-materials-paperization reproduce-ncs-phase53-chgnet-mace-candidate-audit reproduce-ncs-phase62-full-calibration-mlip-evalues

reproduce-materials-baseline-frontier: reproduce-ncs-phase56-version-shift-accounting reproduce-ncs-phase57-t1-mlip-baseline-frontier

reproduce-materials-figures: reproduce-ncs-phase50-51-materials-paperization reproduce-ncs-phase52-materials-t1-uncertainty

validate-evidence-ledger:
	$(PYTHON) scripts/validate_evidence_ledger.py

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
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_label_discordance_preregistration
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
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_queue_source_uncertainty_overlay
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/submission_scope_lock_phase37
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_week0_protocol_freeze
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_temporal_mlip_audit
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/materials_t0_t1_snapshot_acquisition
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase50_materials_version_shift_paperization
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase51_materials_t1_candidate_explanation
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase52_materials_t1_uncertainty
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase56_version_shift_accounting
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase57_t1_mlip_baseline_frontier
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase58_reproducibility_hardening
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase60_parc_v_version_aware_release
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase62_full_calibration_mlip_evalues
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase63_parc_a_certificate_directed_active_verification
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase64_parc_r_versioned_recertification
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase66_certificate_durability
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase65_parc_a_certificate_directed_policy
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase65b_parc_a_mechanism_diagnostics
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase65c_materials_active_audit_attempt
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase67d_durability_risk_headline_hardening
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase69_durability_budgeted_parc
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase69b_parc_d_hardening
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase70_dft_v2_checkpoint
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase74_risk_gated_recertification
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase75_active_versioned_recertification
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase76_parc_lifecycle_calculus
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase77_ncs_architecture_freeze
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase78_ctc_real_one_sided_audit
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase79_controlled_evolving_reference_simulation
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase80_finding_first_submission_package
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase81_ctc_external_blind_audit_mini_study
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase82_ctc_ai_preannotation_for_human_review
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase83_necessity_and_prevented_harm
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase84_real_audit_parc_a_replication
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/b_phase85_external_ai_materials_claim_decay_pilot
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/b_phase86_claim_decay_access_preflight
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/b_phase87_minimal_claim_registry
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/b_phase88_current_reference_smoke
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase88_low_cost_editorial_hardening
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/b_phase89_exact_structure_audit_readiness
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase89_submission_integration_map
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_durability_risk_manuscript_spine
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/ncs_phase68_dft_v2_pilot

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

reproduce-ncs-phase64-parc-r-versioned-recertification:
	$(PYTHON) scripts/build_ncs_phase64_parc_r_versioned_recertification.py

reproduce-ncs-phase65-parc-a-certificate-directed-policy:
	$(PYTHON) scripts/build_ncs_phase65_parc_a_certificate_directed_policy.py

reproduce-ncs-phase65b-parc-a-mechanism-diagnostics:
	$(PYTHON) scripts/build_ncs_phase65b_parc_a_mechanism_diagnostics.py

reproduce-ncs-phase65c-materials-active-audit-attempt:
	$(PYTHON) scripts/build_ncs_phase65c_materials_active_audit_attempt.py

reproduce-ncs-phase68-dft-v2-pilot:
	$(PYTHON) scripts/build_ncs_phase68_dft_v2_pilot.py

reproduce-ncs-phase68b-qe-secondary-local-run:
	$(PYTHON) scripts/build_ncs_phase68b_qe_secondary_local_run.py

reproduce-ncs-phase66-certificate-durability:
	$(PYTHON) scripts/build_ncs_phase66_certificate_durability.py

reproduce-ncs-phase67-margin-stable-certification:
	$(PYTHON) scripts/build_ncs_phase67_margin_stable_certification.py

reproduce-ncs-phase67b-hard-margin-eligibility:
	$(PYTHON) scripts/build_ncs_phase67b_hard_margin_eligibility.py

reproduce-ncs-phase67c-durability-risk-prediction:
	$(PYTHON) scripts/build_ncs_phase67c_durability_risk_prediction.py

reproduce-ncs-phase67d-durability-risk-headline-hardening:
	$(PYTHON) scripts/build_ncs_phase67d_durability_risk_headline_hardening.py

reproduce-ncs-phase69-durability-budgeted-parc:
	$(PYTHON) scripts/build_ncs_phase69_durability_budgeted_parc.py

reproduce-ncs-phase69b-parc-d-hardening:
	$(PYTHON) scripts/build_ncs_phase69b_parc_d_hardening.py

reproduce-ncs-phase70-dft-v2-checkpoint:
	$(PYTHON) scripts/build_ncs_phase70_dft_v2_checkpoint.py

reproduce-ncs-phase74-risk-gated-recertification:
	$(PYTHON) scripts/build_ncs_phase74_risk_gated_recertification.py

reproduce-ncs-phase75-active-versioned-recertification:
	$(PYTHON) scripts/build_ncs_phase75_active_versioned_recertification.py

reproduce-ncs-phase76-parc-lifecycle-calculus:
	$(PYTHON) scripts/build_ncs_phase76_parc_lifecycle_calculus.py

reproduce-ncs-phase77-architecture-freeze:
	$(PYTHON) scripts/build_ncs_phase77_architecture_freeze.py

reproduce-ncs-phase78-ctc-real-one-sided-audit:
	$(PYTHON) scripts/build_ncs_phase78_ctc_real_one_sided_audit.py

reproduce-ncs-phase79-controlled-evolving-reference-simulation:
	$(PYTHON) scripts/build_ncs_phase79_controlled_evolving_reference_simulation.py

reproduce-ncs-phase80-finding-first-submission-package:
	$(PYTHON) scripts/build_ncs_phase80_finding_first_submission_package.py

reproduce-ncs-phase81-ctc-external-blind-audit-mini-study:
	$(PYTHON) scripts/build_ncs_phase81_ctc_external_blind_audit_mini_study.py

reproduce-ncs-phase82-ctc-ai-preannotation-for-human-review:
	$(PYTHON) scripts/build_ncs_phase82_ctc_ai_preannotation_for_human_review.py

reproduce-ncs-phase83-necessity-and-prevented-harm:
	$(PYTHON) scripts/build_ncs_phase83_necessity_and_prevented_harm.py

reproduce-ncs-phase84-real-audit-parc-a-replication:
	$(PYTHON) scripts/build_ncs_phase84_real_audit_parc_a_replication.py

reproduce-ncs-phase91-ctc-strong-model-annotation:
	$(PYTHON) scripts/build_ncs_phase91_ctc_strong_model_annotation.py

reproduce-ncs-phase92-ctc-model-surrogate-gate-replay:
	$(PYTHON) scripts/build_ncs_phase92_ctc_model_surrogate_gate_replay.py

reproduce-b-phase85-external-ai-materials-claim-decay-pilot:
	$(PYTHON) scripts/build_b_phase85_external_ai_materials_claim_decay_pilot.py

reproduce-b-phase86-claim-decay-access-preflight:
	$(PYTHON) scripts/build_b_phase86_claim_decay_access_preflight.py

reproduce-b-phase87-minimal-claim-registry:
	$(PYTHON) scripts/build_b_phase87_minimal_claim_registry.py

reproduce-b-phase88-current-reference-smoke:
	$(PYTHON) scripts/build_b_phase88_current_reference_smoke.py

reproduce-ncs-phase88-low-cost-editorial-hardening:
	$(PYTHON) scripts/build_ncs_phase88_low_cost_editorial_hardening.py

reproduce-b-phase89-exact-structure-audit-readiness:
	$(PYTHON) scripts/build_b_phase89_exact_structure_audit_readiness.py

reproduce-b-phase90-gnome-raw-structure-ingest:
	$(PYTHON) scripts/build_b_phase90_gnome_raw_structure_ingest.py

reproduce-b-phase91-gnome-mp-formula-prefilter:
	$(PYTHON) scripts/build_b_phase91_gnome_mp_formula_prefilter.py

reproduce-b-phase92-gnome-mp-neighbor-gap-analysis:
	$(PYTHON) scripts/build_b_phase92_gnome_mp_neighbor_gap_analysis.py

reproduce-ncs-phase89-submission-integration-map:
	$(PYTHON) scripts/build_ncs_phase89_submission_integration_map.py
