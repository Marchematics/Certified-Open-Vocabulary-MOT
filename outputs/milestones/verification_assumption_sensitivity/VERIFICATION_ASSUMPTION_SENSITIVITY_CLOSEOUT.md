# Verified-Positive Contamination Sensitivity

Status: completed assumption-boundary diagnostic.

This experiment deliberately violates the one-sided verified-positive reliability assumption by injecting false calibration candidates into the observed-positive set before null-superset removal. Nonzero-contamination rows are not formal PARC guarantees; they are stress tests that show when release should be interpreted as requiring refusal, audit, or stronger verification.

- Target rows: 5
- Seed-level rows: 1200
- Contamination rates: 0.0, 0.005, 0.01, 0.02, 0.05, 0.1
- Contamination modes: adversarial, random
- First alpha-violation diagnostic row: materials_alignn_exact_stable_alpha010_K300 / adversarial at epsilon=0.005

## Claim Boundary

- Allowed: verification-assumption boundary diagnostic; shows how release/refusal changes under controlled assumption violation.
- Forbidden: robustness theorem under contaminated positives; prospective discovery; completed external audit.
