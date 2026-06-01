# Phase91 CTC Strong-Model Surrogate Annotation

Status: `strong_model_surrogate_annotations_completed_not_human_evidence`.

Phase91 annotates the frozen Phase84 CTC blind-audit packets with a local
image-based surrogate model.  It reads adjacent CTC frames and SEG masks,
computes crop/template/geometry evidence, and emits human-label-compatible
CSV files that can operationally replace manual labels for downstream dry
runs.

Scope boundary:

- allowed: strong-model surrogate annotations and replacement-label CSVs;
- forbidden: external human audit success, expert microscopy adjudication,
  official CTC ground truth, completed real-audit PARC-A replication, or
  materials/DFT evidence;
- shorthand boundary: not external human evidence.

All `600` packet rows have image-pair availability status recorded.

Evidence scope: `ctc_strong_model_annotation;image_template_segmentation_surrogate;model_surrogate_labels_only;replaces_manual_review_operationally_not_evidentially;not_external_human_audit;not_expert_microscopy_adjudication;not_CTC_ground_truth;not_completed_real_audit_positive_evidence;not_materials_or_DFT_evidence`.
