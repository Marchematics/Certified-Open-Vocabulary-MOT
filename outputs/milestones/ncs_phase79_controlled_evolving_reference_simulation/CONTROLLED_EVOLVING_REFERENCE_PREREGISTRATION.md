# Phase79 Controlled Evolving-Reference Generality Simulation

Status: `completed_controlled_generality_simulation`.

## Objective

Test whether the Phase67c materials durability-risk result has a portable
mechanistic signature. We simulate two evolving-reference regimes:

1. `candidate_driven`: reference flips are driven by candidate-level fragility.
2. `neighborhood_driven`: reference flips are driven by system-level
   reference-neighborhood crowding/activity.

The expected outcome is not that system features always win. The expected
outcome is mechanism recovery: candidate features win in the candidate-driven
regime, while system features win and candidate features are near random in the
neighborhood-driven regime.

## Frozen Parameters

- random seed: `20260530`;
- replicates: `20`;
- systems per replicate: `180`;
- mean candidates per system: `6`;
- CV: `GroupKFold_by_system_id`, `5` folds;
- models: logistic regression with standardization and balanced class weights.

## GO Criterion

GO requires both mechanism-signature checks:

`GO` requires both:

- candidate-driven signature: candidate AUC >= 0.70 and candidate AUC exceeds
  system AUC by at least 0.10;
- neighborhood-driven signature: system AUC >= 0.70, candidate AUC <= 0.60 and
  system AUC exceeds candidate AUC by at least 0.15.

## Scope

This is a controlled mechanism demonstration. It is not a new empirical domain,
not a release certificate, not DFT evidence and not prospective materials
discovery.
