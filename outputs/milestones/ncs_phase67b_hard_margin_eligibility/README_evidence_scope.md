# Phase67b Hard-Margin Eligibility

Status: `completed_hard_margin_eligibility_diagnostic`.

Phase67b is a stricter follow-up to Phase67. It permits release only for
candidates whose frozen t0 hull margin satisfies `margin >= m`, ranks eligible
candidates by t0 margin, and evaluates current-MP t1 survival after release.

Headline positive hard-margin t1 survival allowed: `false`.

Best row by primary-success/safe/nonempty/release-size ordering:

- margin m eV/atom: `0.2`
- K: `20`
- support mode: `margin_10pct_support`
- non-empty seeds: `19/20`
- t1 survival safe seeds: `9/20`
- mean release size: `17.100`
- mean t1 FTR if non-empty: `0.14106858054226476`

Guardrails:

- no prospective materials discovery;
- no independent DFT evidence;
- t0 margin is used as eligibility metadata;
- no post-hoc K or margin selection as a headline unless the full grid is
  reported.
