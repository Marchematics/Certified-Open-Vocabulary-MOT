# Materials t0/t1 Snapshot Acquisition

Status: `completed_t0_t1_hull_shift_acquisition_current_MP_api`

This milestone acquires a t0/t1 hull-shift snapshot for the frozen WBM queue
candidates used in the K=300/500 materials release-policy rows.

- t0 source: local Matbench Discovery/WBM summary with MP v2022.10.28 hull
  labels.
- t1 source: Materials Project API database version `2025.09.25` with
  thermo type `GGA_GGA+U`.
- Target candidates: 1191 unique WBM candidates across
  774 chemical systems.

The t1 labels are recomputed by converting each WBM candidate's frozen
MP2020-corrected formation energy back to a total energy using the current MP
element references, then placing the candidate on the current MP phase diagram
for its chemical system. This is a hull-shift audit and not a new DFT
calculation. It is not a prospective materials-discovery result. It does not
use or disclose the MP API key.

Lead t1-hull utility diagnostics:

  K  PARC_FTR_t1_current_mp  raw_topK_FTR_t1_current_mp  raw_minus_PARC_FTR_t1  PARC_stable_to_unstable_rate  raw_stable_to_unstable_rate  drift_rate_delta_PARC_minus_raw
300                0.315789                    0.422254               0.106464                      0.184211                     0.212553                        -0.028343
500                0.310185                    0.486986               0.176801                      0.203704                     0.221662                        -0.017959

Gate assessment:

                                                    gate                                         status                                                                            lead_metric                                                                        claim
                      t0_t1_current_MP_snapshot_acquired                                           PASS                            1191 WBM queue candidates joined to current MP hull entries                         completed current-MP hull-shift snapshot acquisition
                 PARC_release_lower_t1_FTR_than_raw_topK                                           PASS                   K=300 raw_minus_PARC_FTR=0.106464; K=500 raw_minus_PARC_FTR=0.176801               PARC release has lower conservative t1-hull FTR than raw top-K
       stable_to_unstable_drift_not_concentrated_in_PARC                                           PASS K=300 drift_delta_PARC_minus_raw=-0.028343; K=500 drift_delta_PARC_minus_raw=-0.017959      stable-to-unstable hull drift is not more concentrated in PARC releases
                     strict_alpha010_t1_hull_certificate                                           FAIL                                 K=300 PARC_FTR_t1=0.315789; K=500 PARC_FTR_t1=0.310185         not a strict alpha=0.10 temporal certificate unless this gate passes
unresolved_current_MP_hull_labels_tracked_conservatively                                           PASS                         64 unresolved arm-level rows counted as false in FTR summaries   current-MP missing-reference cases are explicit and conservatively counted
                          overall_t0_t1_hull_shift_audit PASS_UTILITY_DRIFT_NO_STRICT_ALPHA_CERTIFICATE                  utility and drift gates are separated from the alpha-certificate gate completed hull-shift utility diagnostic; not prospective materials discovery
