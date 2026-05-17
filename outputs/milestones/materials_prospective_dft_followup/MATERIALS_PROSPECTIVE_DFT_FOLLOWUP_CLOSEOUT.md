# Materials Prospective DFT Follow-Up Closeout

Evidence status: generated-candidate and public-label-exclusion gate completed; scoring/selection gate blocked.

This package freezes the prospective in-silico DFT follow-up design and now includes a public-safe PGCGM-generated candidate pool plus WBM/Matbench formula-level public-label exclusion outputs. It does not contain frozen ALIGNN-FF scores for the generated candidates, does not contain a PARC-selected follow-up set, does not contain new DFT results, does not claim experimental synthesis, and does not promote a protocol-only positive result.

## Status Summary

| item                   | status                                | completed_positive_result   | blocks_DFT_submission   | reason                                                                                                        |
|:-----------------------|:--------------------------------------|:----------------------------|:------------------------|:--------------------------------------------------------------------------------------------------------------|
| protocol               | frozen                                | False                       | False                   | protocol and failure policy are frozen before DFT outcomes                                                    |
| candidate_pool         | ready_for_public_label_filter         | False                       | False                   | PGCGM generated pool frozen public-safe with 2065 follow-up-eligible structures before public-label exclusion |
| public_label_exclusion | ready_for_alignnff_scoring            | False                       | False                   | WBM/Matbench formula-level public-label exclusion applied; frozen ALIGNN-FF scores still required             |
| selection_frozen       | blocked_missing_alignnff_scores       | False                       | True                    | selection arms require true frozen ALIGNN-FF candidate scores and a PARC release file before job export       |
| dft_job_manifest       | empty_until_nonempty_selection_exists | False                       | True                    | DFT jobs are exported only after nonempty frozen selection arms exist                                         |
| dft_results            | not_started                           | False                       | False                   | new DFT outcomes must be collected after protocol and selection freeze                                        |

## Candidate-Pool Gate

- Raw generated candidates: `3000`.
- Follow-up eligible after parsing/public-safe normalization and WBM/Matbench formula-level exclusion: `2065`.
- Public-label exclusion report rows: `3000`.
- Scope: WBM/Matbench formula-level public-label exclusion is completed for this package; MP/OQMD/Alexandria/GNoME structure-level indexes are not locally available in this milestone and are not claimed as completed evidence.

## Remaining Blocker

`selection_frozen.csv` and `dft_job_manifest.csv` remain empty by design. The next required input is a true frozen ALIGNN-FF score table for the generated candidates and a PARC release file derived from those scores. No surrogate score is used as an ALIGNN-FF score.

## Interpretation

The package has advanced beyond protocol-only freeze to a real generated-candidate gate, but it is still not a completed prospective DFT follow-up result. It blocks DFT submission until nonempty frozen selection arms exist.
