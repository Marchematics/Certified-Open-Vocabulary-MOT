# Release Certification Governance Protocol

This protocol is a reusable checklist for finite scientific-AI candidate universes under one-sided partial verification.

## Required Setup

1. Freeze the candidate universe and proposal-source scores.
2. Define the release unit and downstream artifact.
3. Define the one-sided positive rule: only confirmed positives enter `A=1`; uncertain, negative or disputed labels remain unverified.
4. Define blocks and the empty-block policy.
5. Freeze alpha, requested K values and seeds.

## Release Decision

Run PARC on the frozen universe. A certified refusal is a valid outcome when the observed evidence is insufficient for the requested release.

## Evaluation

Use held-out official labels, public DFT labels, or human-audit labels only after the release/refusal decision. Report raw top-K risk on the same evaluation source.

## Reporting

Every card must include evidence status and limitation language. Protocol-only designs must not be reported as completed evidence.
