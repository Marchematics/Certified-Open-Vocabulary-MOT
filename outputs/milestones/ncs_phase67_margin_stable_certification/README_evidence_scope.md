# Phase67 Margin-Stable Certification

Status: `completed_margin_stable_certification_diagnostic`.

Phase67 changes the release-card target from fragile t0 stability
`e_above_hull,t0 <= 0` to robust t0 margin-stability
`e_above_hull,t0 <= -m`, ranks by t0 margin, and evaluates whether the released
set survives the current-MP t1 hull.

Headline positive margin-stable t1 survival allowed: `false`.

Best row by primary-success/safe/nonempty/release-size ordering:

- margin m eV/atom: `0.2`
- K: `20`
- support mode: `margin_10pct_support`
- non-empty seeds: `19/20`
- t1 survival safe seeds: `9/20`
- mean release size: `17.100`
- mean t1 FTR if non-empty: `0.14106858054226476`

Allowed claim:

- Margin-stable release cards test whether t0 hull margin buffers current-MP
  drift and can identify a smaller release frontier.

Guardrails:

- no prospective materials discovery;
- no independent DFT evidence;
- no claim that t0 margin labels are hidden from selection;
- no post-hoc K or margin selection as a headline unless the full grid is
  reported.
