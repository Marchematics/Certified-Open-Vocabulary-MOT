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
