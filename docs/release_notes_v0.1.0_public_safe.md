# v0.1.0-public-safe Release Notes

Public-safe reproducibility release for PARC.

## Included

- PARC certification code and CLI.
- Frozen configs and public-safe result tables.
- Human-audit benchmark CSVs and second-review evidence.
- CTC learned-hybrid strict release tables and human-confirmed strict audit closeout.
- Materials discovery candidate-release milestone.
- iWildCam and SpaceNet release/refusal audit milestones.
- Open-world visual certification/generalization artifacts.
- Tiny fixture for schema-to-certification smoke testing.
- SHA256 manifest and public-bundle validation tooling.
- Reviewer-oriented documentation:
  - `docs/reviewer_guide.md`
  - `docs/claim_table.md`
  - `docs/audit_protocol.md`
  - `docs/benchmark_card.md`
  - `docs/limitations.md`

## Excluded

Raw videos, raw images, raw annotations, raw crystal structures, model weights,
detector/tracker repositories, Hugging Face caches, GPU caches, frame caches,
and montage images are excluded.  Obtain external datasets and weights from
their original maintainers.

## Verification

```bash
PYTHONPATH=code/parc_track python -m pytest -q tests
sha256sum -c MANIFEST_SHA256.txt
```
