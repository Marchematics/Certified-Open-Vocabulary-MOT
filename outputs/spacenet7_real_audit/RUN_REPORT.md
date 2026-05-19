# SpaceNet 7 Real-Audit Loop Report

Status: historical real-audit workspace retained for provenance. The paper-facing
pre-release evidence copy is `outputs/milestones/spacenet_real_audit_final/`.
Intermediate review-prefill sheets were removed from the tracked pre-release
repository.

## Outputs

- Calibration blind template: `outputs/spacenet7_real_audit/calibration_audit_blind_template.csv`
- Release blind template: `outputs/spacenet7_real_audit/release_audit_blind_template.csv`
- Raw top-K blind template: `outputs/spacenet7_real_audit/raw_topk_audit_blind_template.csv`
- Seed results: `table_spacenet7_real_audit_seed_results.csv`
- Summary: `table_spacenet7_real_audit_summary.csv`

## Primary preliminary status

- Non-empty seeds: 0/20
- Mean release: 0.000
- Official-GT FTR mean: 0.000000
- Raw top-M official-GT FTR mean: 0.003000

## Release-audit target

- Setting status: diagnostic_predefined_budget_after_primary_refusal
- Release-audit alpha: 0.2
- Release-audit M: 50
- Release-audit rows: 147

The pre-release claim-bearing SpaceNet tables are frozen under
`outputs/milestones/spacenet_real_audit_final/`.

## Summary Tables

- Calibration audit summary: `table_spacenet7_real_audit_calibration_summary.csv`
- Primary K=100 refusal diagnostics: `table_spacenet7_real_audit_primary_refusal_diagnostics.csv`
- K=50 diagnostic release audit: `table_spacenet7_real_audit_k50_release_audit.csv`
- Raw top-K/high-score audit: `table_spacenet7_real_audit_raw_topK_audit.csv`

For pre-release citation, use the corresponding finalized milestone tables rather
than this historical workspace.
