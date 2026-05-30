# Phase84 Real-Audit PARC-A Replication

Status: `workflow_replication_packet_frozen_pending_external_labels`.

Phase84 freezes the packet needed to test whether real external one-sided
human calibration support can reproduce the PARC-A CTC active-verification
result.  It is not a completed audit result.

Primary packets:

- calibration audit rows: 150
- release audit rows: 250
- random same-budget control rows: 55

Important blocker:

The tracked Phase81 source rows do not contain a true raw-only top-K arm.
Phase84 therefore uses random same-budget control as the primary workflow
control and keeps raw-overlap rows as diagnostics only.

Evidence scope: `phase84_real_audit_parc_a_replication_protocol;external_labels_pending;workflow_replication_packet_frozen;not_completed_positive_evidence;not_new_CTC_ground_truth;not_materials_or_DFT_evidence`.
