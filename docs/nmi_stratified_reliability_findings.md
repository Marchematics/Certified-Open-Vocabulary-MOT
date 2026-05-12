# NMI Stratified Reliability Findings

This note summarizes the paper-facing conclusions from the NMI stratified reliability analysis in
`outputs/milestones/nmi_generality_reliability_v1/`.

## Source Tables

- `table_tracking_stratified_reliability.csv`
- `table_lvis_detection_stratified_reliability.csv`
- `figure_support_vs_human_valid.csv`
- `figure_release_refusal_distribution.csv`

The tracking release/refusal breakdown uses
`rank_proxy_from_certified_release_count`, because the historical certification
runner did not persist exact released path identifiers for every matrix row.
Use it as a stratified diagnostic, not as an exact released-ID audit table.

## Tracking: OVT-B / TAO

The strongest finding is that incomplete annotations are not uniform noise.
They concentrate in visually difficult strata where official support is much
lower than human-verified validity.

Representative gaps, measured as `human_valid_rate - official_support_rate`:

| Dataset | Dimension | Stratum | Official Support | Human Valid | Gap |
|---|---|---:|---:|---:|---:|
| TAO | motion_speed | medium | 0.389 | 0.979 | 0.589 |
| TAO | object_size | small | 0.418 | 0.997 | 0.579 |
| TAO | track_length | medium | 0.450 | 0.977 | 0.527 |
| TAO | category_frequency | tail | 0.550 | 0.993 | 0.443 |
| OVT-B | track_length | short | 0.610 | 0.947 | 0.337 |
| OVT-B | object_size | small | 0.634 | 0.948 | 0.314 |

Paper framing:

> Incomplete annotations systematically penalize difficult visual regimes. In
> both OVT-B and TAO, small objects and short or moderate-length tracks have much
> lower official support than human-verified validity. This makes
> unmatched-as-false calibration especially unsafe in the very strata where
> open-vocabulary systems are most useful.

Occlusion is marked `attribute_unavailable` in the current OVT-B/TAO candidate
exports, so the main stratified tracking analysis should emphasize object size,
motion speed, track length, and category frequency.

## LVIS Detection Extension

The LVIS single-frame detection experiment shows the same partial-annotation
pathology outside tracking.

GroundingDINO has relatively high official support:

| Detector | Dimension | Stratum | Official Support |
|---|---|---:|---:|
| GroundingDINO | object_area | large | 0.802 |
| GroundingDINO | object_area | medium | 0.792 |
| GroundingDINO | object_area | small | 0.754 |
| GroundingDINO | category_frequency | rare | 0.694 |

OWLv2 shows a much harsher support/refusal boundary:

| Detector | Dimension | Stratum | Official Support | PARC Refusal Within Scope |
|---|---|---:|---:|---:|
| OWLv2 | object_area | large | 0.274 | 1.000 |
| OWLv2 | object_area | medium | 0.083 | 1.000 |
| OWLv2 | object_area | small | 0.023 | 1.000 |
| OWLv2 | category_frequency | frequent | 0.087 | 1.000 |

Paper framing:

> The detection-only LVIS extension demonstrates that PARC is not tied to
> temporal association. When the proposal source has high support
> (GroundingDINO), PARC certifies releases; when official support collapses
> (OWLv2 small and medium objects), PARC refuses release rather than converting
> unsupported detections into false calibration evidence.

## Figure Guidance

Use `figure_support_vs_human_valid.csv` for a faceted bar chart with two bars:
official support rate and human-valid rate. The `highlight_annotation_gap`
column marks strata with a gap of at least 0.20.

Use `figure_release_refusal_distribution.csv` for the release/refusal summary.
In captions, explicitly state that the release/refusal distribution is a
rank-proxy diagnostic derived from certified release counts.
