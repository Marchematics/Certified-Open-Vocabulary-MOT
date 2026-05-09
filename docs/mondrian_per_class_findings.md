# Mondrian And Per-Class Findings

This note summarizes the paper-facing interpretation of the Mondrian granularity
and per-class release diagnostics.

## Mondrian Granularity

For OVT-B at fixed `M=150`, global calibration gives substantially higher release
power, while fine-grained Mondrian cells reduce unsupported/conservative FTR at a
large power cost.

| Dataset | Alpha | Cell | Released Mean | UTR Mean | Cons. FTR Mean | Non-empty Rate |
|---|---:|---|---:|---:|---:|---:|
| OVT-B | 0.10 | global | 135.0 | 0.0219 | 0.0219 | 1.00 |
| OVT-B | 0.10 | category/query/category+occ | 34.0 | 0.0033 | 0.0098 | 0.33 |
| OVT-B | 0.20 | global | 150.0 | 0.0200 | 0.0200 | 1.00 |
| OVT-B | 0.20 | category/query/category+occ | 97.7 | 0.0033 | 0.0033 | 1.00 |
| TAO | 0.20 | global | 147.3 | 0.0246 | 0.0178 | 1.00 |
| TAO | 0.20 | category/query/category+occ | 0.0 | 0.0000 | n/a | 0.00 |

Interpretation:

- Fine cells are not a free improvement. They reduce risk diagnostics on OVT-B
  but can sharply reduce finite-sample power because many cells have sparse or
  empty calibration coverage.
- TAO is the clearest case: the global cell has enough coverage to release at
  `alpha=0.20`, while category/query-level cells remain empty.
- The main paper should present global calibration as the deployed fixed protocol
  for real-data power, with Mondrian granularity as a conservative/power tradeoff
  ablation rather than as an always-better default.

## Per-Class / Head-Mid-Tail Pattern

Head/mid/tail segments are defined by query frequency in the OVT-B full candidate
universe. For OVT-B, GroundingDINO, `alpha=0.10`, fixed `M=150`:

| Query Segment | Num Queries | Candidate Paths | Released Mean | Unsupported Mean | Cons. FTR Proxy |
|---|---:|---:|---:|---:|---:|
| head | 165 | 12828 | 108.7 | 2.3 | 0.0216 |
| mid | 248 | 2688 | 16.3 | 0.7 | 0.0341 |
| tail | 413 | 1297 | 10.0 | 0.0 | 0.0000 |

Interpretation:

- PARC-Track release mass is concentrated in head queries, especially `person`.
  This is expected under a global finite-budget certification layer.
- Tail queries are not completely suppressed: the tail segment still contributes
  roughly 10 releases on average at `alpha=0.10`, with zero unsupported rows in
  this diagnostic.
- The right framing is not "PARC solves long-tail tracking"; it is "PARC remains
  capable of releasing a small number of high-evidence tail-query tracks while
  maintaining conservative risk diagnostics."

Useful examples from released tail queries include `sunglasses`, `garbage truck`,
`seagull`, `picnic basket`, `polo shirt`, `defibrillator`, `music box`, and
`doughnut`.

