# Reviewer Guide

This guide is the fastest route through the public-safe PARC artifact package.
It separates what can be reproduced from the repository alone from experiments
that require the original datasets and external proposal generators.

## What Can Be Checked Without Raw Datasets?

- Unit and fixture tests:

  ```bash
  PYTHONPATH=code/parc_track python -m pytest -q tests
  ```

- Tiny certification fixture:

  ```bash
  PYTHONPATH=code/parc_track python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api
  ```

- Public-bundle safety:

  ```bash
  python scripts/validate_public_bundle.py outputs/milestones/reliability_fortress
  python scripts/validate_public_bundle.py outputs/milestones/scientific_release_success_map
  sha256sum -c MANIFEST_SHA256.txt
  ```

- Paper-facing result tables under `outputs/milestones/*` and
  `outputs/benchmarks/parc_certification_benchmark/`.

## What Requires External Datasets?

Full end-to-end regeneration of candidate universes requires datasets and
proposal-generator outputs that are not redistributed here:

- OVT-B, TAO, BURST, LVIS/LV-VIS/O-VIS for open-world perception rows.
- Cell Tracking Challenge microscopy images/annotations for CTC universe
  regeneration.
- SpaceNet 7 imagery and labels for building-link universe regeneration.
- iWildCam images for camera-trap audit visualization.
- Matbench Discovery / WBM source tables for materials-source reruns.

See `DATA_AVAILABILITY.md` for the exact public-safe boundary.

## Strict Alpha=0.10 Successes

- CTC learned-hybrid source:
  `outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_strict_alpha010_smallK.csv`
- CTC human-confirmed strict audit closeout:
  `outputs/milestones/ctc_strict_human_audit/table_ctc_strict_human_audit_go_no_go.csv`
- Materials CGCNN strict stable-candidate release:
  `outputs/milestones/scientific_domain_materials/table_materials_primary_results.csv`
- Materials threshold/gamma robustness:
  `outputs/milestones/scientific_domain_materials/table_materials_stability_threshold_robustness.csv`
  and `table_materials_gamma_sensitivity.csv`.

## Operational Alpha=0.20 Demonstrations

- iWildCam human-audited animal-present release:
  `outputs/milestones/scientific_domain_iwildcam_human_audit/`
- SpaceNet 7 real-audit low-volume diagnostic release and K=100 refusal:
  `outputs/milestones/spacenet_real_audit_final/`.

## Human-Audit Files

- Audit2000 and second-review evidence:
  `outputs/milestones/reliability_fortress/audit_review/`
- CTC strict human-confirmed audit:
  `outputs/milestones/ctc_strict_human_audit/`
- iWildCam human-confirmed audit:
  `outputs/milestones/scientific_domain_iwildcam_human_audit/`
- SpaceNet real-audit final evidence:
  `outputs/milestones/spacenet_real_audit_final/`

## Interpreting Refusal

An empty release is a valid certified outcome.  Refusal rows should be read as
"the requested release volume/risk level was not supported by the available
one-sided verification evidence", not as a software failure.

## Recommended Review Order

1. Read `docs/claim_table.md`.
2. Verify `MANIFEST_SHA256.txt`.
3. Run `PYTHONPATH=code/parc_track python -m pytest -q tests`.
4. Inspect `outputs/milestones/scientific_release_success_map/table_cross_domain_evidence_matrix.csv`.
5. Inspect the human-audit closeouts for any claim involving real review.
