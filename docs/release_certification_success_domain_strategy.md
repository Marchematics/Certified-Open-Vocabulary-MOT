# Release-Certification Success-Domain Strategy

## Main claim

PARC is a general release-certification interface for finite scientific AI
candidate universes under one-sided partial verification. It should not be
claimed to release in every domain. Instead, the paper should make the stronger
and more testable claim:

> PARC releases when reliable one-sided positives, covered exchangeable blocks,
> sufficient evidence mass, and manageable compatibility conflicts hold; it
> refuses otherwise.

The corresponding public artifact is:

```text
outputs/milestones/scientific_release_success_map/
```

## Evidence hierarchy

1. **Strict positive anchors.**
   - CTC learned-hybrid cell-link release at `alpha=0.10`.
   - Materials/WBM stable-candidate release at `alpha=0.10`.

2. **Practical-benefit rows.**
   - ALIGNN-FF materials rows where raw top-K FTR is high and PARC releases a
     smaller lower-FTR subset.
   - High-volume materials request where PARC refuses an unsafe raw release.
   - Materials stability-threshold and fixed-`gamma` sensitivity rows, now
     backed by completed reruns rather than protocol placeholders.

3. **Real-audit operational/boundary rows.**
   - iWildCam animal-present real human audit succeeds at `alpha=0.20`, while
     strict `alpha=0.10` remains refusal.
   - SpaceNet K=50 human-confirmed release is diagnostic, while K=100 primary
     real-audit request is certified refusal.

4. **Protocol-only gaps.**
   - Strict `alpha=0.10` CTC human/expert audit.
   - Molecular/protein candidate-release domains.

Protocol-only rows must not be cited as completed evidence.

## Paper table guidance

Use `table_cross_domain_evidence_matrix.csv` as the main evidence matrix. It
contains the columns reviewers ask for:

```text
domain, unit, verification_mode, alpha, K, release_status,
PARC_release_size, PARC_FTR, raw_topK_FTR,
false_releases_prevented_est, evidence_mass_phi,
max_observed_e, required_e, block_stress_pass
```

Use `table_success_domain_features.csv` for the success/failure map and
`table_practitioner_success_checklist.csv` as the Methods/Discussion checklist.

## Guardrail language

Recommended wording:

> These experiments map the conditions under which release certification is
> possible. PARC is not a universal releaser: it certifies small release sets
> only when the domain supplies high-precision positives, adequate block
> coverage, and enough evidence mass. Otherwise it returns a certified refusal
> with a diagnostic reason.

Avoid:

> PARC works in all scientific AI domains.

Avoid:

> Protocol-only molecular/protein rows demonstrate generality.
