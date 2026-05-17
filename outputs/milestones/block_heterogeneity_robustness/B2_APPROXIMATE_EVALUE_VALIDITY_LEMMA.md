# B2 Approximate E-Value Validity Lemma

This is a supplement-facing note, not a main-text edit.

Suppose the constructed false-candidate e-values satisfy
`E[E_p] <= 1 + eta` for every false candidate `p`, rather than exact
`E[E_p] <= 1`. If the selected set `R` satisfies the same PARC
self-consistency condition, then

```text
E[ |R ∩ H0| / (|R| ∨ 1) ] <= alpha (1 + eta).
```

Proof sketch. For every false candidate `p`, self-consistency gives

```text
1[p in R] / (|R| ∨ 1) <= alpha E_p / K.
```

Summing over false candidates and taking expectations gives

```text
E[FDP(R)] <= (alpha / K) sum_{p in H0} E[E_p]
          <= alpha (1 + eta) |H0| / K
          <= alpha (1 + eta).
```

Thus block-heterogeneity diagnostics can be read as practical checks for
e-value inflation. If block comparability is poor, size-stratified,
size-matched, or conservative calibration variants are the fallback.
