# Phase94 Current-MP Relaxed Recertification Frontier

Status: `completed_current_mp_relaxed_recertification_boundary_no_go`.

Phase94 sweeps small K and relaxed alpha values after Phase66/74/75 no-go
results. It tests whether a current-MP public-label recertification replay can
recover a non-empty release frontier under the same no-leakage discipline.

Best boundary row:

- alpha: `0.2`;
- K: `25`;
- support mode: `t1_10pct_support`;
- audit policy: `low_risk_score_targeted_t1_audit`;
- audit budget fraction: `0.1`;
- nonempty seeds: `14/20`;
- safe seeds: `11/20`;
- mean release size: `15.850000`;
- mean t1 FTR if nonempty: `0.202619`.

Gate audit:

| gate                                             | threshold                                                                                           | status   | evidence_scope                                                                                                                                                                                                                                                                                                                                                 |
|:-------------------------------------------------|:----------------------------------------------------------------------------------------------------|:---------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| strict_alpha_0p10_current_mp_recertified_release | alpha=0.10; nonempty_seeds>=18; safe_seeds>=18; mean_FTR_t1<=0.10; mean_release_size>=20            | FAIL     | current_MP_relaxed_recertification_frontier;queue_limited_public_label_t1_recertification_emulation;small_K_alpha_grid_reported_in_full;t1_labels_used_only_as_calibration_side_one_sided_positives;test_side_t1_labels_used_only_after_release_for_FTR;not_DFT_evidence;not_prospective_materials_discovery;not_strict_alpha_0p10_certificate_if_relaxed_only |
| relaxed_alpha_current_mp_operating_release       | alpha in {0.15,0.20}; nonempty_seeds>=18; safe_seeds>=18; mean_FTR_t1<=alpha; mean_release_size>=20 | FAIL     | current_MP_relaxed_recertification_frontier;queue_limited_public_label_t1_recertification_emulation;small_K_alpha_grid_reported_in_full;t1_labels_used_only_as_calibration_side_one_sided_positives;test_side_t1_labels_used_only_after_release_for_FTR;not_DFT_evidence;not_prospective_materials_discovery;not_strict_alpha_0p10_certificate_if_relaxed_only |
| boundary_nonempty_any_row                        | any row has nonempty_seeds>0                                                                        | PASS     | current_MP_relaxed_recertification_frontier;queue_limited_public_label_t1_recertification_emulation;small_K_alpha_grid_reported_in_full;t1_labels_used_only_as_calibration_side_one_sided_positives;test_side_t1_labels_used_only_after_release_for_FTR;not_DFT_evidence;not_prospective_materials_discovery;not_strict_alpha_0p10_certificate_if_relaxed_only |
| full_grid_reported                               | all predeclared K alpha support policy budget rows reported                                         | PASS     | current_MP_relaxed_recertification_frontier;queue_limited_public_label_t1_recertification_emulation;small_K_alpha_grid_reported_in_full;t1_labels_used_only_as_calibration_side_one_sided_positives;test_side_t1_labels_used_only_after_release_for_FTR;not_DFT_evidence;not_prospective_materials_discovery;not_strict_alpha_0p10_certificate_if_relaxed_only |

Evidence scope: `current_MP_relaxed_recertification_frontier;queue_limited_public_label_t1_recertification_emulation;small_K_alpha_grid_reported_in_full;t1_labels_used_only_as_calibration_side_one_sided_positives;test_side_t1_labels_used_only_after_release_for_FTR;not_DFT_evidence;not_prospective_materials_discovery;not_strict_alpha_0p10_certificate_if_relaxed_only`.
