# Main Experiment Protocol

This document fixes the paper-facing protocol so future reruns and appendix extensions do not drift.

## Main Results

- Datasets: `OVT-B`, `TAO`, `BURST`.
- Candidate budget: `M=150`.
- Certified risk level: `alpha=0.10`.
- Seeds: `0`, `1`, `2`.
- Main proposal sources: GroundingDINO detector-only, GroundingDINO + tracker when available, OWLv2, and OWL-ViT v1.

The main paper tables use only the fixed protocol above. Sensitivity grids are appendix-only.

## Appendix Sensitivity

- Candidate budgets: `M in {50, 100, 150, 300}`.
- Risk levels: `alpha in {0.05, 0.10, 0.20}`.
- Seeds: `0, 1, 2, 3, 4`.
- Published tracker rows are appendix/provenance rows unless official prediction provenance is complete.

## Output Schema

Every dataset × generator × alpha × M × seed row uses the same field names:

```text
dataset
generator
alpha
certified_risk_level_alpha
M
seed
raw_topM_released
raw_topM_audited_false_rate
raw_topM_unsupported_rate
parc_released
parc_UTR
parc_audited_FTR
parc_conservative_FTR
empirical_audited_FTR
conservative_label_uncertainty_FTR
mass_ratio
best_mass_ratio
self_consistency_margin
required_emax
max_observed_e
mean_observed_e
selected_e_min
selected_e_mean
selected_e_max
release_feasible
empty_reason
safe_refusal_reason
HOTA_or_proxy
IDF1_or_proxy
MOTA_or_proxy
runtime_sec
```

The naming separates `certified_risk_level_alpha` from empirical audit diagnostics. In particular, `empirical_audited_FTR` and `conservative_label_uncertainty_FTR` are audit-derived diagnostics, not the theorem statement itself.

## Paper-Facing Outputs

Cleaned paper-facing outputs live under:

```text
outputs/milestones/reliability_fortress/paper_tables/
```

The raw provenance tables remain frozen elsewhere. Paper-facing tables omit local temporary paths and internal status tags.
