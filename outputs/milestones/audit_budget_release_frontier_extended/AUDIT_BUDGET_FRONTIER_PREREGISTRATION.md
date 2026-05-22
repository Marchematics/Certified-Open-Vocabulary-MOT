# Audit Budget Release Frontier Preregistration

Status: frozen before inspecting the simulated-audit results table for manuscript claims.

This milestone tests how much one-sided verification is needed to move a frozen candidate universe from refusal to certified release. The experiment is a simulated audit over existing held-out labels; it introduces no new human labels, no new DFT, and no prospective materials discovery claim.

## Frozen Grid

- Audit policies: random, top_score
- Audit budget fractions of calibration candidates inspected: 0.0, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0
- Seeds: 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19
- Primary alpha: 0.10
- Candidate rows: CTC learned K=100/300; materials CGCNN K=100; materials ALIGNN-FF K=300/500.

Hidden full labels are used only to simulate whether an inspected item becomes a verified positive and to evaluate post-release FTR. Unverified items are never treated as negative labels.
