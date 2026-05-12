# Phase-2h First Real Non-Empty Certification Milestone

Dataset: OVT-B scaffold
Requested videos: 1000
Processed videos with candidate paths: 996
Method: PARC full (`parc_track_gamma_tuned_uniform_scs`)
Alpha1: 0.10
Candidate budget M: 150
Release grid: [2.0]
Empty block policy: coverage_conditional
Score source: final_score_proxy

## Core Result

- Released tracks: 126
- Official supported released: 116
- Unsupported released: 10
- UTR: 0.079365
- Unsupported audit: 9 actually true, 0 actually false, 1 uncertain
- Audited FTR on supported + labeled released subset: 0.000000
- Conservative FTR if uncertain is false: 0.007937

## Theorem Diagnostics

- gamma: 0.172083
- gamma_star_eff: 0.172083
- p_min_effective: 0.002994
- Emax_effective: 21.144167
- max_observed_e: 21.144167
- released k: 126
- tau_k: 11.904762
- selected_e_min: 11.911400
- selected_e_mean: 19.678648
- selected_e_max: 21.144167
- self-consistency margin: 0.006638

Note: this milestone uses the post-recheck audit labels where uncertain high-score unmatched paths were revisited. The current self-consistency margin is 0.0066; earlier 0.0642 was from the pre-recheck label state.

## Local M-Sweep

The nearby candidate-budget sweep is saved in `table_m_sweep_parc_full_with_audit.csv`.

- Non-empty budgets: M = 75, 100, 125, 150, 175, 200
- Empty budget: M = 250, due to insufficient high-evidence mass
- Audited FTR on supported + labeled released subset remains 0.0 for all non-empty budgets in this sweep.
