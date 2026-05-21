# Initial Experiment Results

Date: 2026-05-22

Plan: `refine-logs/EXPERIMENT_PLAN.md`

## Results by Milestone

### M1: Materials Label-Source Discordance Atlas — DONE

Existing completed artifact:

- `outputs/milestones/materials_label_source_discordance_atlas/table_mp_alex_discordance_atlas_summary.csv`
- Full MP-Alex exact-structure denominator: 43,139 strict matches.
- Exact-stability disagreements: 5,060.
- Discordance rate: 0.1173.
- Claim boundary: benchmark-reliability / source-uncertainty atlas; not positive independent validation and not prospective discovery.

### M2: Verified-Positive Contamination Sensitivity — DONE

Command:

```bash
python scripts/run_verified_positive_contamination_sensitivity.py
```

Outputs:

- `outputs/milestones/verification_assumption_sensitivity/table_verified_positive_contamination_sensitivity_seed_rows.csv`
- `outputs/milestones/verification_assumption_sensitivity/table_verified_positive_contamination_sensitivity_summary.csv`
- `outputs/milestones/verification_assumption_sensitivity/figure_verified_positive_contamination_sensitivity_source.csv`
- `outputs/milestones/verification_assumption_sensitivity/VERIFICATION_ASSUMPTION_SENSITIVITY_CLOSEOUT.md`

Main facts:

- Target rows: 5.
- Seed-level rows: 1,200.
- Summary rows: 60.
- Rates: `0, 0.005, 0.01, 0.02, 0.05, 0.10`.
- Modes: `random`, `adversarial`.
- CTC learned strict rows remain at mean FTR 0 under this diagnostic grid.
- Materials ALIGNN rows expose the expected assumption boundary: adversarial contamination at epsilon 0.005 already pushes the K=300 diagnostic into alpha-violation territory in some seeds; larger epsilon values approach raw-top-K behavior.

Interpretation:

Nonzero-contamination rows are assumption-violation diagnostics. They do not weaken the formal theorem under its stated assumption; they make the use-policy boundary legible.

### M3: Source-Uncertainty Overlay — DONE AS DIAGNOSTIC

Existing completed artifact:

- `outputs/milestones/materials_queue_source_uncertainty_overlay/`

Main facts:

- K=300 and K=500 ALIGNN queue overlays exist at candidate level.
- Exact-structure alex-mp metrics remain diagnostic only.
- These rows explicitly forbid positive independent-validation wording.

### M4: External Blind Audit Packet — PACKET DONE, LABELS PENDING

Existing completed artifact:

- `outputs/milestones/external_blind_audit_packet/`

Main facts:

- Frozen packet contains iWildCam and SpaceNet rows.
- No positive external-audit claim is supported until non-author labels and adjudication return.

## Summary

- Must-run experiments completed: 2/2.
- Nice-to-have artifacts available: 2/2, with claim boundaries.
- Main result: positive for a non-A3 reinforcement package, scoped to release-governance and assumption-boundary diagnostics.
- Ready for `/auto-review-loop`: yes, if the review prompt uses the narrow two-anchor release-governance framing and does not promote A3.
