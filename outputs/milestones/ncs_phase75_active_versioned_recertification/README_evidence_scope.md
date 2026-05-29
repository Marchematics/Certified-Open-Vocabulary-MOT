# Phase75 Active Versioned Recertification

Status: `completed_active_recertification_no_go`.

Phase75 tests whether targeted calibration-side current-MP t1 one-sided
support can restore a non-empty self-consistent versioned release after passive
Phase74 recertification refuses.

No active t1 recertification policy passes the GO-medium or GO-strong gate on the frozen grid.

Scope and guardrails:

- t1 public labels are used only to emulate calibration-side one-sided support;
- test-side t1 labels are used only after SCS release to evaluate FTR;
- each policy is frozen before release and never reads held-out t1 labels;
- null-superset denominators and e-values are recomputed after audit;
- random transition controls are included for every K/support/budget row;
- no DFT evidence;
- no prospective materials discovery.
