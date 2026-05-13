# AI-assisted audit prefill files

These files are convenience drafts for human review only. They copy the existing Audit2000 human-reviewed labels into the second-review columns so the user can audit, overwrite, and then explicitly mark rows as `human_confirmed` after real review.

They are **not** independent blind review results, not paper-facing kappa evidence, and not human-confirmed labels. The original blind templates remain unchanged.

Generated files:

- `boundary_challenge/audit_boundary_challenge_500_ai_prefill_for_human_review.csv`
- `audit2000_reannotation/audit2000_blind_reannotation_ai_prefill_for_human_review.csv`

`review_status` is intentionally set to `ai_prefill_pending_human_confirmation` rather than `human_confirmed`.
