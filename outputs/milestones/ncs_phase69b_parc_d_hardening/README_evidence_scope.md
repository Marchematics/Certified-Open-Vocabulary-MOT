# Phase69b PARC-D Hardening

Status: `completed_PARC_D_hardening`.

Phase69b audits the Phase69 durability-budgeted candidate-level result for
reviewer-facing claim boundaries.

Primary locked row:

- risk model: `system_margin_distribution`
- K: `300`
- alpha0: `0.01`
- retained fraction: `0.4`
- release size: `89`
- 95% alpha0 + beta_UCB: `0.09875270035675841`
- post-filter self-consistency pass: `false`

Interpretation:

The Phase69 row remains a constructive release-card risk-triage result. It does
not become a full current-MP alpha certificate because the retained post-filter
subset does not pass PARC self-consistency at `alpha0=0.01` and seed-level
release reconstruction is unavailable.

Allowed claim:

`t0` public-label chemical-system margin-landscape features can support a
durability-budgeted candidate-level risk-triage subset and route high-risk rows
to recertification.

Forbidden claims:

- no full current-MP alpha certificate;
- no label-free deployment predictor;
- no prospective materials discovery;
- no DFT validation evidence;
- no claim that the retained post-filter subset inherits PARC self-consistency.
