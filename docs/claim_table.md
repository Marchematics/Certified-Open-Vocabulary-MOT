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
| Block heterogeneity diagnostics do not show silent over-release in the public candidate-level materials rows. | `outputs/milestones/block_heterogeneity_robustness/table_size_matched_rerun.csv`; `table_downsampled_blockmax_stress.csv`; `figure_block_size_superuniformity.pdf`; `B2_APPROXIMATE_EVALUE_VALIDITY_LEMMA.md` | `python scripts/build_block_heterogeneity_robustness.py` | Candidate-level size-matched/downsampled reruns are completed for materials only. CTC and SpaceNet are scoped aggregate/audit-sample diagnostics because their full candidate-level universes are not included in this public package. |
| Materials A1/A2 prospective-validation plans are preregistered feasibility artifacts, not completed evidence. | `outputs/milestones/materials_prospective_validation_protocols/A1_TEMPORAL_SPLIT_PREREGISTRATION.md`; `A2_INDEPENDENT_DFT_CROSSVALIDATION_PREREGISTRATION.md`; `table_materials_prospective_validation_go_no_go.csv` | `python scripts/build_materials_prospective_validation_protocols.py` | A1 requires timestamped public-label snapshots; A2 requires an independent DFT join table. Until those inputs exist, these rows must not be promoted as completed positive results. |
| Materials A3 prospective DFT follow-up has a frozen protocol and input gate, not a completed result. | `outputs/milestones/materials_prospective_dft_followup/PROTOCOL.md`; `protocol.yaml`; `table_dft_followup_freeze_status.csv`; `selection_frozen.csv`; `dft_job_manifest.csv` | `python scripts/build_materials_prospective_dft_followup_protocol.py` | The current package lacks an unlabeled generated crystal pool and public crossmatch outputs, so candidate selection and DFT jobs are intentionally empty. Do not report this as new DFT evidence. |
| Materials A3-v2 CHGNet prospective scorer is locally executable but did not support a DFT arm. | `outputs/milestones/materials_prospective_dft_followup_chgnet_v2/table_chgnet_v2_freeze_status.csv`; `table_chgnet_v2_selection_diagnostics.csv`; `selection_frozen_chgnet_v2.csv`; `dft_job_manifest_chgnet_v2.csv` | `python scripts/build_materials_prospective_chgnet_v2.py` | CHGNet replaced the blocked ALIGNN-FF scorer for arbitrary generated candidates. The PGCGM pool produced zero PARC release candidates at the predeclared gate, so selection and DFT manifests remain empty. |
| Materials A3-v3 near-hull CHGNet gate remains a prospective no-go diagnostic, not DFT evidence. | `outputs/milestones/materials_prospective_dft_followup_chgnet_v3/candidate_universe_chgnet_v3.csv`; `candidate_scores_chgnet_v3.csv`; `table_chgnet_v3_endpoint_diagnostics.csv`; `selection_frozen_chgnet_v3.csv`; `dft_job_manifest_chgnet_v3.csv` | `python scripts/build_materials_prospective_chgnet_v3.py` | The v3 pool contains 5,000 near-hull isovalent/chemically similar substitutions scored by CHGNet. Strict `alpha=0.10,K=500`, strict `K=300`, and operational `alpha=0.20,K=500` all refused; no DFT jobs are exported and no positive result is claimed. |
| Materials A3-v4 MatterGen prospective gate is frozen pre-outcome but remains non-evidence. | `outputs/milestones/mattergen_parc_prospective_dft_followup/table_mattergen_environment_status.csv`; `table_mace_environment_status.csv`; `candidate_universe_strict_public_label_free.csv`; `selection_frozen_v4.csv`; `dft_job_manifest_v4.csv` | `python scripts/build_a3_v4_formal_selection_gate.py` | MatterGen generation/scoring progressed to a formal pre-DFT selection gate. Smoke/pilot raw-generation files are removed from the pre-release GitHub package; formal selection, public-label exclusion tables, DFT manifests, and run-package hashes remain. Do not report this as a prospective DFT result until outcomes are analyzed under the frozen policy. |
| Fixed-budget downstream utility is reported as certified stopping/refusal, not fixed-size reranking improvement. | `outputs/milestones/fixed_budget_downstream_utility/table_materials_budget_utility_primary.csv`; `table_materials_baseline_frontier.csv`; `table_ctc_lineage_consequence.csv`; `table_spacenet_persistence_consequence.csv` | `python scripts/build_experimental_finalization_milestones.py` | Raw top-R is a matched-volume diagnostic. The practical claim is lower false downstream entries or certified refusal at the requested budget. |
| Primary effect-size statistics are frozen for the materials and CTC endpoints. | `outputs/milestones/primary_statistics/table_primary_endpoints.csv`; `table_paired_bootstrap_seed_rows.csv`; `table_holm_correction.csv` | `python scripts/build_experimental_finalization_milestones.py` | P-values are descriptive paired diagnostics; theorem-level risk control remains the formal certificate. |
| Materials robustness is consolidated as a stability/block/gamma triad. | `outputs/milestones/materials_robustness_triad/table_stability_definition_robustness.csv`; `table_block_definition_robustness.csv`; `table_gamma_sensitivity.csv`; `table_block_size_heterogeneity.csv` | `python scripts/build_experimental_finalization_milestones.py` | Robustness tables include boundary diagnostics. Boundary-sensitive rows should not be promoted to headline strict passes. |
| The final baseline matrix separates target-object mismatch from deployable release certificates. | `outputs/milestones/baseline_matrix_final/table_baseline_target_objects.csv`; `table_baseline_primary_results.csv`; `table_baseline_certificate_properties.csv` | `python scripts/build_experimental_finalization_milestones.py` | PU, selective conformal, threshold, and e-BH-style rows are different-target comparators unless their certificate properties match PARC. |
| A1/A2 materials prospective-validation finalization remains tightly scoped. | `outputs/milestones/materials_temporal_validation/table_materials_temporal_primary.csv`; `outputs/milestones/materials_independent_dft_validation/table_independent_dft_primary_results.csv`; `outputs/milestones/materials_independent_dft_validation/table_independent_dft_candidate_matches.csv` | `python scripts/build_experimental_finalization_milestones.py`; A2 diagnostic builder: `python scripts/build_materials_independent_oqmd_validation.py` | A1 needs timestamped public-label snapshots. A2 now includes a completed OQMD exact-structure diagnostic, but exact-match coverage is too low for a primary independent validation claim. |
| Materials A1/A2 alex-mp external-snapshot validation is completed but negative/discordant on the exact-match subset. | `outputs/milestones/materials_alex_mp_a1_a2_validation/table_alex_mp_a2_primary_results.csv`; `table_alex_mp_a1_temporal_external_snapshot_primary.csv`; `table_alex_mp_a2_candidate_matches.csv`; `table_alex_mp_label_discordance.csv` | `python scripts/build_materials_alex_mp_a1_a2_validation.py` | This is a completed external-snapshot exact-structure diagnostic, not a positive independent validation. Formula-only matches are excluded from FTR; the high discordance and high alex-mp FTR must be reported as a label-source boundary, not promoted. |
| Phase30 pivots hard-upgrade evidence away from A3 and into completed decision-level evidence. | `outputs/milestones/main_evidence_hard_upgrade_phase30/table_main_evidence_decision_matrix.csv`; `outputs/milestones/ctc_decision_utility_main_evidence/table_ctc_release_utility_primary.csv`; `outputs/milestones/cross_domain_blind_audit_main_evidence/table_cross_domain_audit_primary.csv`; `outputs/milestones/materials_source_discordance_stress_test/table_materials_external_source_stress_summary.csv` | `python scripts/build_phase30_main_evidence_hard_upgrade.py` | A3 remains a high-risk bonus track. Materials external-source rows are completed negative diagnostics only; the non-A3 main evidence is CTC decision utility plus completed human-audit release/refusal behavior. |
| Phase31 aligns preregistered endpoints with allowed headline claims. | `outputs/milestones/protocol_claim_alignment/table_predeclared_endpoint_audit.csv`; `table_claim_to_evidence_alignment.csv`; `outputs/milestones/materials_fixed_budget_scientific_utility/table_materials_fixed_budget_lead_numbers.csv`; `outputs/milestones/ctc_scientific_artifact_consequence/table_ctc_false_lineage_edges_avoided.csv`; `docs/abstract_claim_scope.md` | `python scripts/build_phase31_protocol_claim_alignment.py` | Primary-headline rows must map to completed artifacts, source SHA256 hashes, and exact manuscript sentences. OQMD/alex-mp remain diagnostic or stress-test rows, CGCNN K=100 remains calibration/validity support, and A3 cannot support prospective materials-discovery language unless its DFT gates are met. |
| A3-v4 MatterGen formal selection gate is frozen before DFT but remains release-only pilot evidence. | `outputs/milestones/mattergen_parc_prospective_dft_followup/selection_frozen_v4.csv`; `dft_job_manifest_v4.csv`; `table_phase29_go_no_go.csv` | `python scripts/build_a3_v4_formal_selection_gate.py` | Formal available-source exclusion uses WBM/Matbench formula exclusion plus alex-mp structure matching. OQMD/GNoME/AFLOW/NOMAD structure indexes remain unavailable; the manifest is release-only and pre-outcome, not prospective materials discovery evidence. |
| A3-v4 Phase29b DFT comparator manifest addendum is frozen before outcomes but remains non-evidence. | `outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_addendum.csv`; `table_phase29b_dft_manifest_addendum_summary.csv` | `python scripts/build_a3_v4_dft_manifest_addendum.py` | Addendum uses only frozen scores, ranks, release status and public-label exclusion status. raw_topR is identical to the full PARC release set in this endpoint, raw-only tail is absent, and no DFT outcome is claimed. |
| A3-v4 Phase29c raw-top100 extra-tail manifest is frozen before outcomes but remains non-evidence. | `outputs/milestones/mattergen_parc_prospective_dft_followup/dft_job_manifest_v4_phase29c_raw_top100_extra_tail.csv`; `table_phase29c_raw_top100_extra_tail_summary.csv` | `python scripts/build_a3_v4_phase29c_extra_tail_manifest.py` | Phase29c uses only strict public-label-free status, frozen consensus score and release-addendum candidate ids. Local QE execution inputs are prepared separately, but no DFT outcome or prospective discovery claim is made. |
| Phase33 finalizes the NMI presubmission go/no-go package. | `outputs/milestones/nmi_presubmission_final/presubmission_inquiry_final.md`; `one_page_evidence_table_final.csv`; `submission_go_no_go_checklist.csv`; `forbidden_claims_final.md` | `python scripts/build_phase33_nmi_presubmission_final.py` | Final inquiry is 600-750 words; A3 remains pending, OQMD/alex-mp remain stress tests, and all required go/no-go checks must pass before using the package. |
| Phase32 packages NMI presubmission claims with desk-risk guardrails. | `outputs/milestones/nmi_presubmission_package/presubmission_inquiry_v1.md`; `one_page_evidence_table.csv`; `nmi_editor_cold_read.md`; `docs/nmi_submission_positioning.md` | `python scripts/build_phase32_nmi_presubmission_package.py` | Uses only phase31-approved primary-headline claims for lead numbers; iWildCam/SpaceNet are audited boundary evidence, OQMD/alex-mp are stress tests, and A3 pending rows cannot appear as positive evidence. |
| iWildCam animal-present release is a real human-audited operational `alpha=0.20` result. | `outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_human_audit_primary_results.csv` | `python scripts/validate_public_bundle.py outputs/milestones/scientific_domain_iwildcam_human_audit` | Strict `alpha=0.10` remains refusal; this is an operational, not strict, ecology result. |
| SpaceNet 7 real audit validates release/refusal workflow but does not promote K=100 to flagship. | `outputs/milestones/spacenet_real_audit_final/table_spacenet_k100_refusal_diagnostics.csv`; `table_spacenet_k50_release_audit.csv` | `python scripts/validate_public_bundle.py outputs/milestones/spacenet_real_audit_final` | K=50 is diagnostic low-volume success; K=100 primary real-audit request refused. Prefill review sheets are not part of the pre-release evidence package. |
| PARC refuses unsafe high-volume or low-evidence requests. | `outputs/milestones/scientific_release_success_map/table_cross_domain_evidence_matrix.csv` | `PYTHONPATH=code/parc_track python -m parc_track.cli phase19 success-domain` | Refusal is a valid certified outcome; it is not a utility guarantee. |
| Refusal rows are diagnosed by finite-resolution, evidence-mass, and selector-power categories. | `outputs/milestones/scientific_release_success_map/table_refusal_diagnosis_ilp.csv` | `python -m parc_track.cli phase19 success-domain` | ILP infeasibility is asserted only when rows fail before graph compatibility; no candidate graph is fabricated. |
| Release/refusal behavior is summarized by measurable success-domain features. | `outputs/milestones/scientific_release_success_map/table_success_domain_predictor.csv`; `figure_success_domain_map.pdf`; `table_validity_assumptions_by_domain.csv` | `python -m parc_track.cli phase19 success-domain` | The predictor is descriptive and small-sample, not a causal or deployment classifier. |
| Audit2000 and second-review evidence support the visual-audit benchmark. | `outputs/milestones/reliability_fortress/audit_review/` | `sha256sum -c outputs/milestones/reliability_fortress/MANIFEST_SHA256.txt` | The benchmark is public-safe and does not include raw videos or montage imagery. |
| Community can run the schema-to-certification path without external datasets. | `outputs/benchmarks/parc_certification_benchmark/tiny_fixture/` | `PYTHONPATH=code/parc_track python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api` | Tiny fixture verifies code paths, not paper-scale statistical power. |

| Materials temporal replay remains blocked unless timestamped t0/t1 public-label snapshots are available. | `outputs/milestones/materials_temporal_replay_completed/table_temporal_primary.csv`; `table_temporal_snapshot_inventory.csv` | `python scripts/build_non_a3_main_evidence_upgrades.py` | This milestone is protocol-only for temporal validation and must not be promoted to completed quasi-prospective evidence. |
| Fixed-budget scientific utility is quantified as downstream follow-up value. | `outputs/milestones/fixed_budget_scientific_utility_trial/table_decision_curve.csv`; `table_false_followups_prevented.csv`; `table_cost_per_true_candidate.csv` | `python scripts/build_non_a3_main_evidence_upgrades.py` | Completed public-label utility evidence; the claim is certified stopping/refusal, not fixed-size reranking superiority. |
| Adversarial release stress rows support refusal-boundary diagnostics. | `outputs/milestones/adversarial_release_stress_trial/table_adversarial_stress_trials.csv`; `table_refusal_boundary.csv` | `python scripts/build_non_a3_main_evidence_upgrades.py` | Stress rows are controls/diagnostics and not primary positive evidence. |
| Selector optimality diagnostics separate evidence-mass failure from greedy selector limitations. | `outputs/milestones/selector_optimality_diagnostics/table_greedy_vs_ilp.csv`; `table_mass_vs_graph_failure.csv`; `table_conflict_loss.csv` | `python scripts/build_non_a3_main_evidence_upgrades.py` | ILP/MIS claims are limited to available diagnostics; candidate graphs are not fabricated. |

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
| A3-v4 local QE execution layer is prepared on this machine but remains pre-outcome non-evidence. | `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/qe_job_manifest.csv`; `QE_ENVIRONMENT_STATUS.csv`; `table_qe_pseudopotential_map.csv` | `python scripts/build_a3_qe_local_run_package.py` | Quantum ESPRESSO input decks and pseudopotential hashes are recorded. Third-party pseudopotential payloads are ignored local dependencies, not tracked paper evidence. No DFT outcome or prospective discovery claim is made until outcomes are analyzed under the conservative failure policy. |
| Pre-release repository cleanup removes obsolete intermediates without changing claim-bearing evidence. | `outputs/milestones/pre_release_repository_cleanup/table_pre_release_removed_artifacts.csv`; `table_pre_release_kept_artifacts.csv` | `pytest -q tests/test_pre_release_repository_cleanup.py` | Cleanup is repository hygiene only. It removes legacy dumps, prefill/draft label aids, package archives, and runtime scratch files; it creates no new scientific evidence and does not change A3 selection/manifests. |
| A separate materials-label discordance paper route has a completed minimal probe but not a full NMI-launch result. | `outputs/milestones/materials_label_discordance_preregistration/DATA_ACCESS_GO_NO_GO.md`; `table_minimal_discordance_probe.csv`; `table_frontier_model_scores.csv`; `table_downstream_ranking_flip_summary.csv`; `MATERIALS_LABEL_DISCORDANCE_EXPERIMENT_CLOSEOUT.md` | `python scripts/score_materials_label_discordance_frontier_models.py`; `python scripts/build_materials_label_discordance_experiment.py`; `pytest -q tests/test_materials_label_discordance_preregistration.py` | The existing WBM-vs-alex exact-structure probe passes the discordance launch-signal threshold, and CHGNet/MACE same-denominator scores make the primary ranking endpoint executable. The primary stable-F1 ranking flip gate does not pass, so this is not yet an NMI-launch result or an MP-vs-alex full-snapshot claim. PARC remains only an optional probe. |
| The MP-vs-alex full-snapshot discordance signal is not amplified in ML high-confidence score strata. | `outputs/milestones/materials_selection_conditional_discordance/table_selection_conditional_go_no_go.csv`; `table_top_decile_discordance.csv`; `table_decile_discordance.csv`; `SELECTION_CONDITIONAL_DISCORDANCE_CLOSEOUT.md` | `python scripts/build_materials_selection_conditional_discordance.py`; `pytest -q tests/test_materials_selection_conditional_discordance.py` | Completed go/no-go diagnostic for Proposition B. On the 287 exact-match MP-vs-alex denominator, baseline discordance is about 0.108 and none of ALIGNN-FF, CHGNet, or MACE-MP reaches top-decile discordance >=0.30 or >=2x baseline. This closes the NMI discordance-nugget route unless a new frozen source pair/model panel is preregistered. |
| A3-v4 ALIGNN-FF pre-outcome scores are frozen as a scorer diagnostic, not DFT evidence. | `outputs/milestones/mattergen_alignnff_preoutcome_scoring_snapshot/candidate_scores_alignnff_4039.csv`; `candidate_scores_alignnff_strict_public_label_free_2990.csv`; `table_alignnff_rank_correlation.csv`; `table_alignnff_topk_overlap.csv`; `table_alignnff_release_vs_tail_score_contrast.csv` | `OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python scripts/build_a3_alignnff_preoutcome_scores.py`; `pytest -q tests/test_a3_alignnff_preoutcome_scores.py` | Completed pre-outcome scorer diagnostic only. It does not modify A3 selection, manifests, or the DFT run package; no DFT outcome, utility, or prospective materials-discovery claim is made from this snapshot. |
| Non-A3 frontier reinforcement plan pivots headline upgrades away from A3. | `outputs/milestones/non_a3_frontier_reinforcement_redesign/table_non_a3_frontier_path_priorities.csv`; `table_non_a3_go_no_go.csv` | `python scripts/build_non_a3_frontier_reinforcement.py`; `pytest -q tests/test_non_a3_frontier_reinforcement.py` | This is an execution plan and evidence triage artifact. It creates no new A3 positive claim and does not modify A3 selection, manifests, or DFT packages. |
| MP-Alex exact-structure discordance atlas is a completed public-data benchmark-reliability result. | `outputs/milestones/materials_label_source_discordance_atlas/table_mp_alex_discordance_atlas_summary.csv`; `table_mp_alex_near_hull_localization.csv`; `figure_materials_label_source_discordance_atlas_source.csv` | `python scripts/build_non_a3_frontier_reinforcement.py`; `pytest -q tests/test_non_a3_frontier_reinforcement.py` | Completed source-label uncertainty diagnostic: 43,139 strict MP-Alex matches and 5,060 exact-stability disagreements. Not a positive PARC independent validation, not external databases as interchangeable ground truth, and not prospective materials discovery. |
| Source-uncertainty refusal layer is currently a feasibility/scenario diagnostic, not a completed PARC queue overlay. | `outputs/milestones/materials_source_uncertainty_refusal_layer/table_candidate_level_overlay_feasibility.csv`; `table_materials_source_uncertainty_overlay_scenarios.csv`; `table_source_uncertainty_refusal_policy_template.csv` | `python scripts/build_non_a3_frontier_reinforcement.py`; `pytest -q tests/test_non_a3_frontier_reinforcement.py` | Candidate-level PARC material identifiers are missing from the public aggregate utility tables, so the exact queue overlay is blocked. Scenario rows must not be promoted to primary evidence. |
| External blind audit packet is frozen for iWildCam and SpaceNet but labels remain pending. | `outputs/milestones/external_blind_audit_packet/external_blind_audit_packet_manifest.csv`; `external_blind_auditor_A_template.csv`; `external_blind_auditor_B_template.csv`; `external_blind_adjudication_template.csv` | `python scripts/build_external_audit_and_route_c_diagnostics.py`; `pytest -q tests/test_external_audit_and_route_c_diagnostics.py` | Audit-ready packet only. Auditor templates hide arm, score, rank and existing labels; no completed external audit evidence is claimed until labels and adjudication return. |
| Route C+ reduced frontier panel is a completed no-go diagnostic, not a headline result. | `outputs/milestones/route_c_reduced_frontier_panel_diagnostic/table_route_c_reduced_frontier_panel_summary.csv`; `table_route_c_reduced_panel_model_metrics.csv`; `table_route_c_reduced_panel_scores_public_safe.csv` | `python scripts/build_external_audit_and_route_c_diagnostics.py`; `pytest -q tests/test_external_audit_and_route_c_diagnostics.py` | Existing WBM-vs-alex probe only: no top-model flip, no ordering flip, and no full MP-Alex Route C primary result. Do not promote to headline materials evidence. |
| Materials source-uncertainty overlay is now candidate-level for the ALIGNN-FF K=300/500 queues. | `outputs/milestones/materials_queue_source_uncertainty_overlay/table_materials_queue_overlay_summary.csv`; `table_materials_queue_overlay_lead_contrasts.csv`; `table_materials_queue_overlay_candidate_rows.csv` | `python scripts/build_materials_queue_source_uncertainty_overlay.py`; `pytest -q tests/test_materials_queue_source_uncertainty_overlay.py` | Completed candidate-level diagnostic only. alex-mp exact-structure rows are used as a source-discordance stress test, formula-only rows are excluded from alex-mp FTR denominators, and the result must not be promoted to positive independent validation or prospective materials discovery. |
| Phase37 locks the submission to two hard anchors and explicit forbidden-claim replacements. | `outputs/milestones/submission_scope_lock_phase37/table_submission_evidence_hierarchy.csv`; `table_release_contract_comparator_matrix.csv`; `table_forbidden_to_allowed_submission_claims.csv` | `python scripts/build_phase37_submission_scope_lock.py`; `pytest -q tests/test_submission_scope_lock_phase37.py` | This is a framing/governance artifact, not a new experiment. Only materials fixed-budget utility and CTC artifact consequence are primary; A3, external blind audit pending rows, and OQMD/alex-mp diagnostics cannot support primary positive claims. |
| Week 0 protocol freeze preregisters the next materials/DFT/MLIP/CTC audit package before outcome claims. | `outputs/milestones/ncs_week0_protocol_freeze/NCS_WEEK0_PROTOCOL_FREEZE.pdf`; `table_frozen_candidate_universe.csv`; `table_dft_audit_sampling_scheme.csv`; `table_go_no_go_rules.csv` | `python scripts/build_ncs_week0_protocol_freeze.py`; `pytest -q tests/test_ncs_week0_protocol_freeze.py` | Protocol-freeze only. OSF/Zenodo upload is prepared but not claimed as completed; this creates no new result, no DFT outcome, no prospective materials-discovery claim, and no positive independent materials validation claim. |
| Week 1-4 materials temporal + MLIP audit has directional MLIP support; its original temporal gate is superseded by the current-MP snapshot row below. | `outputs/milestones/materials_temporal_mlip_audit/table_week1_4_go_no_go.csv`; `table_mlip_dense_audit_summary.csv`; `table_temporal_hull_shift_audit.csv` | `python scripts/build_materials_temporal_mlip_audit.py`; `pytest -q tests/test_materials_temporal_mlip_audit.py` | CHGNet, MACE-MP, and ALIGNN-FF pre-outcome scores support the PARC-release versus extra-tail direction, but this is not DFT evidence. The original temporal table was no-go before t0/t1 acquisition; use the subsequent current-MP hull-shift row for completed temporal utility/drift diagnostics. |
| Materials t0/t1 current-MP hull-shift snapshot is acquired and supports a utility/drift diagnostic, not a strict temporal certificate. | `outputs/milestones/materials_t0_t1_snapshot_acquisition/table_t1_hull_ftr_delta.csv`; `table_t0_t1_gate_assessment.csv`; `table_t0_t1_label_join.csv` | `python scripts/acquire_materials_t0_t1_snapshots.py --reuse-mp-entries`; `pytest -q tests/test_materials_t0_t1_snapshot_acquisition.py` | Current MP t1 hull labels are computed for the frozen K=300/500 WBM queue candidates. PARC has lower conservative t1-hull FTR than raw top-K and stable-to-unstable drift is not more concentrated in PARC, but PARC FTR remains above `alpha=0.10`; therefore this is not prospective materials discovery and not a strict temporal alpha certificate. |
| Phase50 paperizes the current-MP hull-shift audit as an NCS materials version-shift utility result. | `outputs/milestones/ncs_phase50_materials_version_shift_paperization/figure_materials_version_shift_inputs.csv`; `table_materials_t1_hull_shift_summary.csv`; `table_materials_evidence_status.csv`; `table_ncs_display_item_plan.csv` | `python scripts/build_ncs_phase50_51_materials_paperization.py`; `pytest -q tests/test_ncs_phase50_51_materials_paperization.py` | The allowed manuscript claim is lower current-label FTR and non-concentrated stable-to-unstable drift for frozen PARC queues relative to raw top-K. The explicit forbidden claim remains t1 `alpha=0.10` control or prospective materials discovery. |
| Phase51 provides candidate-level explanation of t1 materials failures without claiming CHGNet/MACE consensus validation. | `outputs/milestones/ncs_phase51_materials_t1_candidate_explanation/table_materials_t1_mlip_candidate_audit.csv`; `table_materials_t1_false_explanation_summary.csv`; `table_materials_mlip_availability_status.csv`; `table_phase51_go_no_go.csv` | `python scripts/build_ncs_phase50_51_materials_paperization.py`; `pytest -q tests/test_ncs_phase50_51_materials_paperization.py` | Candidate-level WBM queue rows are merged with t1 labels, near-hull flags, ALIGNN-FF release scores, CGCNN/MEGNet model-zoo predictions, raw ranks, release margins, and source-boundary tags. CHGNet/MACE WBM queue scores are unavailable in the public-safe cache, so this is not a completed MLIP consensus claim. |
| Phase52 adds uncertainty quantification for the current-MP t1 utility audit. | `outputs/milestones/ncs_phase52_materials_t1_uncertainty/table_t1_bootstrap_ci.csv`; `table_t1_randomization_tests.csv` | `python scripts/build_ncs_phase52_materials_t1_uncertainty.py`; `pytest -q tests/test_ncs_phase52_materials_t1_uncertainty.py` | Chemical-system bootstrap intervals and rank-bin randomization tests support the version-shift utility interpretation. They do not turn the t1 result into a strict temporal certificate, and `MLIP_consensus_raw_minus_PARC` is explicitly marked not evaluable without CHGNet/MACE queue scores. |
| Phase53 adds a true candidate-level CHGNet/MACE score audit for the frozen WBM queue. | `outputs/milestones/ncs_phase53_chgnet_mace_candidate_audit/table_materials_candidate_level_chgnet_mace_audit.csv`; `table_chgnet_mace_support_by_policy.csv`; `table_chgnet_mace_disagreement_by_t1_status.csv`; `table_phase53_go_no_go.csv` | `python scripts/build_ncs_phase53_chgnet_mace_candidate_audit.py`; `pytest -q tests/test_ncs_phase53_chgnet_mace_candidate_audit.py` | CHGNet/MACE score-support proxies favor PARC release over raw-only extra-tail at K=300/500, but the t1 false-case mechanism is only partial: false PARC candidates are not primarily explained by CHGNet/MACE disagreement or near-hull status. Raw MLIP energies are not reference-hull `e_above_hull`, DFT evidence, or prospective discovery. |
| Phase56 adds a version-shift accounting lemma for fixed release sets. | `outputs/milestones/ncs_phase56_version_shift_accounting/supplement_version_shift_accounting.tex`; `table_version_shift_decomposition.csv`; `figure_version_shift_decomposition_inputs.csv` | `python scripts/build_ncs_phase56_version_shift_accounting.py`; `pytest -q tests/test_ncs_phase56_version_shift_accounting.py` | The t1 current-label burden decomposes exactly into t0 FTR plus stable-to-current-not-stable drift minus not-stable-to-current-stable drift. This is deterministic accounting, not a new t1 alpha certificate and not prospective discovery. |
| Phase57 extends the materials baseline frontier to t1 labels and CHGNet/MACE score proxies. | `outputs/milestones/ncs_phase57_t1_mlip_baseline_frontier/table_t1_mlip_baseline_frontier.csv`; `table_baseline_capability_t1_mlip.csv`; `figure_t1_mlip_baseline_frontier_inputs.csv` | `python scripts/build_ncs_phase57_t1_mlip_baseline_frontier.py`; `pytest -q tests/test_ncs_phase57_t1_mlip_baseline_frontier.py` | Empirical baselines are compared under current-MP labels and Phase53 score proxies. Matched raw top-R can match PARC at the same volume, so the allowed claim remains certified stopping/refusal rather than matched-volume ranking improvement. |
| Phase58 hardens reproducibility with an evidence-scope ledger. | `outputs/milestones/ncs_phase58_reproducibility_hardening/EVIDENCE_SCOPE_LEDGER.csv`; `REPRODUCE_PHASE49.md`; `REPRODUCE_T1_HULL_AUDIT.md`; `REPRODUCE_MLIP_AUDIT.md`; `DATA_PROVENANCE_MATERIALS.md` | `python scripts/build_ncs_phase58_reproducibility_hardening.py`; `python scripts/validate_evidence_ledger.py`; `pytest -q tests/test_ncs_phase58_reproducibility_hardening.py` | Every paper-facing materials claim maps to a source artifact, SHA256 hash, validation command, and overclaim guardrail. Boundary rows explicitly forbid prospective discovery, t1 alpha control, and overclaiming Phase53 raw CHGNet/MACE score proxies as reference-hull or DFT evidence. |
| Phase60 tests a simple PARC-V support-gated version-aware release route. | `outputs/milestones/ncs_phase60_parc_v_version_aware_release/table_parc_v_primary_results.csv`; `table_parc_v_gate_audit.csv`; `PARC_V_PREREGISTRATION.md` | `python scripts/build_ncs_phase60_parc_v_version_aware_release.py`; `pytest -q tests/test_ncs_phase60_parc_v_version_aware_release.py` | The CHGNet/MACE support-gated subset is non-empty but fails the predeclared headline thresholds: it does not lower current-MP t1 FTR to 0.15 or alpha=0.10 and is not a full SCS rerun. The allowed role is completed no-go/feasibility audit, not a new PARC-V theorem, DFT result, or prospective materials discovery claim. |
| Phase61 tests PARC-M multi-evidence fusion. | `outputs/milestones/ncs_phase61_parc_m_multi_evidence_fusion/table_parc_m_primary_results.csv`; `table_parc_m_source_evalue_audit.csv`; `table_parc_m_gate_audit.csv`; `PARC_M_PREREGISTRATION.md` | `python scripts/build_ncs_phase61_parc_m_multi_evidence_fusion.py`; `pytest -q tests/test_ncs_phase61_parc_m_multi_evidence_fusion.py` | Fixed fusion of original PARC evidence with ALIGNN/CHGNet/MACE score-derived e-proxies gives a medium empirical current-MP t1 improvement (~0.03-0.04 FTR) with nontrivial release sizes, but it fails the theorem-grade/headline gate because auxiliary scores are queue-level proxies without full null-superset calibration. It is not a multi-evidence e-value certificate, DFT result, or prospective discovery claim. |

## Phase62 Full-Calibration MLIP E-Values

Status: `completed_full_calibration_sources_no_headline_signal`.

CHGNet and MACE-MP auxiliary scores are now audited as full-calibration
e-value sources over the frozen WBM one-per-composition-family calibration
denominator, with target-overlap rows excluded before computing block maxima.
This resolves the Phase61 queue-only proxy blocker for source availability, but
the milestone is still a t0/t1 queue audit: it is not DFT evidence, not a t1
alpha certificate, and not a prospective materials-discovery claim.

## Phase63 PARC-A Active Verification

Status: `primary_strong_positive_CTC_only`.

PARC-A is a certificate-directed active verification result: in CTC K=100,
0.5% score-targeted one-sided audit yields 20/20 nonempty safe seeds and zero
observed false releases, while matched-budget random audit remains empty and the
random transition control requires 200x the targeted budget. Materials rows are
kept as boundary/secondary public-label active-audit evidence and must not be
promoted to prospective materials discovery.

## Phase65b PARC-A Mechanism Diagnostics

Status: `completed_mechanism_supported`.

Phase65b explains the CTC score-targeted active-audit transition by measuring
whether audited positives remove the calibration null-superset block maxima
that constrain release evidence. This is a mechanism diagnostic over existing
CTC labels, not new human labeling and not materials evidence.

## Phase69 Durability-Budgeted PARC

Status: `completed_durability_budgeted_release_card_diagnostic`.

Phase69 converts the Phase67c t0-only durability-risk predictor into
release-card decision artifacts. Candidate-level durability-budget support:
`true`. Risk-triage support:
`true`.

The allowed claim is that t0 public-label release-card features can route
high-risk materials candidates to recertification and reduce retained
stable-to-unstable burden. Unless the stricter budget gate passes, this is not a
repaired `alpha=0.10` certificate. Even when the candidate-level budget gate
passes, it remains scoped to t0-stable released rows and is not a full
seed-level release certificate, not DFT evidence, and not prospective materials
discovery.

## Phase74 Risk-Gated Recertification

Status: `completed_risk_gated_recertification_no_go`.

Phase74 tests the strongest constructive follow-up to Phase69b: move the
durability-risk gate upstream, rebuild the filtered null-superset denominator,
recompute e-values and rerun SCS. The primary prior row
(`K=300`, retain fraction `0.4`,
support `t1_10pct_support`) returns `0/20`
non-empty seeds. The full grid does not recover a non-empty self-consistent
current-MP release certificate. The allowed claim is therefore a principled
no-go for risk-gated recertification on the queue-limited current-MP audit; it
does not supersede Phase69b risk triage.

## Phase75 Active Versioned Recertification

Status: `completed_active_recertification_no_go`.

Phase75 closes the active versioned recertification route on the frozen grid: targeted calibration-side t1 support does not restore a GO-medium/GO-strong current-MP release.

Allowed scope: versioned public-label recertification emulation. Forbidden
claims: prospective materials discovery, DFT validation, label-free durability
prediction, or current-MP alpha control unless the GO-strong row is explicitly
reported with its public-label scope.

## Phase76 PARC Lifecycle Calculus

Status: `completed_lifecycle_calculus_synthesis`.

Phase76 consolidates PARC as a release-card lifecycle calculus rather than a
single selection rule. It supplies supplement-ready theory statements, a JSON
release-card schema, lifecycle state table, CTC active-audit replay, materials
reference-update replay, and lifecycle capability baselines. The allowed claim
is conceptual and infrastructural: PARC supports release, refusal, audit
acquisition, expiry and recertification states. It does not convert Phase74 or
Phase75 materials no-go outcomes into a current-MP alpha certificate.

## Phase77 NCS Architecture Freeze

Status: `completed_NCS_architecture_freeze`.

Phase77 freezes the NCS manuscript spine around PARC release-card lifecycle
certification. The primary empirical positive is PARC-A in CTC active
verification. Materials is frozen as a lifecycle stress test showing
reference-version expiry, risk triage and recertification/refusal boundaries.
Phase77 explicitly stops further materials fast-fix tuning from entering the
main story.

## Phase78 CTC Real One-Sided Audit

Status: `completed_CTC_real_one_sided_audit_integration`.

Phase78 integrates the existing CTC strict human-confirmed audit package into
the NCS lifecycle story. The strict-release queue has 1064 human-confirmed rows
with zero not-same and zero uncertain labels. This strengthens PARC-A practical
credibility, but it should be described as trained/human-confirmed one-sided
review rather than microscopy-expert adjudication unless a separate expert
review is documented.

## Phase79 Controlled Evolving-Reference Generality Simulation

Status: `completed_controlled_generality_simulation`.

Phase79 is the Phase B breadth check. It shows whether the Phase67c materials
durability-risk pattern is recoverable as a controlled neighborhood-driven
reference-update mechanism. Phase79 is a synthetic mechanism demonstration, not
a new external domain and not a release certificate.

GO status: `True`. If GO is true, the NCS text may claim that the materials
pattern has a controlled generality demonstration. If false, the durability-risk
claim remains materials-specific.
## Phase80 Finding-First NCS Submission Package


Status: `completed_finding_first_submission_package`.

Phase80 incorporates Phase79 into the NCS paper spine and reframes the
submission as a reliability study of scientific AI candidate release. The
allowed center is: targeted one-sided audit can unlock certified release, while
reference-update durability risk is primarily a chemical-system/reference
neighborhood property rather than a candidate-margin/rank property. Phase79
adds controlled mechanism support for this breadth claim.

This is not a new empirical result, not a release certificate, not DFT evidence
and not prospective materials discovery. DFT v2 remains quarantined until
stable_exact and workflow gates pass.
## Phase67d Durability-Risk Headline Hardening


Status: `completed_headline_display_hardening`.

Phase67d completes the review-facing hardening for the durability-risk
centerpiece. The headline model is the pruned t0-only system
margin-landscape/activity model, with ROC-AUC `0.809`
and chemical-system bootstrap 95% CI `0.722` to
`0.874`. Calibration, base-rate and memorization controls
are frozen in the Phase67d artifact.

Allowed claim: t0 public-label system margin landscape and activity support
release-card durability-risk triage.

Forbidden claim: label-free deployment prediction, current-MP alpha repair, DFT
validation, or prospective materials discovery.

## Phase81 CTC External Blind Audit Mini-Study

Status: `packet_frozen_pending_independent_labels`.

Phase81 freezes a two-auditor blind CTC link-audit mini-study packet (600 rows)
with auditor templates, adjudication template, ingest schema and arm registry.
It is designed to turn the PARC-A CTC active-audit result into a real
verification-workflow study once independent labels are returned.  Current
tracked source rows do not contain a true raw-only top-K arm; this is recorded
as a blocker.  Phase81 is not completed positive evidence and must not be
written as expert microscopy adjudication, raw-only comparator success, or a
new CTC benchmark.

## Phase82 CTC AI Preannotation for Human Review

Status: `ai_preannotations_completed_human_review_pending`.

Phase82 generates geometry-only AI preannotations for the frozen Phase81 CTC
blind-audit packet and writes an AI-assisted human review sheet.  The AI uses
only blinded geometry/frame metadata and does not use arm membership, score,
rank, prior human labels or official GT.  These labels are review aids only:
Phase82 is not completed human evidence, external audit success, expert
microscopy adjudication or new CTC ground truth.

## Phase83 Necessity and Prevented Harm

Status: `completed_paperization_synthesis_not_new_empirical_result`.

Phase83 packages the one-sided necessity argument and completed downstream
harm artifacts into a paper-facing release-card framing.  It supports the claim
that PARC is not just a selector: the one-sided information structure requires
a null-superset denominator, a refusal state and active-audit logic.  It also
summarizes completed prevented-harm rows for CTC, materials and SpaceNet.  It
is synthesis only and does not add new labels, DFT evidence, prospective
materials discovery or a new alpha certificate.

## Phase84 Real-Audit PARC-A Replication

Status: `workflow_replication_packet_frozen_pending_external_labels`.

Phase84 freezes a stronger PARC-A real-audit workflow replication packet.  The
primary question is whether external human one-sided calibration support can
rerun PARC-A and unlock a K=100 CTC release, followed by an independent release
audit.  Current status is protocol/packet only: external labels have not been
returned, PARC-A has not been rerun from human calibration positives, and no
real-audit success claim is allowed.  The tracked Phase81 source still lacks a
true raw-only top-K arm, so random same-budget control is the primary workflow
control and raw-overlap rows remain diagnostic.

## Phase85 External AI-Materials Claim-Decay Audit Pilot

Status: `protocol_frozen_current_reference_verdicts_pending`.

Phase85 freezes a B-line pilot protocol for auditing whether public AI/materials
stability claims remain stable under frozen current-reference checks.  Current
status is protocol only: no current-reference verdicts have been produced, no
source-specific decay rate is claimed, and this is not A-paper main evidence.
The pilot is designed to decide whether B should expand into an independent
claim-decay paper or stop without delaying A.

## Phase86 Claim-Decay Access Preflight

Status: `access_preflight_completed_claim_registry_empty`.

Phase86 records dependency status, source endpoint smoke checks, Materials
Project version status when available, and empty claim/current-reference
registry templates for the B-line external AI-materials claim-decay audit.  It
is preflight only: no claim rows have been ingested, no current-reference
verdicts have been produced, and no decay result is allowed.

## Phase87 Minimal External Claim Registry

Status: `minimal_registry_frozen_current_reference_verdicts_pending`.

Phase87 freezes a two-source B-line claim registry for Matbench Discovery/WBM
and GNoME public stable-materials rows.  Current status is registry only: no
current-reference verdicts have been produced, exact raw-structure matching is
not complete, and no claim-decay result is allowed.

## Phase88 Low-Cost Editorial Hardening

Status: `completed_editorial_synthesis_not_new_evidence`.

Phase88 packages low-cost NCS submission hardening actions: first-screen
release-card framing, Phase83 necessity/prevented-harm placement, lifecycle
capability table, Phase81/83 write-permission boundaries, and overclaim scrub.
It is synthesis only and must not be used as new empirical evidence.

## Phase88 B-Line Current-Reference Smoke

Status: `low_cost_smoke_completed_not_claim_decay`.

Phase88 performs a low-cost current-reference smoke using the frozen Phase87
registry and the existing WBM t0/t1 snapshot. It provides WBM existing-snapshot
smoke verdicts only. GNoME and OQMD remain pending, exact raw-structure matching
is not complete, and no source-level claim-decay metric is allowed.

## Phase89 B-Line Exact-Structure Audit Readiness

Status: `readiness_and_protocol_only_current_verdicts_pending`.

Phase89 prepares the B-line exact-structure audit by checking GNoME raw-zip
access, defining local cache rules, freezing the extraction and matching plan,
and keeping current-reference verdicts pending. It is not claim-decay evidence.

## Phase89 NCS Submission Integration Map

Status: `integration_plan_ready_not_manuscript_rewrite`.

Phase89 maps Phase88 low-cost editorial hardening artifacts to concrete
A-manuscript integration targets and blocking submission checks. It is not new
evidence and not a completed manuscript submission.

## Phase90 B-Line GNoME Raw-Structure Ingest

Status: `derived_structure_ingest_completed_current_verdicts_pending`.

Phase90 completes public-safe derived raw-structure ingest for the frozen
GNoME registry rows by reading the local `by_id.zip` cache, hashing raw CIF
bytes, and extracting pymatgen structure metadata. Raw CIF files remain outside
git-tracked artifacts. Exact MP matching and current-reference verdicts remain
pending, so Phase90 is not claim-decay evidence.

## Phase91 CTC Strong-Model Surrogate Annotation

Status: `strong_model_surrogate_annotations_completed_not_human_evidence`.

Phase91 uses a deterministic image-based surrogate annotator over the frozen
Phase84 CTC blind-audit packets and writes human-label-compatible replacement
CSVs. It can replace manual labeling operationally for dry runs, but it is not external human audit evidence and not external human evidence. It is also not
expert microscopy adjudication, official CTC ground truth, completed real-audit
PARC-A replication, or materials/DFT evidence.

## Phase91 B-Line GNoME MP Formula Prefilter

Status: `mp_formula_prefilter_completed_exact_matching_pending`.

Phase91 queries current Materials Project summary records by chemical system
for frozen GNoME rows and writes formula-prefilter candidate IDs. It does not
report current stability verdicts, does not perform exact structure matching,
and is not source-level claim-decay evidence, A-paper evidence, prospective
discovery, or new DFT evidence.
