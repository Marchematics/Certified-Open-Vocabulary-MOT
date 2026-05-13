# Verified-Positive Precision Robustness

Let epsilon denote an upper bound on the false-tracklet rate inside the verified-positive set used for one-sided removal. The null-superset proof controls the nulls that remain in the calibrated null superset. If verified-positive removal has contamination epsilon, an operational additive sensitivity bound is

```text
actual FTR <= certified alpha + contamination_leakage,
contamination_leakage <= epsilon * N_removed / max(1, |R|).
```

A conservative paper-facing version can report this as a robustness margin rather than as the main theorem. In Audit2000, verified-positive rows = 95, observed false verified positives = 0. With zero observed false verified positives, the one-sided 95% binomial upper bound is approximately 0.0310. This bound is intentionally conservative and should be presented as sensitivity analysis, not as a replacement for the one-sided reliability assumption.
