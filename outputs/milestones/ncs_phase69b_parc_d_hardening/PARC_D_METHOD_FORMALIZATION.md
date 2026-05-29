# PARC-D Method Formalization

## Algorithm: durability-budgeted release-card triage

1. Run PARC at reference version \(t_0\) with a base risk budget \(\alpha_0\).
2. Compute durability-risk scores from \(t_0\)-available release-card metadata.
   In this experiment those features are public-label chemical-system margin
   landscape summaries, so the module is not label-free.
3. Use held-out chemical-system folds to calibrate an upper bound
   \(\beta_{\mathrm{UCB}}\) for stable-to-unstable drift on retained rows.
4. A candidate-level operating row is budget-feasible when
   \(\alpha_0+\beta_{\mathrm{UCB}}\le \alpha\).
5. If the retained set also satisfies PARC self-consistency, it can be treated
   as a candidate-level durability-budget certificate. Otherwise it is a
   risk-triage subset and high-risk rows are routed to recertification.

## Proposition: durability-budget accounting

Let \(R_D\) be a retained release-card subset. If

\[
\mathbb E[\mathrm{FTR}_{t_0}(R_D)]\le \alpha_0
\]

and a drift-risk calibration gives

\[
\mathbb E[\delta^+_{R_D}]\le \beta,
\]

then version-shift accounting implies

\[
\mathbb E[\mathrm{FTR}_{t_1}(R_D)]\le \alpha_0+\beta.
\]

If \(\alpha_0+\beta\le\alpha\), the inherited current-reference burden is
budgeted at level \(\alpha\), subject to the validity of the drift calibration.

## Scope

The empirical Phase69/69b row is a historical current-MP durability audit using
cross-fitted t0 public-label release-card features. It is not a prospective
future-update guarantee unless the drift calibration transports to that future
reference update. In the current artifact, the post-filter retained row fails
PARC self-consistency and is therefore reported as risk-triage rather than a
full alpha certificate.
