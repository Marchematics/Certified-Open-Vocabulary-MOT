# Phase92 Protocol: CTC Model-Surrogate Gate Replay

Inputs:

- Phase91 model-surrogate replacement labels;
- Phase84 packet roles.

Procedure:

1. Treat `same_cell_supported` as one-sided positive support.
2. Treat `unsupported` and `uncertain` as conservative failures for release-audit summaries.
3. Report calibration support availability, release conservative failure bounds,
   and random same-budget diagnostic support.
4. Do not claim human evidence.
