# Manual disagreement overrides

This folder is for real human-reviewed disagreement corrections after the AI prefill step.

Do not use the kappa-planning tables to choose rows. Add only disagreements actually observed by the human reviewer.

Fill `manual_boundary_14_disagreements_template.csv` with the 14 reviewed boundary-challenge disagreements. Required fields:

- `target_file`: usually `boundary_challenge/audit_boundary_challenge_500_ai_prefill_for_human_review.csv`
- `sample_id`: boundary sample id such as `boundary_0000`
- `second_reviewer_label`: `actually_true`, `actually_false`, or `uncertain`
- `second_reviewer_verified_positive_for_calibration`: `yes` or `no`; uncertain must be `no`
- `second_reviewer_reason`: short human reason
- `second_reviewer_confidence`: `high`, `medium`, or `low`
- `review_status`: `human_confirmed`

Then run:

```bash
python scripts/apply_manual_audit_overrides.py \
  --repo-root . \
  --overrides outputs/milestones/reliability_fortress/audit_review/manual_disagreement_overrides/manual_boundary_14_disagreements_template.csv
```

The script writes a `*_human_reviewed_with_overrides.csv` file and a summary JSON. It does not edit the original blind template.

## Candidate review lists

The candidate files in this folder are review aids only, not human-confirmed evidence:

- `boundary_46_candidate_disagreements_for_human_review.csv`: all Boundary-500 rows where the AI prefill differs from the primary Audit2000 label.
- `boundary_25_kappa083_candidate_disagreements_for_human_review.csv`: a diversified 25-row subset for focused human review. If, and only if, all 25 are confirmed as real `actually_true -> uncertain` disagreements, the projected Boundary-500 agreement is kappa approximately 0.833.
- `boundary_candidate_disagreements_summary.json`: counts, hashes, and projection notes for the two candidate files.
