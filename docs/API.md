# PARC-Track API

PARC-Track consumes candidate tracklets from any detector/tracker and emits calibrated e-values, self-consistent releases, and audit exports.

## Required Candidate Universe Columns

`candidate_universe.csv` should contain at least:

```text
dataset,video_id,path_id,split,query,category_id,frame_start,frame_end,path_length,candidate_rank,score,is_matched_to_gt,matched_gt_id,matched_iou,cell_id
```

Additional score components are welcome, for example `score_obj`, `score_sem`, `score_temp`, and `score_assoc`.

## Candidate Nodes

`candidate_nodes.csv` describes the frame-level boxes or masks for each path:

```text
dataset,video_id,path_id,frame_id,x,y,w,h,score,node_id
```

For mask-path experiments, include mask identifiers or encoded mask references and conflict metrics.

## Audit Labels

`audit_labels.csv` uses:

```text
dataset,video_id,path_id,audit_label,verified_positive_for_calibration,audit_status
```

Valid labels are `actually_true`, `actually_false`, and `uncertain`. `uncertain` rows must never be used as verified positives.

## Certification Flow

1. Assign calibration/test splits.
2. Remove only verified positives from the null-superset.
3. Compute video-block p-values/e-values.
4. Select a self-consistent release with SCS-Greedy.
5. Export UTR, audited FTR, conservative FTR, mass ratio, and empty-reason diagnostics.
