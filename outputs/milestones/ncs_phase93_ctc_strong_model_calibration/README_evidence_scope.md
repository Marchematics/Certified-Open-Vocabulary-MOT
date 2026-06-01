# Phase93 CTC Strong-Model Calibration

Status: `retrospective_surrogate_calibration_passed_against_existing_human_labels`.

Phase93 joins the frozen Phase81 CTC audit packet, Phase91 surrogate labels and
the existing CTC strict human-audit labels. It is a retrospective calibration
of the model surrogate, not a new external human audit.

Key dry-run facts:

- joined rows: `600`;
- high-confidence surrogate positives: `411`;
- high-confidence surrogate false positives versus existing human labels:
  `0`;
- CP95 upper false-positive fraction for high-confidence positives:
  `0.007262`.

Evidence scope: `ctc_strong_model_calibration_against_existing_human_labels;retrospective_internal_calibration;not_external_human_audit;not_CTC_ground_truth;not_completed_real_audit_positive_evidence;not_materials_or_DFT_evidence`.
