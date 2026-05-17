# Materials Computational Follow-Up Trial Closeout

This milestone implements a quasi-prospective computational decision trial for materials candidates. PARC decides which candidates from a frozen model-ranked queue enter a computational follow-up queue under one-sided partial verification. Held-out public DFT labels in the follow-up partition are used only after the release/refusal decision to evaluate queue quality.

## Status

- Evidence status: `completed_quasi_prospective_public_DFT_label_trial`.
- No new human labels.
- No new DFT calculations.
- Not experimental synthesis and not true prospective discovery.
- Follow-up labels are public DFT labels revealed after the frozen release/refusal replay.

## Primary Headline

At `alpha=0.10, K=500`, ALIGNN-FF raw top-K admits 163.4 unstable candidates per split (32.7% raw FTR). PARC releases 90.8 candidates with 5.2 unstable candidates (4.8% FTR), preventing 158.3 unstable computational follow-ups per split.

At `alpha=0.10, K=5000`, ALIGNN-FF raw top-K admits 2,577.4 unstable candidates per split (51.5% raw FTR). PARC refuses the unsupported high-volume request, preventing 2,577.4 unstable computational follow-ups under the release/refusal interpretation.

## Interpretation

The trial supports a release-governance claim rather than a ranking-improvement claim: PARC identifies where to stop releasing candidates from a frozen scientific queue. The raw top-R matched prefix is reported separately to distinguish certified stopping from reranking.

## Protocol

`MATERIALS_COMPUTATIONAL_TRIAL_PROTOCOL.json` records the frozen model sources, budgets, alpha levels, block definition, partial-verification rule, and input hashes.

## Main Artifacts

- `table_materials_computational_trial_summary.csv`
- `table_materials_computational_trial_seed_results.csv`
- `table_materials_computational_trial_release_cards.csv`
- `figure_materials_computational_trial_main.csv`
- `figure_materials_computational_trial_main.pdf`
