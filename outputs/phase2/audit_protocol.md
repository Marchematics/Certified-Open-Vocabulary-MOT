# PARC-Track Phase-2 Audit Protocol

Audit target:

- Candidate CSV: `/home/waas/paper_experiments/outputs/phase2/audit_candidates.csv`
- Label sheet: `/home/waas/paper_experiments/outputs/phase2/audit_labels.csv`
- Viewer: `/home/waas/paper_experiments/audit_viewer/index.html`

Allowed labels:

- `actually_true`: most frames cover the same real object, the query/category is visually reasonable, and the path is not obvious drift.
- `actually_false`: background, texture, shadow, wrong category, clear object switching, or detector hallucination.
- `uncertain`: small object, severe blur/occlusion, ambiguous category, mixed true/drift, or not enough evidence.

One-sided rule:

- Only `actually_true` may be used as a verified positive.
- `uncertain` stays unverified and must not be removed from the null-superset.
- Prefer `uncertain` over `actually_true` whenever there is doubt.

Recommended visual rule:

- Mark `actually_true` only if at least about 70% of visible sampled panels support the same object identity and class/query.
