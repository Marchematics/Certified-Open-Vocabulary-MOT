# Handoff: PARC Paper Bootstrap / Paper Workflow

**Repo:** `/home/waas/paper_experiments/github/Certified-Open-Vocabulary-MOT`
**Current branch:** `main`
**Latest pushed commit:** `1304acf phase46: add release governance positioning package`
**Focus for next session:** continue paper-facing bootstrap/submission workflow from the now-frozen route-2 positioning: release-time governance under scarce one-sided verification.

## Current Paper Positioning

The manuscript should now be framed as:

> A release-governance paper for scientific AI candidate pipelines, with CTC active verification as the primary strict anchor and materials as a retrospective public-label release-policy frontier.

Do **not** frame the paper as prospective materials discovery. The current clean route is:

1. **Problem paradigm:** release-time governance for frozen finite candidate universes under scarce one-sided verification.
2. **Primary strict headline:** CTC active audit, K=100, alpha=0.10.
3. **Clean-acceptance support:** T1 empirical baseline frontier.
4. **Governance closure:** refusal attribution + audit uncertainty.
5. **Boundary honesty:** materials independent/prospective validation remains no-go/diagnostic; A3 is outside positive evidence.

## Key Completed Commits

- `1304acf` — phase46 release-governance positioning package.
- `2a003bd` — phase45 T1 clean-acceptance baseline frontier.
- `81a7b57` — phase44 active-audit strong-positive gate.
- `550e8e7` — phase43 NMI maintext evidence package.

These are already pushed to `origin/main`.

## Most Important Artifacts

Use these instead of reconstructing the conversation:

- `outputs/milestones/release_governance_problem_paradigm/`
  - `release_governance_abstract_v2.md`
  - `release_governance_maintext_skeleton.md`
  - `table_release_governance_claim_evidence_map.csv`
  - `table_release_governance_figure_blueprint.csv`
- `outputs/milestones/t1_clean_acceptance_package/`
  - T1 baseline frontier and materials validation no-go ledger.
- `outputs/milestones/audit_budget_frontier_strong_positive/`
  - CTC K=100 strong-positive active-audit package.
- `outputs/milestones/nmi_maintext_evidence_package/`
  - Exact claim sentences and figure source rows.
- `refine-logs/EXPERIMENT_RESULTS.md`
  - M8-M14 execution summaries.
- `refine-logs/EXPERIMENT_CODE_REVIEW.md`
  - Local review addenda through phase46.

## Current Evidence Hierarchy

Primary headline:

- `active_audit_ctc_strong_positive`
  - 0.5% top-score audit.
  - 20/20 safe CTC K=100 seeds.
  - 2000 releases, 0 false releases.
  - matched-budget random releases 0/20 seeds.
  - full random audit is 200x larger in the frozen grid.

Clean-acceptance / baseline frontier support:

- `t1_clean_acceptance_package`
  - 11 empirical method families.
  - ALIGNN K=300: raw top-K FTR 0.253; PARC 0.087; raw top-R 0.087; 64.25 unstable follow-ups prevented.
  - ALIGNN K=500: raw top-K FTR 0.327; PARC 0.048; raw top-R 0.048; 158.30 unstable follow-ups prevented.
  - Materials validation ledger: 5/5 independent/prospective routes are not positive evidence.

Boundary / support:

- human-audit uncertainty intervals.
- refusal feasibility attribution.
- materials source-discordance diagnostics.
- contamination sensitivity diagnostics.

## Hard Claim Boundaries

The next agent must preserve these:

- A3 is not positive evidence.
- Do not claim prospective materials discovery.
- OQMD / alex-mp / MP-Alex are diagnostics or stress tests, not positive independent validation.
- Nonzero contamination rows are assumption-violation diagnostics, not formal guarantees.
- External blind audit packet remains pending labels/adjudication unless new labels are actually returned.
- CTC K=100 active audit is the only primary strict headline.
- CTC K=300 is support-only.
- Materials rows are retrospective public-label release-policy / baseline-frontier evidence.

## Current Dirty Worktree

As of this handoff, `git status --short` shows unrelated/uncommitted items:

- Modified root/public docs:
  - `MANIFEST_SHA256.txt`
  - `Makefile`
  - `README.md`
  - `REPRODUCIBILITY.md`
  - `docs/claim_table.md`
  - `outputs/artifact_index.csv`
- Untracked A3/QE preview/formal-policy items:
  - `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/A3_FORMAL_QE_POLICY_CURRENT_SNAPSHOT/`
  - `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/A3_PREVIEW_20_NOT_FOR_CLAIMS/`
  - `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/A3_PREVIEW_CURRENT_NOT_FOR_CLAIMS/`
  - `outputs/milestones/mattergen_parc_prospective_dft_followup/A3_QE_LOCAL_RUN/resume_qe_watchdog.sh`
  - `scripts/build_a3_qe_formal_policy_snapshot.py`
  - `scripts/build_a3_qe_preview.py`

Do not stage or commit these unless the user explicitly asks to regularize the repo or freeze A3/QE snapshots.

## Recommended Next Workflow

For “Paper Bootstrap Paper Workflow”, recommended sequence:

1. Use `research-paper-writing` to turn `release_governance_maintext_skeleton.md` into paper sections.
2. Use `paper-claim-audit` after drafting to verify every abstract/introduction/results claim against source CSVs.
3. Use `paper-figure` or `figure-spec` to generate:
   - Fig. 1 release-governance paradigm.
   - Fig. 2 CTC active-audit primary headline.
   - Fig. 3 T1 empirical baseline frontier.
   - Extended Data: refusal attribution + audit intervals + assumption diagnostics.
4. Use `paper-compile` if/when LaTeX is available.
5. Use `auto-paper-improvement-loop` only after the draft and figures exist; do not let it add unsupported claims.

Suggested skills:

- `research-paper-writing`
- `paper-claim-audit`
- `paper-figure`
- `figure-spec`
- `paper-compile`
- `auto-paper-improvement-loop`

## Verification Commands Already Passing

Latest full test pass before this handoff:

```bash
pytest -q tests
# 257 passed, 4 pandas FutureWarning
```

Manifest checks passed for:

```bash
outputs/milestones/release_governance_problem_paradigm/
outputs/milestones/nmi_maintext_evidence_package/
outputs/milestones/non_a3_experiment_bridge/
```

## Best Immediate Next Task

Draft the actual paper narrative from phase46:

- Abstract: start from `outputs/milestones/release_governance_problem_paradigm/release_governance_abstract_v2.md`.
- Introduction: define “publication/release as the statistical object.”
- Results:
  1. CTC active audit as strict headline.
  2. T1 empirical baseline frontier.
  3. Materials retrospective release-policy frontier with explicit no-go validation boundary.
  4. Refusal attribution and audit uncertainty.
- Discussion: explain why refusal is a scientific governance output, not a hidden failure.

Keep the current NMI score target honest: phase45/46 make the package close to clean submission. Getting to 8+/10 now depends on either real independent/prospective materials validation or a very clear release-governance problem paradigm; the repo is now set up for the latter.
