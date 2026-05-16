# Reviewer Reproducibility Checklist

This checklist summarizes the shortest public-safe path for reviewers to inspect the PARC artifact package.

## Basic Checks

- Run the test suite with `PYTHONPATH=code/parc_track python -m pytest -q tests`.
- Validate public bundles with `scripts/validate_public_bundle.py`.
- Verify file integrity with `sha256sum -c MANIFEST_SHA256.txt`.

## Claim-Level Checks

- See `docs/claim_table.md` for the claim-to-artifact evidence map.
- See `docs/audit_protocol.md` for human-audit label definitions and verified-positive rules.
- See `docs/reviewer_guide.md` for strict, operational, and diagnostic result locations.
- See `REPRODUCIBILITY.md` for full benchmark reproduction notes.

## Scope Checks

- Raw datasets, raw videos/images, model weights, frame caches, and local caches are intentionally excluded.
- Empty certified release is a valid safety outcome, not a runtime failure.
- Human-confirmed rows should not be described as expert-adjudicated unless an expert review is separately documented.

## Fast Command Path

```bash
PYTHONPATH=code/parc_track python -m pytest -q tests
python scripts/validate_public_bundle.py outputs/milestones/reliability_fortress
python scripts/validate_public_bundle.py outputs/milestones/scientific_release_success_map
sha256sum -c MANIFEST_SHA256.txt
```
