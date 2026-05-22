# Experiment Code Review

Status: local-only review. The `experiment-bridge` skill normally requests a secondary Codex code reviewer, but this session is constrained by the active sub-agent policy, so no new reviewer agent was spawned.

## Reviewed Implementation

- `scripts/__init__.py`
- `scripts/run_verified_positive_contamination_sensitivity.py`
- `tests/test_verification_assumption_sensitivity.py`

## Checklist

| Check | Result | Notes |
| --- | --- | --- |
| Implements requested epsilon grid | PASS | Defaults: `0,0.005,0.01,0.02,0.05,0.10`. |
| Implements random and adversarial contamination | PASS | Random uses fixed seeded RNG; adversarial selects highest-score false calibration candidates. |
| Uses dataset ground truth | PASS | CTC uses `~is_unmatched`; materials uses `stable_exact` from frozen WBM labels. |
| Does not use model output as ground truth | PASS | Scores are used only for ranking, observation, and adversarial contamination ordering. |
| Reuses existing PARC e-value/SCS logic | PASS | Imports `compute_evalues_from_null`, `observed_positive_mask`, and `scs_release_count` from the existing candidate-level ablation script. |
| Saves parseable outputs | PASS | Seed rows, summary, figure source, provenance, closeout, and SHA256 manifest. |
| Preserves claim boundary | PASS | Nonzero contamination rows are explicitly marked `assumption_violation_sensitivity_not_formal_guarantee`. |
| Does not modify A3 selection/manifests | PASS | New outputs are under `verification_assumption_sensitivity`; no A3 files touched by the script. |

## Non-blocking Notes

- The diagnostic intentionally breaks the verified-positive assumption; positive or negative results must not be described as formal guarantees.
- The `scripts/__init__.py` file fixes a local import shadowing issue caused by an unrelated site-packages module named `scripts`.

## Phase40 Local Review Addendum

Reviewed:

- `scripts/build_llm_release_agent_stress_test.py`
- `scripts/run_audit_budget_release_frontier.py`
- `tests/test_llm_release_agent_stress_test.py`
- `tests/test_audit_budget_release_frontier.py`

| Check | Result | Notes |
| --- | --- | --- |
| LLM scaffold does not fabricate outputs | PASS | Credential status is recorded without secret values; run manifest remains blocked/pending and marks positive evidence as none. |
| Prompt contract encodes one-sided verification | PASS | The prompt templates explicitly state that unverified candidates are not negative labels. |
| Audit frontier uses hidden truth only as simulated audit oracle / post-hoc evaluation | PASS | Inspected true positives become one-sided verified positives; negative audit results are not used as verified negatives. |
| Audit policies and budgets match preregistration | PASS | Defaults are 4 policies, 7 budget fractions, 20 seeds, and 5 target rows. |
| Uses ground truth for evaluation, not model output | PASS | CTC uses `~is_unmatched`; materials uses WBM `stable_exact`; scores are ranking/audit-priority inputs only. |
| Preserves A3 boundary | PASS | Both closeouts state no A3 evidence and no prospective materials-discovery claim. |

## Phase41 Local Review Addendum

Reviewed:

- `scripts/build_audit_budget_frontier_headline_package.py`
- `tests/test_audit_budget_frontier_headline.py`

| Check | Result | Notes |
| --- | --- | --- |
| Separates strict and mean-operating criteria | PASS | Strict headline requires `safe_release_rate >= 0.9` and mean FTR within alpha; materials rows that only satisfy mean-operating criteria are secondary boundary rows. |
| Keeps CGCNN scoped | PASS | CGCNN K=100 is marked `calibration_check_not_headline`. |
| Provides random comparator | PASS | Extended random/top-score grid reaches 1.0 budget for random and 0.005 for top-score on CTC strict rows. |
| Avoids prospective materials wording | PASS | Closeout and lead rows explicitly preserve simulated-audit / no-A3 / no-prospective-discovery boundaries. |

## Phase42 Local Review Addendum

Reviewed:

- `scripts/build_nmi_reviewer_p0_hardening.py`
- `tests/test_nmi_reviewer_p0_hardening.py`

| Check | Result | Notes |
| --- | --- | --- |
| Keeps materials A1/A2/A3 scoped | PASS | Prospective / independent materials validation remains not-completed positive evidence. |
| Adds audit uncertainty intervals | PASS | iWildCam and SpaceNet zero-false audit rows include Clopper-Pearson, Wilson, and Jeffreys upper intervals. |
| Preserves baseline target boundaries | PASS | Different-target baselines are mapped by certificate properties rather than promoted as direct PARC replacements. |
| Avoids greedy-refusal overclaim | PASS | Refusal attribution distinguishes evidence-mass and finite-resolution gates from selector-power claims. |

## Phase43 Local Review Addendum

Reviewed:

- `scripts/build_nmi_maintext_evidence_package.py`
- `tests/test_nmi_maintext_evidence_package.py`
- `scripts/build_non_a3_experiment_bridge.py`
- `tests/test_non_a3_experiment_bridge.py`

| Check | Result | Notes |
| --- | --- | --- |
| Produces exact claim sentences | PASS | Every claim row maps to a source artifact and SHA256 hash. |
| Restricts primary headline | PASS | The only primary headline row is the CTC active-audit strict transition. |
| Keeps materials rows scoped | PASS | Materials audit-budget rows are boundary/secondary; prospective materials discovery remains forbidden. |
| Preserves bridge boundaries | PASS | The non-A3 bridge now records the package as paper-facing postprocess, not new evidence. |
| Does not touch A3 selection/manifests | PASS | All new outputs are under `nmi_maintext_evidence_package` and `non_a3_experiment_bridge`. |

## Phase44 Local Review Addendum

Reviewed:

- `scripts/build_audit_budget_frontier_strong_positive.py`
- `tests/test_audit_budget_frontier_strong_positive.py`
- updated `scripts/build_nmi_maintext_evidence_package.py`
- updated `scripts/build_non_a3_experiment_bridge.py`

| Check | Result | Notes |
| --- | --- | --- |
| Strong-positive gate is narrow | PASS | Only CTC K=100 is primary strong-positive evidence. |
| Handles CTC K=300 honestly | PASS | K=300 is 19/20 safe at 0.5% audit budget and is support-only, not primary. |
| Keeps materials out of strong-positive claim | PASS | Materials rows are excluded from the strong-positive package and remain boundary/secondary elsewhere. |
| Provides matched-budget random control | PASS | Matched 0.5% random audit releases 0/20 CTC K=100 seeds; full random audit reaches transition at 1.0 budget. |
| Preserves A3 boundary | PASS | Strong-positive closeout states this is not A3 evidence and does not claim prospective materials discovery. |

## Phase45 Local Review Addendum

Reviewed:

- `scripts/build_t1_clean_acceptance_package.py`
- `tests/test_t1_clean_acceptance_package.py`
- updated `scripts/build_nmi_maintext_evidence_package.py`
- updated `scripts/build_non_a3_experiment_bridge.py`

| Check | Result | Notes |
| --- | --- | --- |
| Strengthens empirical baseline frontier | PASS | Builds a combined materials/visual baseline frontier with 11 method families and source SHA256 hashes. |
| Keeps materials validation scoped | PASS | A1/A2/A3 and external-source routes are recorded as unavailable, negative, diagnostic, or pending; none are promoted to positive evidence. |
| Preserves matched-volume interpretation | PASS | ALIGNN K=300/500 lead rows report raw top-R matched FTR alongside PARC and raw top-K, so the claim is fixed-budget utility rather than fixed-size ranking improvement. |
| Restricts full release certificate | PASS | Tests require only PARC rows to have full null-superset + SCS certificate properties. |
| Maintains maintext hierarchy | PASS | The maintext evidence package consumes the T1 baseline frontier as support while keeping the CTC active-audit row as the only primary headline. |
| Preserves A3 boundary | PASS | T1 closeout states A3 remains outside positive evidence unless future DFT gates are met. |

## Phase46 Local Review Addendum

Reviewed:

- `scripts/build_release_governance_paradigm_package.py`
- `tests/test_release_governance_paradigm_package.py`
- updated `scripts/build_nmi_maintext_evidence_package.py`
- updated `scripts/build_non_a3_experiment_bridge.py`

| Check | Result | Notes |
| --- | --- | --- |
| Defines route-2 positioning | PASS | The package frames the paper as release-time governance under scarce one-sided verification. |
| Preserves primary-headline discipline | PASS | Maintext tests still require exactly one primary headline: CTC active audit. |
| Binds evidence into a closure | PASS | CTC active audit, T1 empirical baseline frontier, refusal attribution, and audit uncertainty are all mapped to source artifacts and SHA256 hashes. |
| Avoids materials overclaim | PASS | Claim-map and abstract tests forbid prospective materials-discovery and independent-validation-success language. |
| Keeps synthesis separate from new evidence | PASS | The package is marked `paper_facing_synthesis_only` and adds no new materials validation evidence. |
