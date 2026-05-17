# Materials Prospective DFT Follow-Up Closeout

Evidence status: protocol freeze / input gate only.

This package freezes the prospective in-silico DFT follow-up design and writes
schema-complete candidate, selection, public-label exclusion, novelty, and DFT
job-manifest files. It does not contain new DFT results, does not claim
experimental synthesis, and does not promote a protocol-only positive result.

## Status Summary

| item                   | status                                   | completed_positive_result   | blocks_DFT_submission   | reason                                                                                       |
|:-----------------------|:-----------------------------------------|:----------------------------|:------------------------|:---------------------------------------------------------------------------------------------|
| protocol               | frozen                                   | False                       | False                   | protocol and failure policy are frozen before DFT outcomes                                   |
| candidate_pool         | blocked_missing_unlabeled_candidate_pool | False                       | True                    | requires unlabeled generated candidates with public-label exclusion and structure crossmatch |
| public_label_exclusion | pending_candidate_pool                   | False                       | True                    | must exclude public WBM/MP/OQMD/Alexandria/GNoME stability labels before DFT                 |
| selection_frozen       | not_started_no_candidates                | False                       | True                    | selection arms require a valid PARC release and raw-only tail before job export              |
| dft_job_manifest       | empty_until_selection_exists             | False                       | True                    | DFT jobs are exported only after nonempty frozen selection arms exist                        |
| dft_results            | not_started                              | False                       | False                   | new DFT outcomes must be collected after protocol and selection freeze                       |

## Interpretation

The current package is ready to receive an unlabeled generated crystal pool and
public database crossmatch outputs. Until those inputs exist, `selection_frozen`
and `dft_job_manifest` remain empty by design.
