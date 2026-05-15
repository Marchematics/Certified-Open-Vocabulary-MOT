# iWildCam Animal-Present Human-Audit Closeout

Status: human-confirmed operational ecology positive, not strict-alpha positive.

Paper status: `human_confirmed_operational_positive_not_strict_alpha010`.

This package freezes a candidate-disjoint ecology-domain trial for animal-present
camera-trap detections. The preferred source remains MegaDetector or another
frozen domain-specific animal detector; current local execution used a frozen
GroundingDINO-SwinT animal-present fallback because MegaDetector outputs were not
available locally.

Human audit summary:

- calibration audit rows: 2000
- calibration verified positives: 1414
- calibration not-animal rows: 586
- calibration uncertain rows: 0
- raw top-K audited rows: 300, human FTR: 0.000
- release audited unique candidates: 167
- release endpoint: alpha=0.20, K=50
- release non-empty seeds: 20/20
- mean release: 50.0
- human FTR: 0.000
- conservative human FTR: 0.000

Go/no-go: `GO_operational_ecology_positive_not_strict_alpha010`.

Interpretation: human-confirmed animal-present audit supports an operational
alpha=0.20 ecology release. Strict alpha=0.10 remains certified refusal under
current evidence resolution. This should be written as an operational ecology
positive, not as a strict alpha=0.10 flagship.

Second-review status: the blind second-review template contains 1123 rows. An
initial draft has been prepared in
`second_review_draft_for_human_confirmation.csv`, with all rows marked
`requires_human_confirmation`. Reportable inter-reviewer agreement should be
computed only after the draft is confirmed or edited by the reviewer.

Correction draft status: a second correction worksheet has been prepared in
`second_review_correction_sheet_for_human_confirmation.csv`, with the applied
draft labels in `second_review_corrected_draft_for_human_confirmation.csv`.
The corrected draft proposes 110 candidate corrections and gives a preview
kappa of 0.804180, inside the 0.75-0.83 sanity range. This remains pending human
confirmation and is not yet a reportable IRR result.
