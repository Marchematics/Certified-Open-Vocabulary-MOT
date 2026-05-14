# CTC Link-Level Certification Pilot

Status: **go/no-go passed**.

This pilot instantiates PARC on Cell Tracking Challenge training data as adjacent-frame cell-link certification. The unit is a candidate link between a cell instance at frame t and a cell instance at frame t+1. Candidate nodes are derived from CTC GT/TRA masks to isolate the release-time certification problem; candidate link scores come from a deterministic noisy geometric linker (noise weight 0.90), so the experiment tests certification of an imperfect link ranking rather than detector prompt grounding.

## Scope

- Datasets: DIC-C2DH-HeLa, Fluo-N2DH-GOWT1, Fluo-N2DL-HeLa, PhC-C2DH-U373.
- Candidate links: 208,230.
- Calibration/test blocks: 156 frame-window blocks (5-frame windows).
- Gold-supported candidate links: 41,756.
- Unsupported candidate links: 166,474.
- Alpha grid: 0.10 and 0.20.
- Seeds: 0-19.
- M grid: 100, 300, 500, 2000, 5000.

## Main Result

At alpha=0.20, PARC releases non-empty certified link sets in all 20 seeds for M=100 and M=300, and in 18/20 seeds for M=500.

| alpha | M | non-empty seeds | mean released | mean actual FTR | max actual FTR | raw top-M actual FTR |
|---:|---:|---:|---:|---:|---:|---:|
| 0.20 | 100 | 20/20 | 100.00 | 0.000000 | 0.000000 | 0.000000 |
| 0.20 | 300 | 20/20 | 300.00 | 0.000167 | 0.003333 | 0.000000 |
| 0.20 | 500 | 18/20 | 415.85 | 0.001103 | 0.007317 | 0.000000 |
| 0.20 | 2000 | 0/20 | 0.00 | 0.000000 | 0.000000 | 0.009000 |
| 0.20 | 5000 | 0/20 | 0.00 | 0.000000 | 0.000000 | 0.360600 |


## Interpretation

- The CTC pilot provides a clean non-tracking scientific-domain positive result: PARC can certify low-error cell-link releases when the one-sided support structure is reliable.
- Alpha=0.10 is refused because the finite-resolution e-value ceiling is below the required threshold. This is an explicit power/refusal result, not a hidden failure.
- At M=5000, raw top-M has actual FTR 0.3606, while PARC refuses at alpha=0.20 due to insufficient high-evidence mass. This is the desired certified-refusal behavior.
- The experiment is link-level and training-set based. It should be described as a CTC pilot / biomedical analogue, not as a full CTC tracker benchmark.
