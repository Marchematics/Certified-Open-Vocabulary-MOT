PYTHON ?= python
PYTHONPATH ?= code/parc_track

.PHONY: test tiny-fixture reproduce-main-tables reproduce-main-figures reproduce-no-human-consequence reproduce-materials-computational-trial reproduce-official-downstream-consequence reproduce-release-certification-benchmark reproduce-block-heterogeneity-robustness reproduce-materials-prospective-validation validate-public-bundle verify-manifest package-release package-release-story package-scientific-release

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
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/release_story/paper_diagnostics

verify-manifest:
	sha256sum -c MANIFEST_SHA256.txt

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

package-release-story:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase13 release-story

package-scientific-release: package-release
