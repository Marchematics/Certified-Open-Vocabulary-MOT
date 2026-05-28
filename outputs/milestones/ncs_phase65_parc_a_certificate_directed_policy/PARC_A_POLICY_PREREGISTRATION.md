# PARC-A Certificate-Directed Policy Preregistration

Status: frozen before interpreting Phase65 outputs.

Question: can PARC-A choose scarce one-sided verification targets using the
certificate objective rather than a generic score heuristic?

Frozen policies:

- `random`
- `score_targeted`
- `block_max_gain`
- `mass_gain`
- `diversity_mass_gain`

Primary target: CTC learned-hybrid K=100, alpha=0.1.

GO-strong: a certificate-directed policy reaches strict 20/20 safe release at
a smaller audit budget than score-targeted audit. GO-medium: a
certificate-directed policy matches score-targeted audit while random requires
orders of magnitude more budget.

No new human labels, no DFT, and no prospective materials discovery are used.
