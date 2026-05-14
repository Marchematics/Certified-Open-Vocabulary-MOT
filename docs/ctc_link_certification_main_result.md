# CTC Link Certification Main Result

The Cell Tracking Challenge experiment is the scientific-domain positive anchor for PARC. It instantiates release-time certification on biomedical cell-linking decisions, rather than on open-vocabulary tracking prompts.

## Claim

Across four 2D CTC training datasets, PARC certifies adjacent-frame cell-link releases under one-sided verification and refuses unsafe high-volume requests.

The experiment uses 208,230 candidate links from four datasets:

- `DIC-C2DH-HeLa`
- `Fluo-N2DH-GOWT1`
- `Fluo-N2DL-HeLa`
- `PhC-C2DH-U373`

Candidate nodes are CTC `GT/TRA` cell masks. Candidate links are ranked by a deterministic noisy geometric linker with noise weight `0.90`. CTC tracking truth is the single official GT source. The anti-circularity evidence comes from the controlled partial-verification sweeps: PARC sees only an observed-positive subset, while held-out GT labels are used for final actual-FTR measurement. Rows with `rho=1.0` are full-verification/oracle diagnostics, not independent-source validation.

## Main Numbers

The strict `alpha=0.10` partial-verification rows are certified refusals for the
current CTC linker because the finite-resolution/evidence ceiling is below the
required threshold. The paper-facing positive CTC row is therefore the
relaxed-risk partial-verification protocol:

```text
rho=0.10, observed_positive_strategy=top_score, alpha=0.20, M=100
```

In this row PARC is non-empty in `20/20` seeds, releases exactly `100` links on
average, and has held-out/full-GT actual FTR `0.000`.

The broader `alpha=0.20` diagnostic pattern is:

| M | non-empty seeds | mean release | mean actual FTR | max actual FTR | raw top-M actual FTR |
|---:|---:|---:|---:|---:|---:|
| 100 | 20/20 | 100.00 | 0.000000 | 0.000000 | 0.000000 |
| 300 | 20/20 | 300.00 | 0.000167 | 0.003333 | 0.000167 |
| 500 | 18/20 | 415.85 | 0.001103 | 0.007317 | 0.005500 |

At `M=5000`, PARC refuses entirely at `alpha=0.20`, while raw top-M has actual FTR `0.3606`. This is a positive safety result: PARC certifies small high-confidence releases and refuses unsafe bulk release.

## Partial Verification Sweep

We separate the labels PARC sees from the labels used for final evaluation.

- Full CTC GT is used for final actual-FTR evaluation.
- PARC sees only a subset of true links as observed positives.
- Hidden true links enter the null-superset pool from PARC's perspective.

Two partial-verification policies are reported:

1. `random`: observed positives are sampled uniformly from true links.
2. `top_score`: observed positives are sampled from high-score true links, matching an audit-style high-evidence verification policy.

At `alpha=0.20`, random sparse verification produces safe refusal for all
`rho < 1.0`, because hidden high-score true links contaminate the null-superset
block maxima. In contrast, high-score verification recovers certified releases
even at small observed-positive fractions. The strongest paper-facing row uses
`rho=0.10, M=100`; the larger-budget rows are useful diagnostics but should not
be overclaimed as strict primary results.

| strategy | rho | M | non-empty seeds | mean release | mean actual FTR | max actual FTR |
|---|---:|---:|---:|---:|---:|---:|
| random | 0.05 | 300 | 0/20 | 0.00 | 0.000000 | 0.000000 |
| random | 0.50 | 300 | 0/20 | 0.00 | 0.000000 | 0.000000 |
| top_score | 0.10 | 100 | 20/20 | 100.00 | 0.000000 | 0.000000 |
| top_score | 0.05 | 300 | 20/20 | 300.00 | 0.000167 | 0.003333 |
| top_score | 0.05 | 500 | 18/20 | 415.85 | 0.001103 | 0.007317 |

This is the expected behavior: PARC is not guaranteed to work under arbitrary random sparse verification. It relies on removing high-evidence verified positives from the null superset. When high-score positives are observed, even a small observed-positive fraction is sufficient in this CTC setting.

## Per-Dataset Breakdown

The aggregate result is not supported by a single dataset. At `alpha=0.20, M=300`, all four datasets contribute released links across the 20 seeds:

| Dataset | candidates | GT-supported | blocks | mean release | mean actual FTR |
|---|---:|---:|---:|---:|---:|
| DIC-C2DH-HeLa | 10,575 | 2,106 | 34 | 15.05 | 0.000000 |
| Fluo-N2DH-GOWT1 | 22,635 | 4,494 | 38 | 52.95 | 0.000000 |
| Fluo-N2DL-HeLa | 167,795 | 33,719 | 38 | 223.55 | 0.000259 |
| PhC-C2DH-U373 | 7,225 | 1,437 | 46 | 8.45 | 0.000000 |

## Interpretation

This result should be framed as cell-link release certification, not as a full CTC tracker benchmark. PARC separates prediction from release: given a ranked set of candidate links, it certifies which links can be safely released under one-sided verification and refuses unsafe release volumes. The main validity evidence should emphasize the `rho < 1` partial-verification rows; `rho=1.0` rows should be described as oracle/full-verification diagnostics.

Use CTC as the scientific-domain positive anchor. Use iWildCam as a boundary diagnostic: species-level iWildCam violates one-sided reliability, while animal-present iWildCam lacks sufficient high-evidence mass.
