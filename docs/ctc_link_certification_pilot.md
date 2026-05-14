# CTC Link-Level Certification Pilot

This pilot instantiates PARC on Cell Tracking Challenge training data as adjacent-frame cell-link certification. It is a biomedical analogue of the release-time certification problem, not a full CTC tracker benchmark.

## Setup

- Datasets: `DIC-C2DH-HeLa`, `Fluo-N2DH-GOWT1`, `Fluo-N2DL-HeLa`, `PhC-C2DH-U373`.
- Unit: a candidate link between a cell instance at frame `t` and a cell instance at frame `t+1`.
- Node source: CTC `GT/TRA` masks. This isolates the link-release problem from segmentation errors.
- Candidate source: deterministic noisy geometric linker with noise weight `0.90`.
- Blocks: 5-frame windows, yielding 156 calibration/test blocks.
- Candidates: 208,230 links, of which 41,756 are supported by full GT tracking truth.
- Protocol: alpha in `{0.10, 0.20}`, seeds `0..19`, `M in {100, 300, 500, 2000, 5000}`.

Outputs are under:

```text
outputs/ctc_link_certification/
```

## Result

The CTC pilot passes the go/no-go gate for a scientific-domain positive result.

At `alpha=0.20`, PARC releases non-empty certified link sets in all 20 seeds for `M=100` and `M=300`, and in 18/20 seeds for `M=500`.

| alpha | M | non-empty seeds | mean released | mean actual FTR | max actual FTR | raw top-M actual FTR |
|---:|---:|---:|---:|---:|---:|---:|
| 0.20 | 100 | 20/20 | 100.00 | 0.000000 | 0.000000 | 0.000000 |
| 0.20 | 300 | 20/20 | 300.00 | 0.000167 | 0.003333 | 0.000000 |
| 0.20 | 500 | 18/20 | 415.85 | 0.001103 | 0.007317 | 0.000000 |
| 0.20 | 2000 | 0/20 | 0.00 | 0.000000 | 0.000000 | 0.009000 |
| 0.20 | 5000 | 0/20 | 0.00 | 0.000000 | 0.000000 | 0.360600 |

At `alpha=0.10`, PARC refuses all settings because the finite-resolution e-value ceiling is below the required threshold. At `alpha=0.20`, PARC refuses `M=2000` and `M=5000` because there is insufficient high-evidence mass. This is the desired safe-refusal behavior: raw top-M at `M=5000` has actual FTR `0.3606`.

## Paper Framing

Use this as a positive scientific-domain instantiation:

> On Cell Tracking Challenge training data, PARC certifies adjacent-frame cell-link releases under partial verification and full tracking truth. This demonstrates that the release-time certification abstraction is not tied to open-vocabulary MOT prompts: when reliable one-sided support and a frozen candidate universe are available, PARC can certify low-error releases or refuse unsafe budgets.

Limitations to state clearly:

- This is a link-level pilot, not a full-track CTC tracker benchmark.
- Candidate nodes come from GT/TRA masks to isolate release certification from segmentation quality.
- Full-track aggregation and mitosis-aware lineage release are future extensions.
