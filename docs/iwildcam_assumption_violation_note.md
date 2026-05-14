# iWildCam Assumption-Violation Note

Status: preliminary visual triage, pending human-confirmed audit for any paper-facing FTR claim.

## Core Finding

The relaxed iWildCam frontier should not be framed as a positive human-audited PARC result unless human review overturns the current visual-triage direction. A preliminary visual pass over 156 unique released frontier paths found:

| set | n | true | false | uncertain | false-only FTR | conservative FTR |
|---|---:|---:|---:|---:|---:|---:|
| all released frontier paths | 156 | 7 | 132 | 17 | 0.846 | 0.955 |
| M=50, alpha=0.20 | 84 | 0 | 74 | 10 | 0.881 | 1.000 |
| M=50, alpha=0.30 | 72 | 7 | 58 | 7 | 0.806 | 0.903 |

If confirmed by human review, these numbers mean that the iWildCam official-proxy instantiation is outside the theorem's assumptions. This is not a mathematical counterexample to the PARC theorem; it is an empirical failure of the attempted transfer because the one-sided-positive support model is likely invalid.

## Likely Mechanism

The failure is concentrated in high-scoring species prompts, especially `urocyon cinereoargenteus`. Many released detections are visually birds, large cats, ungulates, elephants, or background regions rather than gray foxes.

This suggests a support-semantics failure:

```text
official image-level species support + high detector score
  does not imply
the specific detection box is a true positive for that species.
```

In PARC notation, the condition analogous to `A_p = 1 => Y_p = 1` is not justified for iWildCam when `A_p` is defined using weak image-level species support rather than dense box-level verification.

## Paper Framing

Do not hide this result as an appendix-only stress case if human review confirms it. The scientifically honest framing is:

> In a scientific-domain camera-trap transfer, a weak official-support proxy can violate the one-sided reliability assumption. PARC then produces an invalid certificate if the proxy is treated as verified support. This negative result clarifies that release-time certification requires auditing not only unsupported releases but also the support semantics used to construct one-sided positives.

This identifies a real boundary of conformal/e-value style release control under incomplete scientific annotations.

## Required Follow-Up

1. Audit iWildCam released frontier paths with human review.
2. Audit a stratified sample of iWildCam official-supported / verified-positive candidate boxes.
3. If official-supported boxes have substantial wrong-species localization, mark iWildCam as an assumption-violation case rather than a positive certification benchmark.
4. If official-supported precision is high but released FTR remains high, investigate SCS/e-value calibration, candidate freezing, and split exchangeability.
5. Only report human-audited iWildCam FTR after human confirmation; until then use preliminary triage numbers only for experiment planning.

## Coarse Animal-Present Follow-Up

We also ran the intended low-cost rescue: replace species-level prompts with a coarse `animal` prompt and change support semantics from exact species identity to image-level animal presence.

The animal-present variant fixes the obvious species-level semantic-misgrounding failure, but it still does not pass the pre-registered release gate:

| target | M | alpha | seeds | non-empty seeds | mean release | mean max e | required e |
|---|---:|---:|---:|---:|---:|---:|---:|
| animal_present | 150 | 0.10 | 20 | 0 | 0.0 | 1.986 | 10.000 |
| animal_present | 50 | 0.10 | 20 | 0 | 0.0 | 1.986 | 10.000 |
| animal_present | 50 | 0.20 | 20 | 0 | 0.0 | 1.986 | 5.000 |
| animal_present | 50 | 0.30 | 20 | 0 | 0.0 | 1.986 | 3.333 |

This is a different failure mode. The species-level experiment fails because released boxes are often the wrong species, violating one-sided reliability. The animal-present experiment is semantically safer, and raw top-M has official proxy UTR=0 because the top detections occur in animal-labeled images. However, the calibration null distribution still contains high animal-prompt scores, so the maximum observed e-value is too small for self-consistent release even at the relaxed frontier.

According to the pre-registered go/no-go rule, iWildCam should not be further tuned as the positive scientific-domain anchor for this paper. The next domain should have stronger localization or track-level support semantics, such as CTC-style cell tracking, rather than another round of camera-trap prompt engineering.

Source report:

- `outputs/iwildcam_animal_present_certification/IWILDCAM_ANIMAL_PRESENT_RUN_REPORT.md`

## Source Files

- `outputs/iwildcam_release_certification/visual_triage_released_frontier/triage_labels_iwildcam_released_frontier.csv`
- `outputs/iwildcam_release_certification/visual_triage_released_frontier/triage_summary_iwildcam_released_frontier.csv`
- `outputs/iwildcam_release_certification/visual_triage_released_frontier/VISUAL_TRIAGE_REPORT.md`
