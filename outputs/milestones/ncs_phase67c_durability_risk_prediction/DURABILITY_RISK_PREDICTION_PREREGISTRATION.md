# Phase67c Durability-Risk Prediction Preregistration

Status: executed as a t0-feature prediction diagnostic on frozen Phase51
candidate rows. This is not a release certificate, prospective discovery or DFT
evidence.

## Frozen inputs

- Candidate source: Phase51 t1 candidate explanation table.
- Input hash: `2f493f4e5551a963d5f3936774cc994769f755a378a1659aff1ff81a94adb1f0`.
- Population: PARC released candidates at K=300/500 that were stable at t0.
- Label: `stable_to_unstable` at the current-MP t1 reference.
- Primary split: GroupKFold by chemical system.

## Feature families

- Candidate margin only.
- Candidate t0 score/release metadata only.
- Chemical-system exploration/crowding proxies computed from t0 rows only.
- Candidate plus system features.

No t1 labels, t1 near-hull flags, drift labels or post-update features are used
as predictors.
