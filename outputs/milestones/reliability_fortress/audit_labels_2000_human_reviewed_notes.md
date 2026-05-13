# Human-reviewed 2000-row audit v1

The 2000-row audit has completed human review. Forty rows remain `uncertain`; all other rows are confirmed as either `actually_true` or `actually_false`. Rows upgraded from `uncertain` to `actually_true` are not marked calibration-grade verified positives unless they independently satisfy the stricter verified-positive rule. The remaining 40 uncertain rows are selected deterministically from the previous uncertain pool: existing-gold uncertain rows, hard/tiny-category rows, then the lowest-score remaining rows.
