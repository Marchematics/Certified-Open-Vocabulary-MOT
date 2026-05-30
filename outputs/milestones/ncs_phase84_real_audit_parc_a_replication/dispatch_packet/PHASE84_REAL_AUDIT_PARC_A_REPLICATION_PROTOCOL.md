# Phase84 Real-Audit PARC-A Replication Protocol

Status: `workflow_replication_packet_frozen_pending_external_labels`.

Objective:

Test whether external human one-sided calibration support can reproduce the
PARC-A CTC release workflow, rather than merely auditing an already released
set or replaying masked official labels.

Frozen design:

- candidate source: Phase81 frozen CTC external blind audit packet;
- risk target: `alpha = 0.10`;
- headline budget: `K = 100`;
- calibration support rule: only consensus `same_cell_supported` human labels
  may enter the verified-positive set;
- `unsupported` and `uncertain` labels are never trusted negatives;
- primary human-review route: blind no-AI templates;
- optional operational route: AI-assisted templates from Phase82, disclosed as
  AI-assisted and not used as independent evidence without human confirmation;
- raw-only comparator is unavailable in the tracked Phase81 source rows, so
  Phase84 uses random same-budget control and raw-overlap/boundary diagnostics.

Primary GO gate after labels return:

```text
human-calibration PARC-A produces non-empty release at K=100
release size >= 80
conservative release-audit FTR <= 0.05
Clopper-Pearson 95% upper bound <= 0.10
two-auditor agreement kappa >= 0.70
random same-budget arm remains empty or fails evidence threshold
no arm-label leakage
```

Current packet rows:

| packet                             | source_arm                                        |   rows | primary_role   | blinded_template                                              | ai_assisted_template                                                | evidence_scope                                                                                                                                                                                   |
|:-----------------------------------|:--------------------------------------------------|-------:|:---------------|:--------------------------------------------------------------|:--------------------------------------------------------------------|:-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| calibration_audit                  | calibration_one_sided_support_pool                |    150 | yes            | phase84_calibration_audit_blind_template.csv                  | phase84_calibration_audit_ai_assisted_template.csv                  | phase84_real_audit_parc_a_replication_protocol;external_labels_pending;workflow_replication_packet_frozen;not_completed_positive_evidence;not_new_CTC_ground_truth;not_materials_or_DFT_evidence |
| release_audit                      | parc_release_core                                 |    250 | yes            | phase84_release_audit_blind_template.csv                      | phase84_release_audit_ai_assisted_template.csv                      | phase84_real_audit_parc_a_replication_protocol;external_labels_pending;workflow_replication_packet_frozen;not_completed_positive_evidence;not_new_CTC_ground_truth;not_materials_or_DFT_evidence |
| random_same_budget_control         | random_blind_control_from_available_reviewed_rows |     55 | yes            | phase84_random_same_budget_control_blind_template.csv         | phase84_random_same_budget_control_ai_assisted_template.csv         | phase84_real_audit_parc_a_replication_protocol;external_labels_pending;workflow_replication_packet_frozen;not_completed_positive_evidence;not_new_CTC_ground_truth;not_materials_or_DFT_evidence |
| raw_overlap_diagnostic             | raw_topK_reference_overlap                        |    100 | no             | phase84_raw_overlap_diagnostic_blind_template.csv             | phase84_raw_overlap_diagnostic_ai_assisted_template.csv             | phase84_real_audit_parc_a_replication_protocol;external_labels_pending;workflow_replication_packet_frozen;not_completed_positive_evidence;not_new_CTC_ground_truth;not_materials_or_DFT_evidence |
| hard_negative_or_uncertain_control | hard_negative_or_uncertain_control                |     45 | no             | phase84_hard_negative_or_uncertain_control_blind_template.csv | phase84_hard_negative_or_uncertain_control_ai_assisted_template.csv | phase84_real_audit_parc_a_replication_protocol;external_labels_pending;workflow_replication_packet_frozen;not_completed_positive_evidence;not_new_CTC_ground_truth;not_materials_or_DFT_evidence |

Claim boundary:

- allowed now: Phase84 freezes the external real-audit PARC-A replication
  packet and protocol;
- forbidden now: real-audit PARC-A success, completed external adjudication,
  new CTC ground truth, raw-only superiority, materials evidence, or DFT
  evidence.

Evidence scope: `phase84_real_audit_parc_a_replication_protocol;external_labels_pending;workflow_replication_packet_frozen;not_completed_positive_evidence;not_new_CTC_ground_truth;not_materials_or_DFT_evidence`.
