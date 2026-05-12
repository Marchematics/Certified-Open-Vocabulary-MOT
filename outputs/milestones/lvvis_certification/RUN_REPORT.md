# LVVIS Certification Coverage Experiment

## Purpose
This milestone tests whether moving from the 20-video OVIS subset to the full LVVIS split inside the OVT-B unified annotation increases calibration coverage enough for PARC-Track certification.

## Dataset Scaffold
- Source family: LVVIS subset of the OVT-B unified box annotations.
- Scope: full LVVIS box / box-to-mask scaffold, not a full official mask benchmark.
- Videos: 1777
- Images: 39865
- Tracks: 11020
- Box annotations: 232378
- Categories: 1018

## Proposal Generation
- Backend: GroundingDINO
- Sharding: 4-way `video_stride=4`, one shard per GPU.
- Processed videos: 1777
- Frame detections: 53828
- Linked candidate paths: 12462
- Exported audit candidates: 200

## Certification Protocol
- Fixed global `M=150`
- alpha: `0.10`, `0.20`
- seeds: `0,1,2`
- release grid: `[2.0]`
- empty-block policy: `coverage_conditional`
- audit labels are templates only for this LVVIS run; conservative FTR treats unsupported unaudited releases as false.

## Outcome
PARC full releases 150/150 candidates for all alpha/seed rows. Coverage-conditional calibration has approximately 594-604 covered calibration videos, with effective `Emax` around 34-35, so the earlier OVIS finite-resolution refusal is resolved by increasing calibration videos.

See `table_lvvis_parc_summary.csv` and `lvvis_alpha_seed_m_matrix.csv` for exact rows.

## Public-Safety Notes
This milestone contains derived candidate CSVs, score/e-value diagnostics, configs, and hashes. It excludes raw frames, raw annotations, model weights, detector caches, and HF/GPU caches. Local paths are sanitized to `${PARC_TRACK_ROOT}` and `${PUBLIC_DATASETS_ROOT}`.
