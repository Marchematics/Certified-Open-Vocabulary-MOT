# Phase74 Risk-Gated PARC-R Recertification

Status: `completed_risk_gated_recertification_no_go`.

Phase74 moves the Phase69/69b durability-risk rule upstream. The low-risk gate
is applied before PARC-R recertification; the calibration null superset,
e-values and SCS threshold are rebuilt inside the filtered universe.

Primary prior row:

- risk model: `system_margin_distribution`
- K original: `300`
- K effective after risk gate: `128`
- retain fraction: `0.4`
- support mode: `t1_10pct_support`
- non-empty seeds: `0/20`
- any self-consistent release: `false`

Full-grid constructive positive: `false`.

Interpretation:

The constructive rescue route does not pass.  Once the risk gate is moved
upstream and the null-superset denominator is recomputed, the low-risk universe
does not produce a non-empty self-consistent current-MP release on the
predeclared grid. PARC-D therefore remains a release-card risk-triage module,
not a current-MP alpha certificate.

Guardrails:

- risk gate is pre-PARC and uses no held-out t1 labels for thresholding;
- denominator and e-values are recomputed after filtering;
- no DFT evidence;
- no prospective materials discovery;
- no full current-MP alpha certificate.
