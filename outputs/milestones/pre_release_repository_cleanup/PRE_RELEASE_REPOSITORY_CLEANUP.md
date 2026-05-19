# Pre-Release Repository Cleanup

Status: completed pre-release hygiene pass.

This milestone records the repository normalization performed before the public pre-release snapshot. The cleanup removes obsolete intermediate bundles, prefill/draft label aids, package archives, and runtime scratch files while preserving completed paper-facing evidence, claim-boundary guardrails, and the frozen A3 pre-DFT selection/manifests.

## Scope

The pre-release repository keeps:

- completed evidence milestones referenced by `docs/claim_table.md`;
- final human-confirmed audit tables;
- source-discordance diagnostics that are explicitly scoped as diagnostics or stress tests;
- A3-v4 MatterGen formal selection, DFT run package, and local QE input layer, all still pre-outcome;
- tests and documentation that enforce the claim boundaries.

The pre-release repository removes:

- legacy internal result dumps superseded by paper-facing milestones;
- generated tarball packages that can be recreated by `make package-release`;
- CTC strict-audit prefill/private-key package after final human-confirmed labels were frozen;
- iWildCam second-review draft and correction-draft files after final human-confirmed labels were frozen;
- SpaceNet review prefill sheets while retaining final blind/metadata/audit summary tables;
- helper scripts whose sole purpose was to create prefill or draft label sheets;
- local runtime scratch files and caches.

## Claim Boundary

This cleanup does not create new evidence. It also does not modify A3-v4 selection or DFT manifests. The active A3 Quantum ESPRESSO outputs remain local runtime state under `A3_QE_LOCAL_RUN/qe_outputs/` and are ignored until outcomes are formally analyzed under the conservative failure policy.

No row removed here may be cited as completed evidence. Removed prefill/draft rows were adjudication aids, not final paper-facing human labels.

## Verification

Run:

```bash
pytest -q tests/test_pre_release_repository_cleanup.py
python scripts/validate_public_bundle.py outputs/milestones/pre_release_repository_cleanup
sha256sum -c outputs/milestones/pre_release_repository_cleanup/MANIFEST_SHA256.txt
```

Then run the normal repository checks:

```bash
pytest -q tests
sha256sum -c MANIFEST_SHA256.txt
```
