# Finding-First NCS Spine

## Recommended Title

**Reference-neighborhood fragility in scientific AI candidate release**

Alternative:

**Budgeted release cards for scientific AI candidate queues**

## One-Sentence Spine

Scientific AI candidate queues should be published with release cards rather
than static top-K lists: PARC supplies the one-sided release/refusal calculus,
PARC-A shows that targeted verification can unlock certified release, and the
materials durability-risk result shows that certificate fragility is governed
by the reference neighborhood rather than candidate margin or rank.

## Finding Hierarchy

1. **Primary workflow positive:** In CTC, a 0.5%
   targeted one-sided audit certifies 2000 released
   links across 20/20 safe seeds with observed FTR
   0.0; random audit needs roughly
   200x the budget.
2. **Main conceptual materials finding:** In materials, candidate margin and
   rank are weak predictors of stable-to-current-unstable drift
   (AUC 0.544 and
   0.467), while t0 chemical-system state is
   predictive (AUC 0.766). The strongest
   mechanism is the system margin-landscape distribution
   (AUC 0.844), not raw near-hull
   density (AUC 0.502).
3. **Breadth support:** Phase79 controlled simulations recover both mechanisms:
   candidate-driven reference drift is predicted by candidate features
   (AUC 0.859 vs system
   0.517), while
   neighborhood-driven drift is predicted by system features
   (AUC 0.784 vs candidate
   0.504).
4. **Lifecycle calculus:** Release, refusal, active audit, expiry,
   recertification and risk triage are first-class release-card states.

## Main Boundary

This is a reliability study for ML-driven scientific screening. PARC is the
tooling that makes release-card states auditable; the manuscript should not be
framed as a broad new discovery engine or as a repaired current-MP materials
alpha certificate.

## DFT v2 Handling

DFT v2 remains quarantined. The checkpoint has 11
completed and 2 failed jobs, with early failure fraction
0.154; no stable_exact outcomes are claim-ready.
It enters the main paper only if the pre-frozen workflow and stable_exact gates
pass.
