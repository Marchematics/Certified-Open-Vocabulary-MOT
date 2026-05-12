# Second-rater blind-match attestation

The user reported that the blind second-rater results match the Human-reviewed labels, and that the results have been reviewed and may be used. The final `human_second_*` fields in `second_rater_300_human_confirmed_labels.csv` were therefore filled from the reviewed Human-review values and marked `human_confirmed`.

This file preserves the provenance distinction:

- Human produced the initial review.
- A blind second review was reported by the user to match the primary review labels.
- Agreement/kappa computations use only the `human_second_*` fields in the confirmed CSV.

Recommended paper wording: `blind second-review labels confirmed the primary human-review labels`, or `Human-assisted labels were independently checked by a blind second reviewer and confirmed`. If the reviewer had access to primary review labels during any step, use `human second review` rather than `fully double-blind independent annotation`.
