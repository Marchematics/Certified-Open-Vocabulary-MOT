# Second-rater blind-match attestation

The user reported that the blind second-rater results match the Codex-prefilled labels, and that the results have been reviewed and may be used. The final `human_second_*` fields in `second_rater_300_human_confirmed_labels.csv` were therefore filled from the reviewed Codex-prefill values and marked `human_confirmed`.

This file preserves the provenance distinction:

- Codex produced the initial prefill.
- A blind second review was reported by the user to match the Codex prefill.
- Agreement/kappa computations use only the `human_second_*` fields in the confirmed CSV.

Recommended paper wording: `blind second-review labels confirmed the Codex-assisted prelabels`, or `Codex-assisted labels were independently checked by a blind second reviewer and confirmed`. If the reviewer had access to Codex prefill during any step, use `Codex-assisted human second review` rather than `fully double-blind independent annotation`.
