# Materials Queue Source-Uncertainty Overlay

Status: completed candidate-level diagnostic. This milestone reconstructs the ALIGNN-FF alpha=0.10, rho=0.10, K=300/500 materials queues and joins them to the alex-mp A2 candidate-match table.

Claim boundary: diagnostic only. The alex-mp rows are a source-discordance stress test, not positive independent validation and not prospective materials discovery. Formula-only matches are retained as tags but excluded from alex-mp FTR and discordance denominators.

Lead diagnostic contrasts:
- K=300: PARC WBM FTR 0.087 vs raw WBM FTR 0.253; PARC alex exact-match FTR 0.745 vs raw alex exact-match FTR 0.734. Exact-match coverage is 0.245 for PARC and 0.359 for raw.
- K=500: PARC WBM FTR 0.048 vs raw WBM FTR 0.327; PARC alex exact-match FTR 0.741 vs raw alex exact-match FTR 0.735. Exact-match coverage is 0.232 for PARC and 0.273 for raw.

Source hashes:
- wbm_summary_sha256: ff19e59d74115de9762fbc868c9f35900ae099c18f23e9c89d10589af1418225
- cgcnn_predictions_sha256: 9fba78430e76e7443436d143d2af9ad1d7e54ef84e73443abe9058e41e4d7ebb
- alignn_predictions_sha256: dc75be97f3bce3ce724680065abf11a19bdc6a3928fdd77ccb42d3f62a02e593
- alex_mp_candidate_matches_sha256: ce98ae0937be9d108a20b33e9d82fbc6a7a0eeeafc003def81a729a073543b96
- alex_mp_candidate_matches_artifact: outputs/milestones/materials_alex_mp_a1_a2_validation/table_alex_mp_a2_candidate_matches.csv
- alpha: 0.1
- rho: 0.1
- budgets: [300, 500]
- seeds: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]
- status: completed_candidate_level_source_uncertainty_diagnostic
