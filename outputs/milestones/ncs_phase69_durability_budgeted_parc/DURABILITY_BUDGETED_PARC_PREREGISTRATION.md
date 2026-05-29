# Phase69 Durability-Budgeted PARC Preregistration

Status: registered after Phase67c leakage audit and before any DFT v2 stability
outcome table.

## Objective

Convert t0-only durability-risk scores into release-card triage and a
candidate-level durability-budget frontier.

## Frozen inputs

- Phase67c cross-fitted risk predictions.
- Phase67c feature provenance and leakage audit.
- Population: t0-stable PARC release rows at K=300/500.
- Label for evaluation: stable-to-unstable at current-MP t1.

## Grids

- alpha0 grid: `[0.01, 0.025, 0.05, 0.075]`.
- retain-fraction grid: `[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0]`.
- total target alpha: `0.1`.
- primary risk model: `system_margin_distribution`.

## Calibration discipline

For each held-out fold, risk thresholds and beta_UCB are computed from other
chemical-system folds. Held-out t1 labels are used only for evaluation.

## Success criteria

Candidate-level budget positive requires:

1. `alpha0 + beta_UCB <= 0.10` using the maximum calibration-fold beta_UCB;
2. observed retained t1 FTR <= 0.10 on held-out folds;
3. every held-out fold non-empty;
4. at least 80% of held-out folds individually t1-safe;
5. at least 10 retained candidate-level release rows in aggregate;
6. at least 5 retained candidate-level rows in every held-out fold.

This is still not a full PARC alpha certificate because the available Phase67c
population is restricted to t0-stable released rows and does not reconstruct
seed-level release sets.
