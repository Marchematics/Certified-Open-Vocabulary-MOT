# Claim Table

Each paper-facing claim is linked to a public artifact, a local verification
command when available, and the intended limitation language.

| Claim | Evidence path | Reproduction / check | Limitation |
|---|---|---|---|
| PARC releases strict `alpha=0.10` CTC learned-hybrid cell links. | `outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_strict_alpha010_smallK.csv` | `PYTHONPATH=code/parc_track python -m parc_track.cli phase19 success-domain` | Candidate instances are CTC link candidates; this is release certification, not an end-to-end cell tracker claim. |
| CTC strict-release audit queue is human-confirmed with release-queue FTR 0.0. | `outputs/milestones/ctc_strict_human_audit/table_ctc_strict_human_audit_go_no_go.csv` | `python scripts/validate_public_bundle.py outputs/milestones/ctc_strict_human_audit` | No microscopy-expert adjudication is claimed unless separately documented. |
| Materials discovery supports strict stable-candidate release under partial DFT verification. | `outputs/milestones/scientific_domain_materials/table_materials_primary_results.csv` | `python scripts/validate_public_bundle.py outputs/milestones/scientific_domain_materials` | Uses public WBM/Matbench-derived labels and controlled partial-positive masking. |
| Modern materials-model sensitivity remains compatible with release/refusal certification. | `outputs/milestones/scientific_domain_materials/table_materials_modern_model_sensitivity.csv` | Inspect `MATERIALS_DISCOVERY_CLOSEOUT.md` | Sensitivity rows are source-quality diagnostics, not a leaderboard claim. |
| Materials results are robustly reported under boundary-label and fixed-gamma sensitivity. | `outputs/milestones/scientific_domain_materials/table_materials_stability_threshold_robustness.csv`; `table_materials_gamma_sensitivity.csv` | `sha256sum -c outputs/milestones/scientific_domain_materials/MANIFEST_SHA256.txt` | Some sensitivity settings expose boundary fragility and should be reported as such. |
| iWildCam animal-present release is a real human-audited operational `alpha=0.20` result. | `outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_human_audit_primary_results.csv` | `python scripts/validate_public_bundle.py outputs/milestones/scientific_domain_iwildcam_human_audit` | Strict `alpha=0.10` remains refusal; this is an operational, not strict, ecology result. |
| SpaceNet 7 real audit validates release/refusal workflow but does not promote K=100 to flagship. | `outputs/spacenet7_real_audit/table_spacenet7_real_audit_go_no_go.csv` | Inspect `SPACENET7_REAL_AUDIT_GO_NO_GO.md` | K=50 is diagnostic low-volume success; K=100 primary real-audit request refused. |
| PARC refuses unsafe high-volume or low-evidence requests. | `outputs/milestones/scientific_release_success_map/table_cross_domain_evidence_matrix.csv` | `PYTHONPATH=code/parc_track python -m parc_track.cli phase19 success-domain` | Refusal is a valid certified outcome; it is not a utility guarantee. |
| Audit2000 and second-review evidence support the visual-audit benchmark. | `outputs/milestones/reliability_fortress/audit_review/` | `sha256sum -c outputs/milestones/reliability_fortress/MANIFEST_SHA256.txt` | The benchmark is public-safe and does not include raw videos or montage imagery. |
| Community can run the schema-to-certification path without external datasets. | `outputs/benchmarks/parc_certification_benchmark/tiny_fixture/` | `PYTHONPATH=code/parc_track python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api` | Tiny fixture verifies code paths, not paper-scale statistical power. |

For the consolidated evidence matrix, use:

```bash
PYTHONPATH=code/parc_track python -m parc_track.cli phase19 success-domain
```
