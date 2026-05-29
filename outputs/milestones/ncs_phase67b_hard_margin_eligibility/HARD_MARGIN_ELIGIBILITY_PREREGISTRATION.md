# Phase67b Hard-Margin Eligibility Preregistration

Status: executed as a versioned release-card design diagnostic on frozen t0/t1
queue artifacts. This is not prospective materials discovery and not DFT
evidence.

## Frozen inputs

- Candidate universe: Phase51 frozen K=500 WBM queue union.
- Candidate universe hash: `2f493f4e5551a963d5f3936774cc994769f755a378a1659aff1ff81a94adb1f0`.
- Alpha: `0.10`.
- Seeds: `0..19`.
- K grid: `[10, 15, 20, 25, 50, 75, 100, 150, 200, 300, 500]`.
- Margin grid eV/atom: `[0.0, 0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.3, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]`.

## Eligibility and validity event

For margin `m`, a candidate can enter the release pool only if
`e_above_hull,t0 <= -m`.  The certified t0 event is the same margin-stability
event.  Current-MP t1 labels are used only for post-release survival audit.

## Selection rule

Eligible candidates are ranked by t0 margin and then filtered by the PARC SCS
e-value rule.  The rule explicitly uses t0 hull margin as eligibility metadata;
it is therefore a durability design diagnostic, not a hidden-label discovery
benchmark.
