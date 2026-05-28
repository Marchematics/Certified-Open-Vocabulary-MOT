# Phase53 CHGNet/MACE Candidate-Level Audit

Status: `completed_candidate_level_CHGNet_MACE_score_audit_partial_false_case_explanation`

This milestone scores the frozen K=300/500 WBM queue candidates with real
CHGNet and MACE-MP single-point energies from local WBM structures. It upgrades
Phase51 from an ALIGNN/model-zoo explanation to a candidate-level universal
potential audit, while keeping the claim boundary narrow.

Important boundary: the CHGNet/MACE columns are raw energy-per-atom score
proxies, not model-consistent reference-hull e_above_hull values. Stable labels
are t0-prevalence quantile score-support proxies and must not be cited as DFT
ground truth.

Allowed claim: CHGNet/MACE candidate-level score audit compares PARC release,
raw top-K, matched raw top-R and raw-only extra-tail under a frozen t1 audit.
The queue-level score-support contrast favors PARC release over raw-only
extra-tail. The t1 false-case explanation gate is weaker: false PARC candidates
are not primarily explained by CHGNet/MACE disagreement or t1 near-hull status,
so this milestone should not be promoted as a completed false-case mechanism.

Forbidden claim: CHGNet/MACE proves prospective materials discovery or strict
t1 alpha control.
