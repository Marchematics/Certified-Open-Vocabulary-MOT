# A3-v4 MatterGen--PARC Prospective DFT Follow-up Protocol

This milestone freezes a frontier-candidate route for prospective in-silico
materials follow-up. It upgrades the candidate generator from PGCGM/near-hull
substitution to MatterGen and uses a conservative CHGNet + MACE-MP consensus
score before PARC release. It is not a completed DFT result.

## Evidence boundary

- MatterGen must generate a real public-label-free candidate pool before any
  DFT outcome is available.
- CHGNet and MACE-MP must score both calibration representatives and generated
  candidates under the same frozen score rule.
- PARC must produce a nonempty release arm satisfying the predeclared DFT gate.
- `selection_frozen_v4.csv` and `dft_job_manifest_v4.csv` remain empty until
  all gates above pass.
- No new DFT outcomes, synthesis claims or discovery claims are included in
  this protocol gate.

## Endpoints

Primary strict endpoint: `v4a_strict_exact_K100`, alpha=0.10, rho=0.10,
K=100, composition-family blocks, exact-stability target, minimum release for
DFT = 25.

Secondary endpoint: `v4b_strict_exact_K300`.

Near-hull operational endpoint: `v4c_near_hull_25meV_K300`, reported only as
near-hull computational follow-up.
