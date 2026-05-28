# Phase66 Certificate Durability Frontier

Status: `completed_certificate_durability_frontier`.

This milestone makes version dependence explicit.  It reports a deterministic
version-shift accounting identity, a margin-buffer durability design diagnostic,
and a full predeclared K-sweep for queue-limited current-MP PARC-R
recertification.

Headline positive current-MP recertification allowed: `false`.

Best observed K-sweep row by safe/non-empty seeds:

- K: `10`
- support mode: `t1_10pct_support`
- non-empty seeds: `13/20`
- safe seeds: `0/20`
- mean release size: `5.950`
- mean t1 FTR if non-empty: `0.30192307692307696`

Allowed claims:

- Version-shift accounting decomposes t1 burden into t0 error plus
  stable-to-unstable drift minus unstable-to-stable correction.
- Historical margin/drift tails provide a durability design diagnostic.
- The predeclared K-sweep tests whether current-MP recertification recovers a
  smaller release after high-K refusal.

Forbidden claims:

- no prospective materials discovery;
- no DFT evidence;
- no t1 alpha certificate for the old t0 release;
- no post-hoc K selection using observed t1 FTR;
- no future-drift guarantee from historical drift tails.
