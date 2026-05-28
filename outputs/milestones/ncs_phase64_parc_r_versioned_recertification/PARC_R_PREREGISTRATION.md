# PARC-R Versioned Recertification Preregistration

Status: frozen before interpreting Phase64 outputs.

Question: when the public materials hull moves from t0 to current-MP t1, should
the old t0 release be inherited, or should the queue be recertified under the
new label version?

Inputs:

- Frozen K=300/500 materials queue union from Phase51.
- Frozen raw ALIGNN-FF score/rank.
- Current-MP t1 labels acquired in Phase49.

Protocol:

1. Split chemical systems into calibration/follow-up blocks for seeds 0-19.
2. Reveal only t1-stable positives in calibration blocks.
3. Construct null-superset block-max e-values from calibration non-observed rows.
4. Run the original SCS rule at alpha=0.1.
5. Evaluate held-out t1 follow-up blocks only after the recertification decision.

Scope:

- queue-limited recertification audit, not full-WBM recertification;
- not a t1 alpha certificate for the old t0 release;
- no new DFT and no prospective materials discovery.
