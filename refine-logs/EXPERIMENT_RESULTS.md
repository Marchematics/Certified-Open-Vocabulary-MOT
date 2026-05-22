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

### M5: Materials Label-Discordance Preregistration / Minimal Probe — DONE

Outputs:

- `outputs/milestones/materials_label_discordance_preregistration/`

This package freezes source-access, matching, and go/no-go rules and includes a minimal discordance probe. It supports the material-source uncertainty framing, but it is not a final positive independent-validation result and does not make PARC the primary contribution.

### M6: Selection-Conditional Discordance — DONE NO-GO

Outputs:

- `outputs/milestones/materials_selection_conditional_discordance/table_selection_conditional_go_no_go.csv`

Main facts:

- Source pair: Materials Project vs alex-mp v20.
- Common denominator: 287.
- Baseline discordance: 0.1080.
- Models tested: ALIGNN-FF, CHGNet, MACE-MP.
- Models supporting the preregistered high-score amplification rule: 0.
- Go/no-go: `NO_GO_hypothesis_B_not_supported`.

Interpretation:

This is a completed negative diagnostic. It should be used to show that not every plausible source-discordance hypothesis is supported, not as positive validation or headline evidence.

### M7: LLM Release-Agent Stress-Test Protocol — BLOCKED, PROTOCOL FROZEN

Outputs:

- `outputs/milestones/llm_release_agent_stress_test/`

Main facts:

- Frozen prompt conditions: minimal curator, one-sided-aware curator, high-pressure scientific curator, PARC-informed curator, and raw-score leaderboard curator.
- Frozen task manifest covers CTC, materials ALIGNN, SpaceNet, and iWildCam release settings.
- Credential check found no usable API keys in the environment.
- No LLM calls were made and no release-agent decisions were scored.

Interpretation:

This is a protocol/task scaffold only. It cannot support a positive LLM-agent headline claim until model outputs are actually run and scored.

### M8: Active Audit Budget Frontier — DONE

Command:

```bash
python scripts/run_audit_budget_release_frontier.py
```

Outputs:

- `outputs/milestones/audit_budget_release_frontier/table_audit_budget_frontier_seed_rows.csv`
- `outputs/milestones/audit_budget_release_frontier/table_audit_budget_frontier_summary.csv`
- `outputs/milestones/audit_budget_release_frontier/figure_audit_budget_frontier_source.csv`
- `outputs/milestones/audit_budget_release_frontier/AUDIT_BUDGET_FRONTIER_CLOSEOUT.md`

Main facts:

- Target rows: 5.
- Seeds: 20.
- Audit policies: random, top-score, block-balanced top-score, diversity round-robin.
- Audit budgets: 0, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20 of calibration candidates inspected.
- Seed-level rows: 2,800.
- Summary rows: 140.
- Top-score audit reaches safe release at 0.005 for CTC K=100/K=300 and ALIGNN K=300/K=500 in the simulated-audit grid; random audit does not reach a safe-release transition within the frozen grid for those rows.

Interpretation:

This is completed simulated-audit evidence for an audit-budget release frontier. Hidden full labels are used only to simulate one-sided audit returns and post-hoc FTR, not as new prospective labels. The result supports an audit-governance method claim only under the simulated-audit scope; it is not prospective materials discovery and does not modify A3.

### M9: Audit Budget Headline Package — DONE

Commands:

```bash
python scripts/run_audit_budget_release_frontier.py \
  --policies random,top_score \
  --budget-fractions 0,0.005,0.01,0.02,0.05,0.1,0.2,0.5,1.0 \
  --out-dir outputs/milestones/audit_budget_release_frontier_extended
python scripts/build_audit_budget_frontier_headline_package.py
```

Outputs:

- `outputs/milestones/audit_budget_release_frontier_extended/`
- `outputs/milestones/audit_budget_release_frontier_headline/table_audit_budget_transition_primary.csv`
- `outputs/milestones/audit_budget_release_frontier_headline/table_audit_policy_efficiency.csv`
- `outputs/milestones/audit_budget_release_frontier_headline/table_audit_budget_frontier_lead_numbers.csv`
- `outputs/milestones/audit_budget_release_frontier_headline/figure_audit_budget_transition_source.csv`

Main facts:

- Extended random/top-score grid adds budgets 0.5 and 1.0.
- CTC K=100 and K=300 meet the strict seed-stable criterion at 0.005 top-score audit budget.
- Random audit reaches the same strict criterion only at 1.0 for those CTC rows, giving a 200x top-score-vs-random budget ratio in the frozen grid.
- Materials ALIGNN K=300 and K=500 meet a mean-operating criterion at 0.005, but not the strict seed-stable criterion: seed-level alpha-violation rates are 0.45 and 0.15 respectively.
- CGCNN K=100 remains a calibration/check row, not a headline utility claim.

Interpretation:

The audit-budget frontier now has one clean strict headline candidate: CTC release certification can transition from refusal to strict seed-stable release with a tiny targeted audit budget. The materials ALIGNN audit-budget rows are useful but must be reported as secondary boundary evidence, not as a strict headline.

### M10: NMI Reviewer P0 Hardening — DONE

Command:

```bash
python scripts/build_nmi_reviewer_p0_hardening.py
```

Outputs:

- `outputs/milestones/nmi_reviewer_p0_hardening/table_p0_reviewer_gap_action_matrix.csv`
- `outputs/milestones/nmi_reviewer_p0_hardening/table_human_audit_uncertainty_intervals.csv`
- `outputs/milestones/nmi_reviewer_p0_hardening/table_baseline_frontier_maintext_map.csv`
- `outputs/milestones/nmi_reviewer_p0_hardening/table_assumption_diagnostics_maintext_map.csv`
- `outputs/milestones/nmi_reviewer_p0_hardening/table_refusal_feasibility_attribution.csv`

Main facts:

- Prospective / independent materials validation remains `not_completed_positive_evidence`.
- External materials labels remain completed negative/diagnostic-only evidence, not positive validation.
- iWildCam 167/167 and SpaceNet 147/147 zero-false audit rows now include Clopper-Pearson, Wilson, and Jeffreys upper intervals.
- Baseline rows are mapped by target object and certificate properties, keeping different-target comparators scoped.
- Refusal rows are attributed to evidence-mass or finite-resolution gates, not to an unexamined greedy miss.

Interpretation:

This package turns the reviewer P0 checklist into paper-facing support tables. It hardens the claim boundary, but does not create prospective materials evidence.

### M11: NMI Main-Text Evidence Package — DONE

Command:

```bash
python scripts/build_nmi_maintext_evidence_package.py
```

Outputs:

- `outputs/milestones/nmi_maintext_evidence_package/table_headline_evidence_hierarchy.csv`
- `outputs/milestones/nmi_maintext_evidence_package/table_maintext_claim_sentences.csv`
- `outputs/milestones/nmi_maintext_evidence_package/figure_audit_budget_maintext_source.csv`
- `outputs/milestones/nmi_maintext_evidence_package/figure_reviewer_p0_support_source.csv`
- `outputs/milestones/nmi_maintext_evidence_package/table_figures_to_artifacts.csv`

Main facts:

- The only primary-headline row is the CTC active-audit strict transition.
- The exact primary sentence states that 0.5% top-score audit converted CTC K=100/K=300 refusal into strict seed-stable certified release at alpha=0.10, while random audit required full calibration-set inspection in the frozen grid.
- Materials audit-budget rows are boundary/secondary because K=300 and K=500 have seed-level alpha-violation rates of 0.45 and 0.15.
- The materials prospective row is explicitly `not_completed_positive_evidence`.
- Every claim sentence maps to a source artifact and SHA256 hash.

Interpretation:

This is a paper-facing postprocess package. It does not add new evidence; it prevents the manuscript from accidentally promoting diagnostics, pending rows, or materials no-go rows into headline claims.

### M12: Active Audit Budget Strong-Positive Gate — DONE

Command:

```bash
python scripts/build_audit_budget_frontier_strong_positive.py
python scripts/build_nmi_maintext_evidence_package.py
python scripts/build_non_a3_experiment_bridge.py
```

Outputs:

- `outputs/milestones/audit_budget_frontier_strong_positive/table_strong_positive_gate_audit.csv`
- `outputs/milestones/audit_budget_frontier_strong_positive/table_ctc_primary_seed_rows.csv`
- `outputs/milestones/audit_budget_frontier_strong_positive/table_audit_budget_policy_contrast.csv`
- `outputs/milestones/audit_budget_frontier_strong_positive/table_active_audit_effect_sizes.csv`
- `outputs/milestones/audit_budget_frontier_strong_positive/figure_active_audit_strong_positive_source.csv`

Main facts:

- Primary strong-positive row: `ctc_learned_strict_alpha010_K100`.
- Top-score audit budget: 0.005 of calibration candidates.
- Top-score result: 20/20 nonempty safe seeds, 2,000 total releases across seeds, 0 observed false releases, mean FTR 0.
- Matched-budget random audit: 0/20 nonempty seeds at the same 0.005 budget.
- Full random audit transition: random reaches 20/20 safe seeds only at 1.0 audit budget, a 200x budget ratio.
- CTC K=300 is support-only because it is 19/20 safe at the same budget, not 20/20.
- Materials rows are excluded from this strong-positive gate and remain boundary/secondary.

Interpretation:

This fixes Active audit budget frontier as a clean non-A3 strong positive: a tiny targeted one-sided audit can turn CTC refusal into certified release, while matched-budget random audit cannot. The claim is deliberately CTC-only and simulated-audit scoped; it does not create prospective materials evidence and does not alter A3.

### M13: T1 Clean Acceptance Baseline Frontier — DONE

Command:

```bash
python scripts/build_t1_clean_acceptance_package.py
python scripts/build_nmi_maintext_evidence_package.py
python scripts/build_non_a3_experiment_bridge.py
```

Outputs:

- `outputs/milestones/t1_clean_acceptance_package/table_t1_baseline_frontier_summary.csv`
- `outputs/milestones/t1_clean_acceptance_package/figure_t1_empirical_baseline_frontier_source.csv`
- `outputs/milestones/t1_clean_acceptance_package/table_t1_baseline_family_coverage.csv`
- `outputs/milestones/t1_clean_acceptance_package/table_t1_materials_validation_go_no_go.csv`
- `outputs/milestones/t1_clean_acceptance_package/table_t1_clean_acceptance_lead_numbers.csv`
- `outputs/milestones/t1_clean_acceptance_package/T1_CLEAN_ACCEPTANCE_CLOSEOUT.md`

Main facts:

- ALIGNN K=300 fixed-budget row: raw top-K FTR 0.253, PARC FTR 0.087, raw top-R matched FTR 0.087, and 64.25 unstable follow-ups prevented.
- ALIGNN K=500 fixed-budget row: raw top-K FTR 0.327, PARC FTR 0.048, raw top-R matched FTR 0.048, and 158.30 unstable follow-ups prevented.
- CGCNN K=500 baseline frontier: raw top-K FTR 0.326, post-filter e-value FTR 0.163, PARC/raw top-R FTR 0.032; e-BH releases no candidates.
- The empirical frontier covers 11 method families, including raw top-K, raw top-R, thresholds, split conformal, post-filter e-value, e-BH-style, nnPU, Bao-style selective conformal adaptation, oracle prefix, and PARC.
- The materials validation ledger marks 5/5 independent/prospective routes as not positive evidence.

Interpretation:

This package addresses the T1 clean-acceptance gap with a stronger empirical baseline frontier figure while preserving the materials boundary. It does not create prospective materials evidence. Raw top-R remains a matched-volume diagnostic, and only PARC rows have the full null-superset + SCS release certificate.

### M14: Release-Governance Problem Paradigm — DONE

Command:

```bash
python scripts/build_release_governance_paradigm_package.py
python scripts/build_nmi_maintext_evidence_package.py
python scripts/build_non_a3_experiment_bridge.py
```

Outputs:

- `outputs/milestones/release_governance_problem_paradigm/table_release_governance_paradigm_components.csv`
- `outputs/milestones/release_governance_problem_paradigm/table_release_governance_claim_evidence_map.csv`
- `outputs/milestones/release_governance_problem_paradigm/table_release_governance_figure_blueprint.csv`
- `outputs/milestones/release_governance_problem_paradigm/release_governance_abstract_v2.md`
- `outputs/milestones/release_governance_problem_paradigm/release_governance_maintext_skeleton.md`
- `outputs/milestones/release_governance_problem_paradigm/RELEASE_GOVERNANCE_PARADIGM_CLOSEOUT.md`

Main facts:

- The package defines the paper as release-time governance for frozen scientific candidate universes under scarce one-sided verification.
- It binds the CTC K=100 active-audit strong-positive row, the T1 empirical baseline frontier, refusal attribution, and audit uncertainty into one claim-evidence closure.
- The draft abstract keeps the strong headline on CTC active audit and keeps materials as retrospective public-label release-policy frontier evidence.
- The maintext evidence package now includes the release-governance paradigm as `paper_positioning_frame`, not as a new primary headline.

Interpretation:

This is the route-2 clean-acceptance package. It raises the framing from a collection of diagnostics to a coherent problem paradigm without adding new labels or creating independent materials validation. The only primary headline remains CTC K=100 active audit; T1 remains baseline-frontier support.
