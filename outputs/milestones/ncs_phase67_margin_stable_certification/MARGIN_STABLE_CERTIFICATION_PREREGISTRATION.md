# Phase67 Margin-Stable Certification Preregistration

Status: executed as a versioned release-card diagnostic on already frozen
t0/t1 queue artifacts.  This is not prospective materials discovery and not DFT
evidence.

## Frozen inputs

- Candidate universe: Phase51 frozen K=500 WBM queue union.
- Candidate universe hash: `2f493f4e5551a963d5f3936774cc994769f755a378a1659aff1ff81a94adb1f0`.
- t0 reference: WBM/Matbench t0 hull labels already present in Phase51 table.
- t1 reference: current-MP labels already present in Phase51 table; used only
  for post-release survival audit.
- Blocks: chemical system / composition-family proxy via `chemical_system`.
- Alpha: `0.10`.
- Seeds: `0..19`.
- K grid: `[10, 15, 20, 25, 50, 75, 100, 150, 200, 300, 500]`.
- Margin grid eV/atom: `[0.0, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]`.

## Validity event

For margin `m`, the certified t0 event is:

`Y_m(t0) = 1[e_above_hull,t0 <= -m]`.

The t1 survival audit uses the ordinary current-MP stability event
`e_above_hull,t1 <= 0`.

## Selection rule

Candidates are ranked by t0 margin (`-e_above_hull,t0`) and then filtered by
the PARC SCS e-value rule.  Raw model score is not used for Phase67 ranking.

## Success gate

A row is a constructive margin-stable t1-survival positive only if:

- non-empty release in at least `18/20` seeds;
- t1 FTR <= alpha in at least `18/20` non-empty seeds;
- mean t1 FTR among non-empty releases <= alpha.

All K and margin rows are reported; no row is selected by post-release t1 FTR.
