# Phase92 CTC Model-Surrogate Gate Replay

Status: `model_surrogate_gate_replay_completed_not_human_evidence`.

Phase92 consumes Phase91 model-surrogate labels as an operational replacement
for returned human labels and replays the Phase84 calibration, release-audit
and random-control gates.  This is a dry-run gate replay, not external human
evidence.

Gate statuses:

| gate                                                 | threshold                             |   observed | status     | evidence_scope                                                                                                                                                                                                                           |
|:-----------------------------------------------------|:--------------------------------------|-----------:|:-----------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| model_surrogate_calibration_support_available        | same_cell_supported >= 80             | 102        | PASS       | ctc_model_surrogate_gate_replay;phase91_labels_used_as_operational_replacement;not_external_human_audit;not_expert_microscopy_adjudication;not_CTC_ground_truth;not_completed_real_audit_positive_evidence;not_materials_or_DFT_evidence |
| model_surrogate_release_conservative_FTR_point       | conservative_fail_fraction <= 0.05    |   0.004    | PASS       | ctc_model_surrogate_gate_replay;phase91_labels_used_as_operational_replacement;not_external_human_audit;not_expert_microscopy_adjudication;not_CTC_ground_truth;not_completed_real_audit_positive_evidence;not_materials_or_DFT_evidence |
| model_surrogate_release_CP95_upper                   | CP95 upper conservative fail <= 0.10  |   0.018834 | PASS       | ctc_model_surrogate_gate_replay;phase91_labels_used_as_operational_replacement;not_external_human_audit;not_expert_microscopy_adjudication;not_CTC_ground_truth;not_completed_real_audit_positive_evidence;not_materials_or_DFT_evidence |
| random_same_budget_control_not_empty_under_surrogate | reported diagnostic; no positive gate |  46        | DIAGNOSTIC | ctc_model_surrogate_gate_replay;phase91_labels_used_as_operational_replacement;not_external_human_audit;not_expert_microscopy_adjudication;not_CTC_ground_truth;not_completed_real_audit_positive_evidence;not_materials_or_DFT_evidence |

Scope boundary:

- allowed: model-surrogate gate replay over frozen Phase84 packets;
- forbidden: external human audit success, expert microscopy adjudication,
  official CTC ground truth, completed real-audit PARC-A replication,
  materials evidence or DFT evidence;
- shorthand boundary: not external human evidence.

Evidence scope: `ctc_model_surrogate_gate_replay;phase91_labels_used_as_operational_replacement;not_external_human_audit;not_expert_microscopy_adjudication;not_CTC_ground_truth;not_completed_real_audit_positive_evidence;not_materials_or_DFT_evidence`.
