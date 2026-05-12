# IJCV Phase-4 Sprint v1

Frozen on 2026-05-09.

This milestone contains paper-facing Phase-4 experiment assets for the IJCV sprint. It intentionally excludes raw videos, raw annotations, model weights, HF caches, and large per-candidate e-value caches.

## Contents

- `tables/table_prop5_validation.csv`: 8-row Prop. 5 high-evidence mass validation.
- `tables/table_score_ablation_summary.csv`: 2 datasets x 2 alpha x 4 score variants.
- `tables/table_alpha_frontier_meanstd.csv`: alpha frontier for GroundingDINO and OWLv2.
- `tables/table_ncalib_sensitivity.csv`: calibration-size sensitivity with effective gamma tuning.
- `metrics/table_motmetrics.csv`: first-pass motmetrics IDF1/MOTA scaffold.
- `audit/owlv2_top150_mini_audit_candidates.csv`: OWLv2 top-150 mini-audit sample, 50 per dataset.
- `audit/second_rater_sample.csv`: 100-row audit reliability sample.
- `diagnostics/failure_case_manifest.csv`: false/uncertain/suspicious release case manifest.
- `docs/reference_sanity_phase4.md`: reference sanity notes.
- `code/phase4.py`: exact Phase-4 runner snapshot.
- `MANIFEST_SHA256.txt`: checksums for all milestone files.

## Key Results

- Prop. 5 correctly predicts non-empty vs empty outcomes for all 8 paper-facing generator/dataset/alpha rows.
- Score ablation shows temporal/association/weighted score variants improve or stabilize release power relative to detector-only in the current scaffold.
- OVT-B GroundingDINO alpha frontier is non-empty for all seeds at alpha >= 0.10; TAO GroundingDINO becomes non-empty from alpha = 0.15 in this scaffold.
- OWLv2 remains a failure-analysis generator in this revision.
- MOT metrics are a first-pass scaffold: IDF1/MOTA are reported via `motmetrics`; HOTA remains marked as requiring TrackEval.
- TrackEval has been cloned to `<PARC_ROOT>/third_party/TrackEval` for the follow-up HOTA run; this milestone does not yet report HOTA.

## Verification

The final test run completed with:

```text
43 passed, 1 warning
```

See `manifest.json` for command history and caveats.
