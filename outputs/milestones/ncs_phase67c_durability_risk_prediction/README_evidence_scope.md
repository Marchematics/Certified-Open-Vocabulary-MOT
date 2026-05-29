# Phase67c Durability-Risk Prediction

Status: `completed_durability_risk_prediction_diagnostic`.

This experiment asks whether t0-time features can predict which t0-stable PARC
release candidates later become unstable under the current-MP t1 reference.

Primary prediction signal allowed: `true`.

Best model by primary-signal/AUC ordering:

- feature set: `chemical_system_exploration_only`
- mean group-CV ROC-AUC: `0.7659166126950671`
- mean average precision: `0.4027846197223421`
- top-20% enrichment vs base: `1.783820224719101`
- delta AUC vs candidate-margin baseline: `0.221621158818747`

Allowed claim:

- Durability risk can be audited as a t0-time prediction problem.

Guardrails:

- no release certificate;
- no prospective materials discovery;
- no DFT evidence;
- no t1 features used as predictors;
- report candidate-only, system-only and combined models together.
