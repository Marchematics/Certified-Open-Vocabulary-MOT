# Audit Budget Frontier Headline Package

Status: completed paper-facing transition package.

This package post-processes the completed simulated-audit frontier into lead numbers, policy-transition rows, and plot-ready source data. The headline transition criterion is `safe_release_rate >= 0.9` and `actual_FTR_mean <= alpha`. Rows that only meet the mean-operating criterion are explicitly secondary/boundary rows.

## Lead Transitions

- ctc_learned_strict_alpha010_K100: strict seed-stable transition at top-score budget 0.005; random baseline reached; efficiency 200.0x.
- ctc_learned_strict_alpha010_K300: strict seed-stable transition at top-score budget 0.005; random baseline reached; efficiency 200.0x.
- materials_alignn_exact_stable_alpha010_K300: mean-operating transition at top-score budget 0.005 with seed-level alpha-violation rate 0.45; report as boundary/secondary, not strict headline.
- materials_alignn_exact_stable_alpha010_K500: mean-operating transition at top-score budget 0.005 with seed-level alpha-violation rate 0.15; report as boundary/secondary, not strict headline.

## Claim Boundary

These are simulated audit-budget results over existing labels. They do not create new labels, do not modify A3, and do not support prospective materials-discovery wording. CGCNN K=100 is kept as a calibration/check row, not as a headline utility claim.
