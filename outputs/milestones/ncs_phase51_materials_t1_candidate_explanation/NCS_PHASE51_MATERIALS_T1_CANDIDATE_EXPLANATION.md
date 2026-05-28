# NCS Phase51 Materials t1 Candidate-Level Explanation

Status: `completed_candidate_level_t1_explanation_v1_no_MLIP_consensus_claim`

This milestone merges the current-MP t1 hull labels with the frozen K=300/500
materials queue rows, ALIGNN-FF release scores, local CGCNN/MEGNet model-zoo
predictions, release margins, raw ranks, source-boundary tags, and near-hull
flags. It explains current-label false candidates at candidate level.

Claim boundary:

- This is a candidate-level explanation/model-zoo diagnostic.
- The `structure_hash` column in the public candidate-level alias table is a
  deterministic public-safe row hash over WBM identifiers and metadata, not a
  crystallographic structure hash.
- It is not a CHGNet/MACE consensus validation for the WBM queue, because
  candidate-level CHGNet and MACE-MP WBM queue scores are unavailable in the
  public-safe cache.
- It is not a prospective materials-discovery claim and not a strict t1
  alpha=0.10 certificate.

Recommended use in the NCS paper:

Use the figure-source CSVs to explain whether current-label failures are
near-hull, source-boundary, unresolved-current-MP-reference, or model-disagreed
cases. Do not write that two independent MLIPs validate the WBM t1 release.
