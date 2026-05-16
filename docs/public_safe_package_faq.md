# Public-Safe Package FAQ

This FAQ explains what reviewers and downstream users can inspect without downloading restricted raw datasets or model weights.

## What is included?

- Certification code and command-line entry points.
- Frozen public-safe milestone tables and configuration files.
- Human-audit CSVs that contain derived labels and anonymized candidate identifiers.
- Tiny fixtures for checking the certification API and public schema.
- SHA256 manifests for integrity verification.

## What is intentionally excluded?

- Raw videos, raw images, and raw dataset annotations governed by third-party licenses.
- Model weights and detector or tracker caches.
- Local absolute paths, GPU caches, and intermediate visualization montages that may reveal restricted data.

## Can the main claims be checked without raw datasets?

Yes for table integrity, schema compliance, audit status, release/refusal summaries, and public-bundle safety checks. Full reruns from pixels or raw trajectories require acquiring the original datasets from their official providers.

## How should reviewers start?

1. Read `docs/reviewer_checklist.md`.
2. Read `docs/claim_table.md`.
3. Run `pytest -q tests`.
4. Verify `sha256sum -c MANIFEST_SHA256.txt`.
5. Inspect `outputs/milestones/` for frozen public-safe evidence.

## Why are some rows certified refusals?

PARC is a release-or-refusal interface. An empty certified release is a valid safety outcome when evidence mass, block coverage, or compatibility constraints are insufficient.
