# Certified Refusal Guide

PARC returns either a certified release set or a certified refusal. This guide explains how to interpret refusal rows in public tables.

## What certified refusal means

A certified refusal means the public evidence available to the release rule is insufficient to certify a non-empty compatible set under the requested risk level and budget.

It does not mean that every candidate is false. It means the current verification, scoring, block coverage, or compatibility graph does not support a statistically certified release.

## Common refusal reasons

- **Finite-resolution cap:** the largest observed e-value is below the threshold needed for the requested `K / alpha`.
- **Evidence-mass failure:** high-evidence candidates exist, but not enough compatible mass exists to support the requested release.
- **Coverage failure:** too few calibration or audit positives cover release-relevant blocks.
- **Compatibility conflict:** individually strong candidates conflict with each other under the set-level compatibility graph.
- **One-sided reliability failure:** the verification source cannot safely assert that `A=1` implies a true positive.
- **Semantic grounding failure:** the detector or prompt source does not align with the target release semantics.

## How refusal should be reported

Public tables should include:

- the requested `K`, `alpha`, and seed set;
- `non_empty_seeds`;
- `max_observed_e` and the required threshold when available;
- evidence mass or mass ratio diagnostics;
- block coverage diagnostics;
- an `empty_reason` or `safe_refusal_reason`.

## Why refusal is useful

Refusal prevents unsafe release when raw top-K output would be unsupported, high-risk, or outside the verified operating envelope. For deployment, the refusal is an actionable signal: add verification coverage, reduce the requested release volume, improve the proposal source, or change the compatibility graph.

## What refusal does not claim

Certified refusal is not a statement about the full candidate universe and is not a proof that the upstream model is unusable. It is a release decision for a specific frozen universe, protocol, and risk target.
