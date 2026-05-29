# Phase77 NCS Architecture Freeze

Status: `completed_NCS_architecture_freeze`.

## Recommended Title

**Budgeted release certification for scientific AI candidate queues**

Alternative: **Release-card lifecycle certification for scientific AI candidate queues**

## One-sentence Claim

Scientific AI candidate pipelines need release cards rather than static top-K
lists: PARC certifies release or refusal under one-sided verification, PARC-A
shows how scarce targeted audits unlock certified release, and lifecycle
recertification prevents expired certificates from being inherited after
reference drift.

## Finding-first Abstract Skeleton

Scientific AI pipelines increasingly produce finite candidate queues faster than they can be verified. We introduce PARC as a release-card lifecycle framework: it certifies release or refusal under one-sided verification, directs scarce verification budgets, records reference-version expiry and routes expired certificates to recertification, risk triage or refusal. In CTC cell tracking, targeted one-sided audit certifies 2000 links across 20 seeds with no observed false releases, whereas random audit requires far more verification. Materials screening then stress-tests the lifecycle: t0 public-label release cards expire under a current-MP hull update; durability risk is predictable from t0 public-label chemical-system state, but passive and active current-MP recertification refuse. PARC therefore treats refusal, expiry and risk triage as first-class scientific outputs rather than failures to hide.

## Result Order

1. PARC defines one-sided release/refusal certificates for finite candidate queues.
2. Release cards have a lifecycle: certified release/refusal, active audit,
   expiry, recertification, risk triage and refusal.
3. PARC-A is the primary empirical positive in CTC: targeted audit converts
   scarce one-sided verification into certified release.
4. Materials is the lifecycle stress test, not the main positive: t0 public
   release cards expire after current-MP reference drift and recertification
   refuses.
5. PARC-D provides risk triage, not alpha repair.
6. Capability/reproducibility ledger distinguishes PARC lifecycle from
   e-BH-style selection, raw top-K and threshold baselines.

## Stop Rules

- Stop tuning materials K, margin, risk gates or active recertification.
- Do not add new visual/open-world domains.
- Do not wait for DFT v2 before rewriting the manuscript.
- DFT v2 enters only if stable_exact and workflow gates pass.
- The only new empirical study worth adding before writing is Phase78 CTC real
  one-sided audit.

## Evidence Boundary

The NCS core is PARC lifecycle + PARC-A CTC active verification. Materials is a
versioned lifecycle stress test showing expiry, risk triage and refusal. It is
not a prospective materials-discovery claim and not a current-MP alpha
certificate.
