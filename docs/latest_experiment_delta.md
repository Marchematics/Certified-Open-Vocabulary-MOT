# Latest Experiment Delta

This repository snapshot is synchronized with the local post-Phase-4 writing bundle:

- Package: `/home/waas/paper_experiments/outputs/packages/parc_track_post_phase4_delta_for_writing_20260510_013544.tar.gz`
- SHA256: `04ead85d895d274404c006ef8adad9473058a594c04700e7d7cee7dfcb14391f`
- Anchor package: `outputs/packages/phase4_third_generator_delta_from_ijcv_extra_cpu_v1_20260509_160838.tar.gz`

The bundle includes derived CSV/JSON/figures/tables and milestone summaries created after the anchor.
It intentionally excludes raw datasets, raw annotations, model weights, HF/GroundingDINO caches,
viewer montages/clips, sharded intermediate duplicate candidates, and compiled extensions.

Key late-stage milestones included in this Git snapshot:

- `outputs/milestones/ijcv_stability_v1`
- `outputs/milestones/ijcv_stability_v2`
- `outputs/milestones/ijcv_burst_v2`
- `outputs/milestones/ijcv_burst_owlv2_stress_v1`

BURST summary:

- GroundingDINO BURST audit-200: `168 actually_true / 6 actually_false / 26 uncertain`
- BURST released-unsupported audit coverage: all released unsupported paths audited, audited FTR `0.0`
- BURST GroundingDINO Prop.5 mass-ratio validation: `6/6` correct
- BURST GroundingDINO + OWLv2 cross-generator Prop.5 validation: `12/12` correct
- BURST OWLv2 is retained as stress/failure analysis, not the primary positive result.
