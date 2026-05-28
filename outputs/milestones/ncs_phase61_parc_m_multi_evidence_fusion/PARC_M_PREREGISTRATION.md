# PARC-M Multi-Evidence Fusion Preregistration

Objective: test whether fixed multi-evidence fusion of original PARC evidence,
ALIGNN score evidence, CHGNet score evidence and MACE score evidence can improve
the materials current-MP t1 release frontier.

Frozen fusion rules:

- `PARC-M-avg`: equal mixture of original PARC, ALIGNN, CHGNet and MACE e-proxies.
- `PARC-M-raw-heavy`: 0.50 original PARC + 0.25 CHGNet + 0.25 MACE.
- `PARC-M-maxBonf`: max evidence divided by four.
- `PARC-M-consensus`: same fixed original/CHGNet/MACE mixture as raw-heavy.
- `PARC-M-aux-only`: ALIGNN + CHGNet + MACE e-proxies only.

Headline gates:

- GO-strong: t1 FTR improves over original PARC by at least 0.05 with a
  nontrivial release.
- GO-medium: t1 FTR improves by at least 0.03 with a nontrivial release.
- Claim-ready theorem gate: every component evidence source must be constructed
  from full null-superset calibration block maxima. This milestone does not meet
  that gate for CHGNet/MACE.
