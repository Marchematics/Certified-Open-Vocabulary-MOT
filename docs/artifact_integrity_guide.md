# Artifact Integrity Verification Guide

This guide gives the shortest integrity checks for the public-safe repository.

## Root manifest

Run:

```bash
sha256sum -c MANIFEST_SHA256.txt
```

This verifies tracked public files against the root SHA256 manifest.

The root manifest intentionally excludes `MANIFEST_SHA256.txt` itself to avoid a self-referential checksum.

## Milestone manifests

Many frozen artifact directories include their own `MANIFEST_SHA256.txt`. Verify them from the repository root, for example:

```bash
sha256sum -c outputs/milestones/scientific_domain_materials/MANIFEST_SHA256.txt
sha256sum -c outputs/milestones/ctc_strict_human_audit/MANIFEST_SHA256.txt
```

## Public-bundle validation

Run the repository validator on public-safe bundles:

```bash
python scripts/validate_public_bundle.py outputs/milestones/reliability_fortress
python scripts/validate_public_bundle.py outputs/milestones/ctc_strict_human_audit
python scripts/validate_public_bundle.py outputs/milestones/scientific_domain_iwildcam_human_audit
```

## Raw-data exclusion

The validator and documentation are designed to catch or discourage:

- raw images and videos;
- raw dataset annotations that cannot be redistributed;
- model weights;
- detector/tracker caches;
- local absolute paths;
- generated montages or thumbnails that reveal restricted data.

## When a check fails

If a manifest check fails after editing a public file, regenerate the manifest as part of the same commit. If a public-bundle validation fails, fix the unsafe path or move the file outside the public package.

## Reviewer note

Manifest verification checks file integrity. It does not imply that all external raw datasets are bundled; those must be obtained from the original providers.
