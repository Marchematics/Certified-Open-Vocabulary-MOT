# LVVIS SAM Mask-Path Certification v1

## Purpose
This milestone upgrades the LVVIS box-path coverage experiment into a SAM-derived mask-path benchmark. The local LVVIS/OVT-B unified annotation contains boxes but no official segmentation masks, so masks are generated from each candidate box with SAM box prompts and evaluated through mask-IoU conflicts. This is a full candidate-node mask materialization over the LVVIS scaffold, not a claim of official LVVIS ground-truth mask evaluation.

## Mask Materialization
- SAM checkpoint: `sam_vit_b_01ec64.pth`
- Model type: `vit_b`
- Candidate node rows: 53828
- SAM mask rows: 53828
- Unique paths: 12462
- Unique images: 14083
- Missing node rows: 0
- Failed mask rows: 0
- Execution: 4-way GPU sharding by image.

## Certification Analysis
- Fixed global `M=150`
- alpha: `0.10`, `0.20`
- seeds: `0,1,2`
- mask IoU thresholds: `0.3`, `0.5`, `0.7`
- conflict-aware SCS uses the same block e-values as LVVIS certification, then enforces mask path conflicts by greedy disjoint selection among eligible high-evidence paths.

## Result
All alpha/seed/threshold rows release 150/150 candidates. At threshold 0.3 the top graph contains about 18 conflict edges on average, yet mask-disjoint SCS still finds a full release. Mean UTR/conservative FTR remains 0.0111 because unsupported released paths are few and unaudited unsupported paths are conservatively counted as false.

See `table_lvvis_mask_certification.csv` and `table_lvvis_mask_summary.csv`.

## Public-Safety Notes
This package contains derived SAM RLE masks for candidate nodes, certification tables, configs, scripts, logs, and hashes. It excludes raw frames, raw annotations, model weights, detector cache, and HF/GPU caches. Paths are sanitized to `${PARC_TRACK_ROOT}` and `${PUBLIC_DATASETS_ROOT}`.
