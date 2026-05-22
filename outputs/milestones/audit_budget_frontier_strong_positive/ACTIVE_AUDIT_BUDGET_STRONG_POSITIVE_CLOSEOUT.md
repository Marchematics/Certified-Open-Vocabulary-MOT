# Active Audit Budget Frontier Strong-Positive Closeout

Status: completed strong-positive CTC active-audit result.

This package tightens the audit-budget frontier into a CTC-only strong-positive gate. The primary row is deliberately narrower than the broader headline package: it requires 20/20 nonempty safe seeds, zero observed false releases, a matched-budget random refusal, and a full-random-audit transition control. Materials rows are excluded from the strong-positive gate.

## Primary Gate

- Primary row: ctc_learned_strict_alpha010_K100.
- Top-score audit budget: 0.005.
- Top-score safe seeds: 20/20.
- Top-score total releases / false releases: 2000 / 0.0.
- Matched-budget random nonempty seeds: 0/20.
- Random transition budget: 1.0 (200.0x the targeted budget).
- Support row: ctc_learned_strict_alpha010_K300 released safely in 19/20 seeds at the same 0.5% budget, so it is support-only rather than the primary gate.

## Claim Boundary

- This is completed simulated-audit evidence over existing CTC held-out labels.
- It is a strong positive for the active-audit release-governance mechanism, not for A3.
- It does not claim prospective materials discovery.
- Materials audit-budget rows remain boundary/secondary evidence outside this strong-positive gate.
