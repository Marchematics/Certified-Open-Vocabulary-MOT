# CTC Learned-Hybrid Link Certification Main Result

The Cell Tracking Challenge experiment is the strict scientific-domain positive anchor for PARC. It instantiates release-time certification on biomedical cell-linking decisions with a sequence-disjoint learned-hybrid proposal source.

## Claim

PARC certifies adjacent-frame cell-link releases from a learned-hybrid appearance/geometry linker under one-sided partial verification. The proposal scorer is trained on sequence-disjoint data and frozen before PARC certification; held-out labels are used only after release to compute actual FTR.

## Main Numbers

The paper-facing CTC flagship is the strict learned-source row:

```text
rho=0.10, observed_positive_strategy=top_score, alpha=0.10, K=10--300
```

Across this grid PARC is non-empty in `20/20` seeds and has held-out actual FTR `0.000`. Representative rows:

| K | non-empty seeds | mean release | mean actual FTR | max actual FTR | raw top-K actual FTR | evidence mass |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 20/20 | 100.00 | 0.000000 | 0.000000 | 0.000000 | 1.338 |
| 300 | 20/20 | 300.00 | 0.000000 | 0.000000 | 0.000000 | 1.338 |

The earlier geometric CTC rows remain useful as diagnostics and historical ablations, but the manuscript flagship should use the learned-hybrid strict `alpha=0.10` result.

## Leakage and robustness checks

The learned-source result is accompanied by three reviewer-facing checks:

- a leakage audit specifying allowed and forbidden features;
- reverse split sensitivity;
- random-score negative control, where raw top-K FTR is high and PARC refuses.

These checks are critical because a strict learned-source row with zero observed FTR would otherwise invite leakage or lucky-split concerns.

## Partial Verification

The current learned CTC flagship is still a controlled partial-verification result: PARC sees only a masked subset of true links as observed positives, while full held-out GT is used after release to compute actual FTR. It should not be described as an independent-source human audit until the strict CTC human-audit protocol is completed.

The next high-value validation is a quasi-prospective CTC audit:

```text
alpha = 0.10, K in {100,300}
human/expert-confirmed positive links enter PARC
official CTC GT or separate blind review evaluates released-set FTR
```

## Interpretation

This result should be framed as cell-link release certification, not as a full CTC tracker benchmark. PARC separates prediction from release: given a ranked set of candidate links, it certifies which links can be safely released under one-sided verification and refuses unsafe release volumes. Use CTC learned-hybrid as the strict scientific-domain flagship; use iWildCam and SpaceNet to show real-audit operational release/refusal boundaries.
