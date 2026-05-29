# Phase69 Durability-Budgeted PARC

Status: `completed_durability_budgeted_release_card_diagnostic`.

Phase69 upgrades the Phase67c durability-risk prediction signal into
release-card decision artifacts. It reports cross-fitted risk scores,
risk-triage frontiers and a candidate-level durability-budget frontier.

Primary budgeted candidate-level support: `true`.
Risk-triage support: `true`.

Allowed claims:

- t0 public-label release-card features can triage which released materials
  candidates are more likely to lose durability after a reference update.
- A candidate-level durability budget can be audited with
  `alpha0 + beta_UCB <= 0.10`, using thresholds and beta estimates from
  chemical-system-held-out calibration folds.

Guardrails:

- no label-free deployment predictor;
- no prospective materials discovery;
- no DFT evidence;
- no full-release alpha certificate unless a future seed-level/full-release
  analysis satisfies the required gate;
- t0 public-label aggregate features are allowed only as release-card
  durability-audit features.
