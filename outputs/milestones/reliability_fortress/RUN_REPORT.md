# Reliability Fortress

Reliability-focused bundle with human-reviewed 2000-row audit and explicit assumption-boundary diagnostics.

- Audit rows: 2000 human-reviewed.
- Audit labels: 1927 actually true, 33 actually false, 40 uncertain.
- Verified positives: 95.
- Second review: completed human-confirmed closeout. The hard-case Boundary-500 challenge has 25 disagreements out of 500 rows (Cohen's kappa = 0.8325676092). The full Audit2000 reannotation closeout has 25 disagreements out of 2000 rows (Cohen's kappa = 0.8490142138).
- Non-exchangeability: iid rows use existing certificates; custom shift rows are marked as rerun-required design rows.
- Null inflation: existing-release label interpretations are empirical; altered verified-positive removal ratios are marked rerun-required.
- OVVIS: box-to-mask scaffold over BURST, not full LV-VIS mask benchmark.
- Empty/refusal rows are valid certified-refusal outcomes.
