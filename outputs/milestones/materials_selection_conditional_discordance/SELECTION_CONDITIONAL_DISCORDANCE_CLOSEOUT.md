# Selection-Conditional Materials Label Discordance Go/No-Go

This milestone tests Proposition B: whether MP/Alexandria exact-stability discordance is amplified in the high-confidence region selected by ML materials-stability scores.

## Inputs

- Source pair: Materials Project vs alex-mp v20.
- Exact matched denominator: `287` structures.
- Baseline discordance: `0.108`.
- Models: `ALIGNN-FF, CHGNet, MACE-MP`.
- Score direction: lower score means more model-favored / more stable.

## Result

- ALIGNN-FF: top-decile discordance `0.179` (5/28), enrichment `1.65x`.
- CHGNet: top-decile discordance `0.107` (3/28), enrichment `0.99x`.
- MACE-MP: top-decile discordance `0.107` (3/28), enrichment `0.99x`.

## Go/No-Go

- Decision: `NO_GO_hypothesis_B_not_supported`.
- Interpretation: MP-vs-alex full snapshot discordance is not concentrated in the high-confidence model-score region.

## Claim Boundary

This is a completed diagnostic, not a positive independent-validation result and not prospective materials discovery. It uses existing frozen MP/Alex exact-match labels and existing frozen model scores only.
