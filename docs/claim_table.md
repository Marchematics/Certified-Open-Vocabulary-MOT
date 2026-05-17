# Claim Table

Each paper-facing claim is linked to a public artifact, a local verification
command when available, and the intended limitation language.

## Main Claim Map

| Claim | Evidence path | Reproduction / check | Limitation |
|---|---|---|---|
| PARC releases strict `alpha=0.10` CTC learned-hybrid cell links. | `outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_strict_alpha010_smallK.csv` | `PYTHONPATH=code/parc_track python -m parc_track.cli phase19 success-domain` | Candidate instances are CTC link candidates; this is release certification, not an end-to-end cell tracker claim. |
| CTC strict-release audit queue is human-confirmed with release-queue FTR 0.0. | `outputs/milestones/ctc_strict_human_audit/table_ctc_strict_human_audit_go_no_go.csv` | `python scripts/validate_public_bundle.py outputs/milestones/ctc_strict_human_audit` | No microscopy-expert adjudication is claimed unless separately documented. |
| Materials discovery supports strict stable-candidate release under partial DFT verification. | `outputs/milestones/scientific_domain_materials/table_materials_primary_results.csv` | `python scripts/validate_public_bundle.py outputs/milestones/scientific_domain_materials` | Uses public WBM/Matbench-derived labels and controlled partial-positive masking. |
| Modern materials-model sensitivity remains compatible with release/refusal certification. | `outputs/milestones/scientific_domain_materials/table_materials_modern_model_sensitivity.csv` | Inspect `MATERIALS_DISCOVERY_CLOSEOUT.md` | Sensitivity rows are source-quality diagnostics, not a leaderboard claim. |
| Materials results are robustly reported under boundary-label and fixed-gamma sensitivity. | `outputs/milestones/scientific_domain_materials/table_materials_stability_threshold_robustness.csv`; `table_materials_gamma_sensitivity.csv` | `sha256sum -c outputs/milestones/scientific_domain_materials/MANIFEST_SHA256.txt` | Some sensitivity settings expose boundary fragility and should be reported as such. |
| Materials robustness figures are paper-ready diagnostics derived from completed CSVs. | `outputs/milestones/scientific_domain_materials/materials_threshold_robustness_figure.pdf`; `materials_gamma_sensitivity_heatmap.pdf`; `materials_raw_vs_parc_ftr_panel.pdf` | `python -m parc_track.cli phase19 success-domain` | The ALIGNN margin-excluded 25meV K=100 row is a boundary sensitivity case, not a strict pass. |
| Verified-positive removal is load-bearing for the CTC learned and materials main/boundary rows. | `outputs/milestones/scientific_release_success_map/table_verified_positive_removal_load_bearing.csv`; `VERIFIED_POSITIVE_REMOVAL_LOAD_BEARING_CLOSEOUT.md` | `python scripts/run_verified_positive_removal_load_bearing_ablation.py` | Completed candidate-level rerun over six preselected CTC/materials rows; the ALIGNN margin-excluded 25meV K=100 row remains boundary sensitivity, not a strict pass. |
| PARC changes computational follow-up queues without adding human labels. | `outputs/milestones/no_human_scientific_consequence/table_materials_computational_followup.csv`; `table_ctc_lineage_consequence.csv`; `table_spacenet_map_consequence.csv`; `table_no_human_consequence_summary.csv`; `figure_no_human_consequence_main.pdf` | `python scripts/build_no_human_scientific_consequence.py && python scripts/build_no_human_paper_integration.py` | Materials follow-up is retrospective public-DFT/hidden-label evaluation, not experimental synthesis; CTC and SpaceNet consequences use official benchmark labels; randomized/unsafe rows are stress controls, not primary positive deployments. |
| PARC changes a frozen materials computational follow-up queue under public-label replay. | `outputs/milestones/materials_computational_followup_trial/table_materials_computational_trial_summary.csv`; `table_materials_computational_trial_release_cards.csv`; `figure_materials_computational_trial_main.pdf` | `python scripts/build_materials_computational_trial.py` | Quasi-prospective replay with public DFT labels revealed after the frozen release/refusal decision; no new DFT, experimental synthesis, or true prospective discovery is claimed. |
| PARC changes downstream scientific artifacts under official labels. | `outputs/milestones/official_downstream_consequence/table_official_downstream_consequence_summary.csv`; `table_ctc_official_lineage_metric_summary.csv`; `table_spacenet_map_metric_summary.csv`; `figure_official_downstream_consequence.pdf` | `python scripts/build_official_downstream_consequence.py` | CTC values are official-GT lineage-edge and TRA/AOGM-style edit-burden proxies, not official challenge leaderboard scores; SpaceNet values are building-persistence map proxies from official identities; no new human labels are introduced. |
| PARC is packaged as a reusable scientific AI release-certification governance protocol. | `outputs/milestones/release_certification_benchmark/table_release_certification_cards.csv`; `table_release_certification_track_registry.csv`; `table_release_governance_checklist.csv`; `figure_release_certification_benchmark_map.pdf` | `python scripts/build_release_certification_benchmark_cards.py` | This is a release-card wrapper over completed evidence and diagnostics; protocol-only ideas remain schema/checklist items and are not promoted to completed evidence. |
| iWildCam animal-present release is a real human-audited operational `alpha=0.20` result. | `outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_human_audit_primary_results.csv` | `python scripts/validate_public_bundle.py outputs/milestones/scientific_domain_iwildcam_human_audit` | Strict `alpha=0.10` remains refusal; this is an operational, not strict, ecology result. |
| SpaceNet 7 real audit validates release/refusal workflow but does not promote K=100 to flagship. | `outputs/spacenet7_real_audit/table_spacenet7_real_audit_go_no_go.csv` | Inspect `SPACENET7_REAL_AUDIT_GO_NO_GO.md` | K=50 is diagnostic low-volume success; K=100 primary real-audit request refused. |
| PARC refuses unsafe high-volume or low-evidence requests. | `outputs/milestones/scientific_release_success_map/table_cross_domain_evidence_matrix.csv` | `PYTHONPATH=code/parc_track python -m parc_track.cli phase19 success-domain` | Refusal is a valid certified outcome; it is not a utility guarantee. |
| Refusal rows are diagnosed by finite-resolution, evidence-mass, and selector-power categories. | `outputs/milestones/scientific_release_success_map/table_refusal_diagnosis_ilp.csv` | `python -m parc_track.cli phase19 success-domain` | ILP infeasibility is asserted only when rows fail before graph compatibility; no candidate graph is fabricated. |
| Release/refusal behavior is summarized by measurable success-domain features. | `outputs/milestones/scientific_release_success_map/table_success_domain_predictor.csv`; `figure_success_domain_map.pdf`; `table_validity_assumptions_by_domain.csv` | `python -m parc_track.cli phase19 success-domain` | The predictor is descriptive and small-sample, not a causal or deployment classifier. |
| Audit2000 and second-review evidence support the visual-audit benchmark. | `outputs/milestones/reliability_fortress/audit_review/` | `sha256sum -c outputs/milestones/reliability_fortress/MANIFEST_SHA256.txt` | The benchmark is public-safe and does not include raw videos or montage imagery. |
| Community can run the schema-to-certification path without external datasets. | `outputs/benchmarks/parc_certification_benchmark/tiny_fixture/` | `PYTHONPATH=code/parc_track python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api` | Tiny fixture verifies code paths, not paper-scale statistical power. |

## Reviewer Route

Use this route when checking the repository from a clean clone:

1. Run `pytest -q tests`.
2. Verify the root manifest with `sha256sum -c MANIFEST_SHA256.txt`.
3. Validate the key public bundles with `scripts/validate_public_bundle.py`.
4. Inspect the claim-specific evidence paths in the table above.
5. Check limitation language before treating a diagnostic row as a main claim.

## Claim Status Vocabulary

- **Strict:** predeclared risk target, typically `alpha=0.10`, with non-empty releases and realized FTR below the target.
- **Operational:** useful release/refusal demonstration at a less stringent or deployment-oriented operating point.
- **Diagnostic:** informative support or failure analysis that should not be promoted to a flagship claim.
- **Refusal:** certified no-release outcome under the requested protocol.

For the consolidated evidence matrix, use:

```bash
PYTHONPATH=code/parc_track python -m parc_track.cli phase19 success-domain
```
