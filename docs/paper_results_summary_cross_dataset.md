# Cross-Dataset Results Summary

Updated: 2026-05-08T13:52:06

## TAO Released Unsupported Audit

TAO `alpha=0.10` PARC best-M diagnostic now has all released unsupported paths covered by audit labels. In the refreshed matrix, the best-M rows are:

```text
 seed  candidate_budget_M  released  official_supported  unsupported  unsupported_actually_true  unsupported_actually_false  unsupported_uncertain  unsupported_unlabeled      utr  conservative_ftr_uncertain_and_unlabeled_false  self_consistency_margin
    0                 100        97                  96            1                        1.0                         0.0                    0.0                    0.0 0.010309                                             0.0                 0.245214
    1                 100       100                 100            0                        0.0                         0.0                    0.0                    0.0 0.000000                                             0.0                 0.583484
    2                 100       100                  99            1                        1.0                         0.0                    0.0                    0.0 0.010000                                             0.0                 0.496466
```

## TAO alpha=0.20 Fixed M=150

```text
 seed  candidate_budget_M  released      utr  conservative_ftr_uncertain_and_unlabeled_false  self_consistency_margin
    0                 150       150 0.033333                                        0.026667                 0.883048
    1                 150       150 0.033333                                        0.026667                 0.898867
    2                 150       142 0.007042                                        0.000000                 0.016582
```

Bundle: `/home/waas/paper_experiments/outputs/milestones/ijcv_cross_dataset_v6`
