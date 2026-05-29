# NCS Display Plan

Each main figure has one dominant claim.  Dense robustness, no-go grids and DFT
execution details move to Extended Data or Supplement unless they are needed to
understand the lifecycle.

## Figure 1: Release-card lifecycle calculus

**Claim:** PARC turns static candidate queues into versioned release cards with
release, refusal, active audit, expiry, recertification and risk-triage states.

- Panel A, methodological bridge: candidate queue to release card.
- Panel B, definition: lifecycle state machine from `table_release_card_states`.
- Panel C, schema: required release-card fields from `release_card_schema.json`.
- Panel D, translational consequence: lifecycle replay overview for CTC and
  materials.
- Anchor panel: B.
- Main-text topic sentence: Scientific candidate publication is a lifecycle
  decision, not a one-shot top-K list.

## Figure 2: PARC release/refusal mechanism

**Claim:** One-sided null-superset evidence and self-consistency make both
release and refusal valid outputs.

- Panel A, definition: verified positives versus unverified candidates.
- Panel B, claim-supporting method: calibration null-superset block maxima.
- Panel C, method: e-values and self-consistency threshold.
- Panel D, failure mode: certified refusal when evidence mass is insufficient.
- Anchor panel: C.
- Main-text topic sentence: PARC keeps unverified candidates in the null
  superset and refuses when the release-card evidence is insufficient.

## Figure 3: PARC-A active verification primary positive

**Claim:** Targeted one-sided audit unlocks certified CTC release at tiny
verification budgets where random audit does not.

- Panel A, setup: CTC K=100 active-audit task.
- Panel B, anchor evidence: 20/20 safe seeds,
  2000 released links, observed FTR
  0.0.
- Panel C, benchmark comparison: random requires roughly
  200x the targeted budget.
- Panel D, mechanism: score-targeted positives remove null-superset block maxima
  182.5x more than random at the fine-grid
  mechanism point.
- Anchor panel: B.
- Main-text topic sentence: PARC-A converts verification budget into release
  evidence rather than treating missing labels as negatives.

## Figure 4: Materials lifecycle stress test

**Claim:** Materials screening demonstrates why release cards must expire and
recertify under reference drift; it is not the main positive.

- Panel A, lifecycle timeline: t0 public-label release to current-MP t1 update.
- Panel B, version accounting: inherited release burden after reference update.
- Panel C, recertification boundary: Phase74 risk-gated recertification returns
  0/20 non-empty seeds.
- Panel D, active recertification boundary: Phase75 best row has
  4/20 non-empty and
  0/20 safe seeds.
- Anchor panel: C.
- Main-text topic sentence: After the reference changes, the correct lifecycle
  action is expiry plus recertification or refusal, not inherited publication.

## Figure 5: Durability-risk triage

**Claim:** t0 public-label chemical-system state predicts durability risk and
supports triage, but does not repair alpha certification.

- Panel A, model comparison: candidate margin/rank versus system features.
- Panel B, anchor evidence: dropping the top
  30% high-risk rows leaves retained flip
  rate 0.115 versus base
  0.225, while the flagged rows contain
  64.3% of observed flips.
- Panel C, decision map: low-risk retain, high-risk recertify/audit.
- Panel D, boundary: post-filter and risk-gated self-consistency failures.
- Anchor panel: B.
- Main-text topic sentence: Durability risk is a release-card triage signal, not
  a label-free deployment predictor or current-MP certificate.

## Figure 6: Lifecycle capability and claim ledger

**Claim:** PARC lifecycle differs from e-BH-style selection because it supports
one-sided evidence construction, refusal, audit acquisition, expiry,
recertification and release cards.

- Panel A, capability matrix: PARC lifecycle versus e-BH, raw top-K, threshold,
  conformal and PU baselines.
- Panel B, evidence hierarchy: completed positive, stress test, no-go, pending.
- Panel C, reproducibility ledger: claim-to-artifact mapping.
- Panel D, optional slot: DFT v2 enters only after stable_exact and workflow
  gates pass.
- Anchor panel: A.
- Main-text topic sentence: The contribution is a lifecycle capability rather
  than another static selector.

## Supplement Priority

- Full materials K/margin/risk-gate grids.
- Phase74/75 no-go details.
- DFT v2 execution checkpoint.
- Extended baseline risk-utility tables.
- Additional schema fields and release-card examples.
