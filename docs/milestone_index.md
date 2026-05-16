# Milestone Index

This index points reviewers to the main frozen public-safe artifact groups.

| Milestone | Path | Role |
|---|---|---|
| Reliability fortress | `outputs/milestones/reliability_fortress/` | Core open-vocabulary reliability and audit benchmark artifacts. |
| PARC certification benchmark | `outputs/benchmarks/parc_certification_benchmark/` | Public-safe schema, fixture, and benchmark package. |
| CTC learned certification | `outputs/milestones/scientific_domain_ctc_learned/` | Biomedical learned-source cell-link certification evidence. |
| CTC strict human audit | `outputs/milestones/ctc_strict_human_audit/` | Human-confirmed strict-release audit queue closeout. |
| Materials discovery | `outputs/milestones/scientific_domain_materials/` | Stable-material candidate release under partial DFT verification. |
| iWildCam human audit | `outputs/milestones/scientific_domain_iwildcam_human_audit/` | Human-audited ecological animal-present operational release. |
| Scientific success map | `outputs/milestones/scientific_release_success_map/` | Consolidated cross-domain success/refusal matrix. |
| SpaceNet real audit | `outputs/spacenet7_real_audit/` | Human-audit release/refusal workflow diagnostics for building links. |

## How to use this index

1. Start with `docs/claim_table.md` to identify the claim of interest.
2. Open the corresponding milestone path above.
3. Read the local closeout or run report.
4. Validate the bundle with `scripts/validate_public_bundle.py` when applicable.
5. Verify the relevant `MANIFEST_SHA256.txt`.

## Naming policy

Public artifact names avoid venue-specific labels. Older internal names may appear in provenance sidecars only when needed to preserve reproducibility history.
