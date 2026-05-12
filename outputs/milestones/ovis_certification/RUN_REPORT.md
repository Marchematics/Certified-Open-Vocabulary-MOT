# OVIS Certification v1

This milestone evaluates the OVIS subset contained in the local OVT-B-format annotation as an OVIS-in-OVT-B bbox certification scaffold. It is **not** a full official O-VIS mask benchmark.

## Dataset Scaffold

- Videos: 20
- Frames/images: 2284
- Tracks: 142
- Box annotations: 14379
- Categories: 5

## Candidate Generation

GroundingDINO proposal generation completed on all 20 OVIS videos. The candidate universe contains 272 linked paths and 846 detection nodes.

## Certification Outcome

PARC-Track with fixed global `M=150`, `alpha={0.10,0.20}`, and seeds `0/1/2` produced certified refusal in all six rows. This is expected from finite-resolution diagnostics: the OVIS subset has only 10 calibration videos and 6-7 covered calibration videos, yielding `Emax≈1.32-1.42`, below the required thresholds (`10` at alpha=0.10 and `5` at alpha=0.20).

The result should be reported as a small-subset finite-resolution boundary case, not as a tracker failure. See `table_ovis_certification_summary.csv` and `ovis_alpha_seed_m_matrix.csv`.

## Public-Safe Scope

This milestone excludes raw frames, raw annotations, model weights, detector caches, and montage images. `ovis_ovtb_ann.summary.json` is included, but the derived OVIS annotation JSON is not packaged.
