# OWLv2 Cross-Generator Failure Analysis

Status: diagnostic only, not a main PARC-Track result.

## Finding

OWLv2 candidate generation completed on OVT-B and TAO, but the resulting candidate ranking is too weak for PARC-Track fixed-M certification. The failure is not caused by finite p-value resolution: the effective maximum e-values are high enough. The bottleneck is insufficient high-evidence mass under uniform SCS-Greedy.

## Evidence

Top-M official support rates are much lower for OWLv2 than for the GroundingDINO scaffold:

- OVT-B top-150 PSR: OWLv2 22.7%, GroundingDINO 99.3%.
- TAO top-150 PSR: OWLv2 6.7%, GroundingDINO 96.0%.

For OWLv2 fixed M=150, PARC has `release_feasible=True` from the finite-resolution diagnostic, but no alpha/seed releases. The reported empty diagnostic is:

```text
insufficient_high_e_mass_for_uniform_scs
```

Small-M sweeps show that OWLv2 can produce non-empty releases only at very small budgets, but these releases have high UTR and are not suitable as positive cross-generator evidence.

## OWLv2-rerank v1

We implemented a label-free reranker using objectness, semantic score, association score, path length, and temporal stability. It improves PSR but not enough to support the requested `M=50/100/150` matrix:

- OVT-B PSR@150 improves from 22.7% to 31.3%.
- TAO PSR@150 improves from 6.7% to 16.0%.
- PARC remains empty for `M=50/100/150`, `alpha in {0.10, 0.20}`, and seeds 0/1/2.

## Paper Usage

Use OWLv2 as a cross-generator failure analysis, not as a main result. The correct interpretation is that PARC-Track exposes proposal/ranking weakness: low-quality candidate universes can be detected before publication by high-e mass and UTR diagnostics.
