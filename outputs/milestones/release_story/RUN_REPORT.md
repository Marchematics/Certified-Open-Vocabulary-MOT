# Release Story

This milestone reframes PARC-Track as auditable release-time certification for open-vocabulary visual AI under incomplete annotations. It is intentionally compact: it does not add more MOT grids, and it does not claim SOTA tracking, detection, or segmentation performance.

## Included Evidence

1. Non-tracking positive evidence from LVIS/LVVIS detection and mask-path scaffolds.
2. Release-policy value tables contrasting score/top-M style release with PARC release/refusal.
3. A qualitative teaser manifest for official matches, real official-unmatched objects, uncertain cases, false tracklets, high-score refusal candidates, and certified releases.
4. Near-boundary practice-benefit rows where a non-random learned materials source has raw top-K FTR in the 23.5%-32.6% range while PARC releases a smaller lower-FTR subset.
5. CTC audit-contamination sensitivity showing how release rate, release size, actual FTR, violation rate, and mass ratio change when the one-sided verified-positive assumption is deliberately violated.

## Scope

- Detection and mask rows are generality evidence, not SOTA benchmark claims.
- Visual examples are represented as public-safe manifests; raw images/videos are not packaged.
- Existing Audit2000 and reliability-fortress results remain the reliability foundation.

## Summary JSON

```json
{
  "status": "completed",
  "milestone": "outputs/milestones/release_story",
  "nontracking_positive": {
    "status": "completed",
    "table": "${PARC_TRACK_ROOT}/outputs/phase13_release_story/table_release_story_nontracking_positive.csv",
    "rows": 12
  },
  "release_policy_value": {
    "status": "completed",
    "table": "${PARC_TRACK_ROOT}/outputs/phase13_release_story/table_release_policy_value.csv",
    "figure_csv": "${PARC_TRACK_ROOT}/outputs/phase13_release_story/figure_release_policy_decision_curve.csv",
    "rows": 56
  },
  "teaser_manifest": {
    "status": "completed",
    "manifest": "${PARC_TRACK_ROOT}/outputs/phase13_release_story/figure_release_story_teaser_manifest.csv",
    "rows": 48
  },
  "copied_files": [
    "table_release_story_nontracking_positive.csv",
    "table_release_policy_value.csv",
    "figure_release_policy_decision_curve.csv",
    "figure_release_story_teaser_manifest.csv",
    "paper_diagnostics/table_near_boundary_release_value.csv",
    "paper_diagnostics/table_ctc_audit_contamination_sensitivity.csv"
  ],
  "raw_data_included": false,
  "model_weights_included": false,
  "package": "outputs/packages/release_story.tar.gz"
}
```
