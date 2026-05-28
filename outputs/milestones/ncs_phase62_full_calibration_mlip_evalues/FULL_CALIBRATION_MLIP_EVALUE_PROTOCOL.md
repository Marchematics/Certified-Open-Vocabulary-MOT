# Phase62 Full-Calibration CHGNet/MACE E-Value Protocol

Objective: replace the Phase61 queue-only CHGNet/MACE rank proxies with
auxiliary e-values computed from a frozen WBM calibration denominator.

Calibration denominator: the A3-v3 WBM one-per-composition-family calibration
subset. Before computing block maxima, any target queue candidate that overlaps
this denominator is excluded to avoid calibration-target leakage.

Scores:

- CHGNet: `-chgnet_energy_per_atom` from the frozen CHGNet calibration table.
- MACE-MP: `-mace_energy_per_atom` scored locally from the same WBM structures.

Observed positives: top-score 10% of DFT-stable calibration rows for each
source. All other calibration rows remain in the null-superset block-max
denominator. Candidate e-values use the same gamma rule as PARC.

Allowed claim: CHGNet/MACE can now be audited as full-calibration auxiliary
e-value sources over the frozen WBM calibration subset.

Forbidden claims: no t1 alpha control, no DFT evidence, no prospective
materials discovery, and no claim that this alone proves a new NCS headline.
