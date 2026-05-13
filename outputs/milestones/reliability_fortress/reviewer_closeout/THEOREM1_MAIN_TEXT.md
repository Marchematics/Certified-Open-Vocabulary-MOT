# Theorem 1 Main-Text Statement Draft

**Theorem 1 (Audit-aware null-superset certified release).** Fix a candidate universe, a score rule, a Mondrian cell rule, a release grid, and an SCS selector before observing calibration/test labels. Assume:

1. **Video-level exchangeability.** Calibration and test videos are exchangeable within each reported protocol split.
2. **One-sided verified-positive reliability.** Any path removed from the null superset by the audit protocol is truly non-null, except for the separately reported robustness sensitivity epsilon.
3. **Frozen universe and selection rule.** Candidate generation, scoring, calibration, gamma selection, and SCS selection do not use test labels except through the released-set audit diagnostics reported after selection.

Then the PARC release set R satisfies the target false-tracklet-rate control for the calibrated null-superset target,

```text
E[ |R ∩ H0| / max(1, |R|) ] <= alpha,
```

where H0 is the true false-tracklet null set under the one-sided audit reliability assumption. Empty releases are valid certified refusals. The full proof remains in the supplement; the main text should include this full statement and a proof sketch.
