# PARC Non-A3 Frontier Reinforcement Experiment Plan

Status: active execution plan for `experiment-bridge`.

## Goal

Move the paper away from A3-dependent prospective-materials claims and toward a completed non-A3 reinforcement package:

1. Materials label-source discordance atlas.
2. Verified-positive contamination sensitivity.
3. Source-uncertainty release/refusal overlay if candidate-level joins are available.
4. External blind audit packet as a trust-upgrade asset, not completed positive evidence until labels return.

## Milestones

| Milestone | Priority | Execution rule | Success criterion | Status |
| --- | --- | --- | --- | --- |
| M0: Inventory and plan freeze | MUST | Reuse existing phase34-37 artifacts; do not modify A3 selection/manifests | Plan/tracker/code-review logs created | in_progress |
| M1: Materials label-source discordance atlas | MUST | Use existing public-data MP-Alex atlas outputs | Full denominator 43,139 strict matches / 5,060 disagreements present and scoped as benchmark reliability | completed_existing_artifact |
| M2: Verified-positive contamination sensitivity | MUST | Run epsilon grid `{0,0.005,0.01,0.02,0.05,0.10}` with `random` and `adversarial` contamination over CTC/materials hard rows | Seed rows, summary, figure source, manifest, and tests | running |
| M3: Source-uncertainty overlay | NICE | Use existing phase36 candidate-level overlay if available; otherwise no-go as diagnostic | K=300/500 exact-match-only overlay summary exists and forbids independent-validation overclaim | completed_existing_artifact |
| M4: External blind audit packet | NICE | Use existing phase35 frozen blind packet; labels are pending | Packet integrity tables exist; no positive claim | completed_packet_pending_labels |

## Guardrails

- A3 is not headline-positive evidence.
- OQMD/alex-mp/MP-Alex are source-discordance diagnostics, not positive independent validation.
- Nonzero contamination rows are assumption-violation diagnostics, not formal PARC guarantees.
- External blind audit packets are pending until non-author labels and adjudication return.
- Evaluation uses dataset ground truth labels or frozen public label sources, never another model as ground truth.

## Deployment

Backend: local CPU.

Estimated runtime: minutes for table-building; no GPU required.

## Execution Update

The initial non-A3 bridge has now been extended into a paper-facing evidence package.

| Milestone | Status | Claim Role |
| --- | --- | --- |
| M5: Materials label-discordance preregistration/probe | completed | source-uncertainty preregistration/probe only |
| M6: Selection-conditional discordance | completed no-go | completed negative diagnostic |
| M7: LLM release-agent stress-test protocol | blocked / protocol frozen | no behavioral evidence without model outputs |
| M8: Active audit budget frontier | completed | simulated audit-governance frontier |
| M9: Active audit budget headline package | completed | CTC strict headline candidate; materials boundary secondary |
| M10: NMI reviewer P0 hardening | completed | reviewer-facing support and claim-boundary hardening |
| M11: NMI main-text evidence package | completed | exact claim sentences and figure source rows |

The current paper-facing hierarchy is: CTC active-audit strict transition as the only primary headline; materials fixed/audit-budget rows as retrospective or boundary evidence; external material-source diagnostics as stress/no-go evidence; A3 outside positive claims.
