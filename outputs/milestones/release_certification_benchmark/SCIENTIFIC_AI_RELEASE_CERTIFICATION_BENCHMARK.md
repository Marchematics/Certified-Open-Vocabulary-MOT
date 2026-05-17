# Scientific AI Release Certification Benchmark

Evidence status: completed benchmark-card package.

This milestone packages completed PARC evidence into a reusable release-governance protocol. It does not add new experiments, human labels, or protocol-only positive rows. Each card identifies a frozen candidate source, one-sided verification source, block definition, requested risk/budget, release/refusal decision, evaluation source, and required limitation language.

Summary:
- Tracks: 5
- Release cards: 9
- Strict-risk cards: 6
- Human-confirmed cards: 2
- Refusal or downstream-guardrail cards: 5

Primary files:
- `table_release_certification_cards.csv`
- `table_release_certification_track_registry.csv`
- `table_release_card_field_schema.csv`
- `table_release_governance_checklist.csv`
- `table_release_certification_benchmark_index.csv`
- `figure_release_certification_benchmark_map.csv`
- `figure_release_certification_benchmark_map.pdf`

Use:
1. Select a track with a matching release unit.
2. Follow the governance checklist before inspecting held-out labels.
3. Fill the release-card fields for the new candidate universe.
4. Mark evidence as completed only after the release/refusal decision and evaluation are both finished.

Scope boundaries:
- CTC link cards certify candidate links, not an end-to-end tracker.
- Materials cards are public-label computational replay, not new DFT or synthesis.
- iWildCam is an operational alpha=0.20 card, not a strict alpha=0.10 success.
- SpaceNet and CTC downstream consequence cards report artifact proxies, not official leaderboard scores.
