# PARC-Track Results v0

This draft fixes the current reporting protocol: fixed `M=150` is the main OVT-B scaffold protocol, tune-fallback `M=150` is reported as a protocol supplement, and best-M is diagnostic only.

## 1. Missing-GT Audit on OVT-B

We audited 246 high-score OVT-B tracklets unmatched to official annotations. After the second-pass model-assisted visual review, 184 were labeled actually true, 57 actually false, and 5 uncertain. The actually-true rate is 74.80%, and 131 tracklets (53.25%) satisfy the stricter verified-positive-for-calibration criterion.

This is the main real-data evidence for the partial-annotation premise: unmatched tracklets cannot be treated as false calibration samples.

## 2. First Non-Empty Real Certification

On the 1000-video OVT-B scaffold (996 videos with paths), PARC full with fixed `M=150` and `alpha1=0.10` released 126 certified tracklets. Of these, 116 were officially supported and 10 were unsupported, yielding `UTR=0.0794`. All unsupported released tracklets were audited: 9 were actually true, 0 false, and 1 uncertain. The audited FTR on supported-plus-labeled released tracklets is 0.0000; treating the uncertain case as false gives conservative FTR 0.0079. The selected set satisfies self-consistency with margin 0.0066.

## 3. Main Fixed-M Protocol

The current main protocol uses fixed `M=150`. This avoids test-grid hyperparameter selection and is safe to report as the current OVT-B scaffold result. At `alpha1=0.10`, the fixed-M PARC row is:

| seed | candidate_budget_M | released | utr | conservative_ftr_uncertain_and_unlabeled_false | self_consistency_margin | empty_diagnostic |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 150 | 126 | 0.07937 | 0.007937 | 0.006638 |  |
| 1 | 150 | 0 | 0 |  |  | insufficient_high_e_mass_for_uniform_scs |
| 2 | 150 | 0 | 0 |  |  | insufficient_high_e_mass_for_uniform_scs |

## 4. Tune-Fallback Protocol Supplement

The tune-M protocol is implemented, but the current 100-video outer tuning split is too small to find a feasible M internally. Therefore all PARC rows use the pre-specified fallback `M=150`. This is a valid protocol supplement but should not be described as a successful tune-selected-M result.

| seed | candidate_budget_M | released | utr | conservative_ftr_uncertain_and_unlabeled_false | self_consistency_margin | selection_protocol | selection_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 150 | 126 | 0.07937 | 0.007937 | 0.006638 | tune_fallback_M | no_feasible_M_on_tune_fallback |
| 1 | 150 | 0 | 0 |  |  | tune_fallback_M | no_feasible_M_on_tune_fallback |
| 2 | 150 | 0 | 0 |  |  | tune_fallback_M | no_feasible_M_on_tune_fallback |

## 5. Best-M Diagnostic

Best-M over the test grid is diagnostic only. It shows that at `alpha1=0.10`, seed 0 has a strong non-empty regime around `M=150`, seed 1 is non-empty at smaller M, and seed 2 remains empty in the current M grid. This supports the high-evidence-mass interpretation rather than a pipeline failure.

| seed | best_M_on_test_grid | released | utr | conservative_ftr_uncertain_and_unlabeled_false | self_consistency_margin | empty_diagnostic |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 150 | 126 | 0.07937 | 0.007937 | 0.006638 |  |
| 1 | 75 | 39 | 0.02564 | 0 | 1.177 |  |
| 2 | 75 | 0 | 0 |  |  | insufficient_high_e_mass_for_uniform_scs |

## 6. Expanded Baselines

The expanded baseline table uses a unified schema. Diagnostic baselines without a certificate, such as confidence threshold and greedy score, release many tracks but have high conservative false rates under the current audit coverage. The unmatched-as-false block baseline remains empty at the main fixed-M operating point.

| method | released | utr | conservative_ftr | margin | nonempty_rate |
| --- | --- | --- | --- | --- | --- |
| confidence_threshold | 150 ± 0 | 0.04444 ± 0.03289 | 0.9578 ± 0.03791 |  | 1 |
| greedy_score_no_risk | 150 ± 0 | 0.04444 ± 0.03289 | 0.9578 ± 0.03791 |  | 1 |
| null_superset_no_audit | 42 ± 72.75 | 0.02646 ± 0.04582 | 0.007937 ± 0 | 0.3799 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 42 ± 72.75 | 0.02646 ± 0.04582 | 0.007937 ± 0 | 0.006638 ± 0 | 0.333 |
| post_filter_e_bh | 42 ± 72.75 | 0.02646 ± 0.04582 | 0.9286 ± 0 | 0.006638 ± 0 | 0.333 |
| tracklet_e_bh | 42 ± 72.75 | 0.02646 ± 0.04582 | 0.9286 ± 0 | 0.1472 ± 0 | 0.333 |
| tracklet_p_bh | 150 ± 0 | 0.04444 ± 0.03289 | 0.9578 ± 0.03791 |  | 1 |
| unmatched_as_false_block | 0 ± 0 | 0 ± 0 |  |  | 0 |

## 7. Alpha Sweep

The alpha sweep supports a finite-sample power frontier: `alpha1=0.20` is non-empty across all seeds, `alpha1=0.10` is partially non-empty, and `alpha1=0.05` is much more conservative. Full mean/std rows are in `table_alpha_sweep_meanstd.csv`.

| method | alpha1 | candidate_budget_M | released | utr | conservative_ftr | margin | nonempty_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| null_superset_no_audit | 0.05 | 75 | 25 ± 43.3 | 0.01778 ± 0.03079 | 0 ± 0 | 1.824 ± 0 | 0.333 |
| null_superset_no_audit | 0.05 | 100 | 33.33 ± 57.74 | 0.02667 ± 0.04619 | 0 ± 0 | 1.824 ± 0 | 0.333 |
| null_superset_no_audit | 0.05 | 125 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| null_superset_no_audit | 0.05 | 150 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| null_superset_no_audit | 0.05 | 175 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| null_superset_no_audit | 0.05 | 200 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| null_superset_no_audit | 0.05 | 250 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| null_superset_no_audit | 0.1 | 75 | 38 ± 37.51 | 0.02632 ± 0.02667 | 0 ± 0 | 6.842 ± 7.045 | 0.667 |
| null_superset_no_audit | 0.1 | 100 | 33.33 ± 57.74 | 0.02667 ± 0.04619 | 0 ± 0 | 11.82 ± 0 | 0.333 |
| null_superset_no_audit | 0.1 | 125 | 41.67 ± 72.17 | 0.02667 ± 0.04619 | 0.008 ± 0 | 2.285 ± 0 | 0.333 |
| null_superset_no_audit | 0.1 | 150 | 42 ± 72.75 | 0.02646 ± 0.04582 | 0.007937 ± 0 | 0.3799 ± 0 | 0.333 |
| null_superset_no_audit | 0.1 | 175 | 35.33 ± 61.2 | 0.02516 ± 0.04357 | 0 ± 0 | 5.314 ± 0 | 0.333 |
| null_superset_no_audit | 0.1 | 200 | 35.33 ± 61.2 | 0.02516 ± 0.04357 | 0 ± 0 | 2.956 ± 0 | 0.333 |
| null_superset_no_audit | 0.1 | 250 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| null_superset_no_audit | 0.2 | 75 | 75 ± 0 | 0.02667 ± 0.02667 | 0 ± 0 | 7.359 ± 8.243 | 1 |
| null_superset_no_audit | 0.2 | 100 | 100 ± 0 | 0.04333 ± 0.04041 | 0 ± 0 | 6.759 ± 8.717 | 1 |
| null_superset_no_audit | 0.2 | 125 | 116.7 ± 14.43 | 0.048 ± 0.04233 | 0.008 ± 0.008 | 2.786 ± 3.896 | 1 |
| null_superset_no_audit | 0.2 | 150 | 100 ± 86.6 | 0.04222 ± 0.03672 | 0.01333 ± 0.009428 | 2.171 ± 2.271 | 0.667 |
| null_superset_no_audit | 0.2 | 175 | 111 ± 96.5 | 0.03994 ± 0.03471 | 0.01521 ± 0.005345 | 0.9712 ± 1.335 | 0.667 |
| null_superset_no_audit | 0.2 | 200 | 66.67 ± 115.5 | 0.01833 ± 0.03175 | 0.01 ± 0 | 1.915 ± 0 | 0.333 |
| null_superset_no_audit | 0.2 | 250 | 83.33 ± 144.3 | 0.01867 ± 0.03233 | 0.02 ± 0 | 0.7472 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.05 | 75 | 25 ± 43.3 | 0.01778 ± 0.03079 | 0 ± 0 | 1.144 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.05 | 100 | 33.33 ± 57.74 | 0.02667 ± 0.04619 | 0 ± 0 | 1.144 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.05 | 125 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| parc_track_gamma_tuned_uniform_scs | 0.05 | 150 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| parc_track_gamma_tuned_uniform_scs | 0.05 | 175 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| parc_track_gamma_tuned_uniform_scs | 0.05 | 200 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| parc_track_gamma_tuned_uniform_scs | 0.05 | 250 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| parc_track_gamma_tuned_uniform_scs | 0.1 | 75 | 38 ± 37.51 | 0.02632 ± 0.02667 | 0 ± 0 | 6.161 ± 7.048 | 0.667 |
| parc_track_gamma_tuned_uniform_scs | 0.1 | 100 | 33.33 ± 57.74 | 0.02667 ± 0.04619 | 0 ± 0 | 11.14 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.1 | 125 | 41.67 ± 72.17 | 0.02667 ± 0.04619 | 0.008 ± 0 | 1.911 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.1 | 150 | 42 ± 72.75 | 0.02646 ± 0.04582 | 0.007937 ± 0 | 0.006638 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.1 | 175 | 35.33 ± 61.2 | 0.02516 ± 0.04357 | 0 ± 0 | 4.635 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.1 | 200 | 35.33 ± 61.2 | 0.02516 ± 0.04357 | 0 ± 0 | 2.276 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.1 | 250 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| parc_track_gamma_tuned_uniform_scs | 0.2 | 75 | 75 ± 0 | 0.02667 ± 0.02667 | 0 ± 0 | 6.986 ± 7.974 | 1 |
| parc_track_gamma_tuned_uniform_scs | 0.2 | 100 | 100 ± 0 | 0.04333 ± 0.04041 | 0 ± 0 | 6.405 ± 8.434 | 1 |
| parc_track_gamma_tuned_uniform_scs | 0.2 | 125 | 116.7 ± 14.43 | 0.048 ± 0.04233 | 0.008 ± 0.008 | 2.547 ± 3.78 | 1 |
| parc_track_gamma_tuned_uniform_scs | 0.2 | 150 | 100 ± 86.6 | 0.04222 ± 0.03672 | 0.01333 ± 0.009428 | 1.955 ± 2.206 | 0.667 |
| parc_track_gamma_tuned_uniform_scs | 0.2 | 175 | 58.33 ± 101 | 0.02095 ± 0.03629 | 0.01143 ± 0 | 1.71 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.2 | 200 | 66.67 ± 115.5 | 0.01833 ± 0.03175 | 0.01 ± 0 | 1.71 ± 0 | 0.333 |
| parc_track_gamma_tuned_uniform_scs | 0.2 | 250 | 83.33 ± 144.3 | 0.01867 ± 0.03233 | 0.02 ± 0 | 0.5783 ± 0 | 0.333 |
| unmatched_as_false_block | 0.05 | 75 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.05 | 100 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.05 | 125 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.05 | 150 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.05 | 175 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.05 | 200 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.05 | 250 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.1 | 75 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.1 | 100 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.1 | 125 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.1 | 150 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.1 | 175 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.1 | 200 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.1 | 250 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.2 | 75 | 50 ± 43.3 | 0.02667 ± 0.02667 | 0 ± 0 | 2.291 ± 2.861 | 0.667 |
| unmatched_as_false_block | 0.2 | 100 | 33.33 ± 57.74 | 0.02667 ± 0.04619 | 0 ± 0 | 4.314 ± 0 | 0.333 |
| unmatched_as_false_block | 0.2 | 125 | 41.67 ± 72.17 | 0.02667 ± 0.04619 | 0.008 ± 0 | 1.586 ± 0 | 0.333 |
| unmatched_as_false_block | 0.2 | 150 | 50 ± 86.6 | 0.02222 ± 0.03849 | 0.006667 ± 0 | 0.3774 ± 0 | 0.333 |
| unmatched_as_false_block | 0.2 | 175 | 35.33 ± 61.2 | 0.02516 ± 0.04357 | 0 ± 0 | 1.059 ± 0 | 0.333 |
| unmatched_as_false_block | 0.2 | 200 | 0 ± 0 | 0 ± 0 |  |  | 0 |
| unmatched_as_false_block | 0.2 | 250 | 0 ± 0 | 0 ± 0 |  |  | 0 |

## 8. Second Dataset Status

TAO/OV-TAO has been started via official data acquisition. The full annotation archive was downloaded from the official TAO GitHub annotation release, and the original train/validation JSONs now exist under `./data/TAO/annotations/`. The current full-train adapter report is annotation-complete but frame-incomplete, because full TAO frames are distributed through gated HuggingFace access or source-dataset downloads.

To verify the second-dataset adapter path without claiming a full TAO benchmark result, we created a one-video TAO AVA mini subset using a real public AVA movie from the TAO annotations. This mini subset now passes strict tracking-layout inspection:

| Dataset | Status | Videos | Frames | Tracks | Boxes | Categories |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| TAO AVA mini | tracking_layout_ok | 1 | 40 | 6 | 201 | 2 |

Artifacts:

- Download report: `./outputs/phase3_tao/tao_download_report.json`
- Mini adapter report: `./outputs/phase3_tao/dataset_adapter_report_tao_ava_mini.json`

No full TAO audit or certification claim is made yet. The next TAO step is to obtain a larger frame subset through accepted HuggingFace access or source-dataset downloads, then run the same missing-GT audit/certification scaffold.

## 9. IDSW Status

The CLEAR-MOT IDSW evaluator entry is implemented and unit-tested, but real `clear_mot_events.csv` has not yet been generated. IDSW should remain pending in the main results until real evaluator events are available.

## 10. Bundle Metadata

TPAMI-core v2 manifest: `contains_tuned_m_main_result=True`, `tuned_m_has_fallbacks=True`. Because fallback is used, the fixed-M table remains the safest main table for the current draft.
