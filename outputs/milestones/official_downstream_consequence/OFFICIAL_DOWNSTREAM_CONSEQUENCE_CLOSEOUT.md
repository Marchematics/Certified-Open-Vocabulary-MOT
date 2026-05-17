# Official Downstream Consequence Closeout

Evidence status: completed official-GT downstream consequence diagnostics.

Scope:
- No new human labels are introduced.
- CTC uses official/held-out lineage identities to compute link-level lineage consequences.
- SpaceNet 7 uses official building identities to compute map-level persistence consequences.
- CTC TRA/AOGM values are edge-edit burden proxies, not official challenge leaderboard scores.
- SpaceNet map metrics are link-derived persistence artifacts, not a new geospatial challenge score.

Headline results:
- CTC noisy high-volume K=5000 raw queue inserts 2907.5 false lineage edges per seed and 5888.9 edge-edit burden proxy units; PARC refuses and prevents 2907.5 false lineage edges per seed.
- SpaceNet identity-preserving random-score K=5000 raw queue inserts 3398.9 false persistence links per seed and 6796.1 map-edit burden proxy units; PARC prevents 3398.9 false persistence links per seed.

Paper-facing interpretation:
PARC changes the downstream scientific artifact: a cell-lineage graph or a building-persistence map. These diagnostics do not claim improved upstream prediction. They quantify which raw candidate edges are kept out of downstream artifacts when release evidence is insufficient.

Primary artifacts:
- `table_ctc_official_lineage_metric_summary.csv`
- `table_spacenet_map_metric_summary.csv`
- `table_official_downstream_consequence_summary.csv`
- `figure_official_downstream_consequence.csv`
- `figure_official_downstream_consequence.pdf`
