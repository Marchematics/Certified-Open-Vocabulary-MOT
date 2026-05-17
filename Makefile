PYTHON ?= python
PYTHONPATH ?= code/parc_track

.PHONY: test tiny-fixture reproduce-main-tables reproduce-main-figures reproduce-no-human-consequence validate-public-bundle verify-manifest package-release package-release-story package-scientific-release

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

reproduce-main-figures:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase16 generality-closeout

reproduce-no-human-consequence:
	$(PYTHON) scripts/build_no_human_scientific_consequence.py
	$(PYTHON) scripts/build_no_human_paper_integration.py

validate-public-bundle:
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/reliability_fortress
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/release_story
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_ctc_learned
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_spacenet7_prospective
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_iwildcam_human_audit
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_materials
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_release_success_map
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/no_human_scientific_consequence
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

package-release-story:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase13 release-story

package-scientific-release: package-release
