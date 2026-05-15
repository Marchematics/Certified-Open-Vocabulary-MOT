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

Second-review completion: the corrected worksheet was confirmed by human review
and frozen in `second_review_human_confirmed_labels.csv`. The reportable
agreement table is `table_iwildcam_second_review_agreement_summary.csv`.
Overall label agreement is 0.902048 with Cohen kappa 0.804180
(bootstrap 95% CI: 0.768494-0.837898). The release-audit subset remains
167/167 animal-present under second review; disagreements are confined to
calibration-review candidates and are listed in
`table_iwildcam_second_review_disagreement_cases.csv`.
