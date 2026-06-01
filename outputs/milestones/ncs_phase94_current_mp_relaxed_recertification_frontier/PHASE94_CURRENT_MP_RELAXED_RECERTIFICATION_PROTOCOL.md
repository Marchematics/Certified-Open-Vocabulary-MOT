# Phase94 Protocol: Current-MP Relaxed Recertification Frontier

Frozen grid:

- K: `[25, 50, 75, 100, 150, 200]`;
- alpha: `[0.1, 0.15, 0.2]`;
- audit budgets: `[0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 1.0]`;
- policies: `['random_t1_audit', 'score_targeted_t1_audit', 'low_risk_score_targeted_t1_audit', 'blockmax_gain_t1_audit']`;
- support modes: `['t1_10pct_support', 't1_full_calibration_block_support']`.

Procedure:

1. Use the Phase75 queue-limited current-MP t1 public-label recertification
   emulation machinery.
2. Use t1 labels only as calibration-side one-sided positives.
3. Recompute the null-superset denominator and e-values after audit.
4. Evaluate held-out t1 labels only after release.
5. Report the full grid. Do not select a row by hiding failures.

Forbidden claims:

- independent DFT validation;
- prospective materials discovery;
- strict alpha=0.10 current-MP certificate unless the strict gate passes;
- physical ground truth.
