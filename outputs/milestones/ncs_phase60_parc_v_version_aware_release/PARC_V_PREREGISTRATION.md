# PARC-V Support-Gate Preregistration

Status: frozen feasibility audit after Phase53 score generation and before any
new DFT recomputation.

Objective: test whether a frozen CHGNet/MACE score-support gate can create a
headline-capable version-aware release subset from the original t0 PARC
materials release.

Construction rules:

1. The candidate universe is the frozen WBM K=300/500 queue used in Phase50-53.
2. The primary PARC-V candidate is the original PARC release intersected with
   CHGNet/MACE consensus score support.
3. Secondary score tiers rank only the original PARC release by frozen
   CHGNet/MACE support score; t1 labels are not used for construction.
4. Current-MP t1 labels are used only for evaluation.
5. This milestone is not a full theorem-grade SCS rerun and cannot be cited as
   a new alpha certificate, DFT result, or prospective discovery.

Empirical headline gate:

- non-empty support-gated release;
- t1 FTR <= 0.15, preferably <= alpha=0.10;
- material improvement over original PARC t1 FTR by at least 0.05;
- release size not trivial.
