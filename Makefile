PYTHON ?= python
PYTHONPATH ?= code/parc_track

.PHONY: test tiny-fixture reproduce-main-tables reproduce-main-figures validate-public-bundle verify-manifest package-release package-release-story package-scientific-release

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

reproduce-main-figures:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase16 generality-closeout

validate-public-bundle:
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/reliability_fortress
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/release_story
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_ctc_learned
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_spacenet7_prospective
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_iwildcam_human_audit
	$(PYTHON) scripts/validate_public_bundle.py outputs/milestones/scientific_domain_materials
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

package-release-story:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m parc_track.cli phase13 release-story

package-scientific-release: package-release
