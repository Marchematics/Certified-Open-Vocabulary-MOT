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
