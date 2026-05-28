# Phase61 PARC-M Multi-Evidence Fusion

Status: `empirical_medium_signal_not_claim_ready`

PARC-M tests fixed mixtures of original PARC e-values with frozen
ALIGNN/CHGNet/MACE score-derived e-proxies. The empirical signal is better than
the simple Phase60 support gate: the best proxy-fusion rows reduce current-MP
t1 FTR by about 0.03-0.04 while keeping nontrivial release sizes.

However, this is not yet a theorem-grade PARC-M result. CHGNet and MACE scores
are available here only for the frozen queue, not for the full null-superset
calibration blocks. Therefore the e-value mixture theorem cannot be invoked for
the auxiliary sources in this milestone.

Allowed claim: PARC-M has a medium empirical feasibility signal that justifies a
full-calibration implementation if the project wants a method upgrade.

Forbidden claims:

- no theorem-grade multi-evidence e-value certificate;
- no t1 alpha control;
- no DFT evidence;
- no prospective materials discovery;
- no claim that CHGNet/MACE queue score proxies are calibrated null-superset
  e-values.
