# Phase62 Full-Calibration CHGNet/MACE E-Values

Status: `completed_full_calibration_sources_no_headline_signal`.

This milestone fixes the main Phase61 source-availability blocker: CHGNet and
MACE-MP are no longer used only as queue-level rank proxies. They are converted
to auxiliary e-values using a frozen WBM calibration denominator, with target
overlap excluded before block maxima are computed.

The result remains deliberately scoped. It is a full-calibration auxiliary
e-value audit over the available WBM calibration subset; it is not DFT evidence,
not a current-MP t1 alpha certificate, and not a prospective materials discovery claim.
Headline status depends on the gate table, especially whether the full-calibration
fusion gives a nontrivial release and improves t1 FTR over the original PARC
release by at least 0.05.
