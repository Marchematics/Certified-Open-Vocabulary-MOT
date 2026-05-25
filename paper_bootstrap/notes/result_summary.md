# Result Summary

Last updated: 2026-05-24

## Primary Headline

### CTC active-audit strong positive

Source:

- `outputs/milestones/audit_budget_frontier_strong_positive/table_strong_positive_gate_audit.csv`

Lead numbers:

- Target row: `ctc_learned_strict_alpha010_K100`
- Top-score audit budget: 0.005
- Safe seeds: 20/20
- Total releases: 2000
- False releases: 0
- Matched-budget random audit: 0/20 nonempty seeds
- Full random audit transition: 1.0 budget
- Budget ratio: 200x

Claim scope:

- Completed simulated-audit strong positive for CTC only.
- No new labels.
- No A3 evidence.

## Clean-Acceptance Support

### T1 empirical baseline frontier

Source:

- `outputs/milestones/t1_clean_acceptance_package/`

Lead numbers:

- 11 empirical method families.
- ALIGNN K=300: raw top-K FTR 0.253; PARC FTR 0.087; raw top-R matched FTR 0.087; 64.25 unstable follow-ups prevented.
- ALIGNN K=500: raw top-K FTR 0.327; PARC FTR 0.048; raw top-R matched FTR 0.048; 158.30 unstable follow-ups prevented.
- CGCNN K=500 baseline frontier: raw top-K FTR 0.326; post-filter e-value FTR 0.163; PARC/raw top-R FTR 0.032; e-BH releases no candidates.
- 5/5 materials independent/prospective validation routes are not positive evidence.

Claim scope:

- Strong empirical baseline frontier.
- Retrospective public-label materials release-policy evidence.
- Not prospective materials discovery.

## Boundary Support

### Refusal attribution

Source:

- `outputs/milestones/nmi_reviewer_p0_hardening/table_refusal_feasibility_attribution.csv`

Use:

- Explain refusal as evidence-mass or finite-resolution gate behavior.
- Do not claim new positive release evidence.

### Human audit uncertainty

Source:

- `outputs/milestones/nmi_reviewer_p0_hardening/table_human_audit_uncertainty_intervals.csv`

Use:

- Report zero-false audit outcomes with interval uncertainty.
- Avoid universal zero-risk language.

### Release-governance synthesis

Source:

- `outputs/milestones/release_governance_problem_paradigm/`

Use:

- Start drafting from `release_governance_abstract_v2.md` and `release_governance_maintext_skeleton.md`.
