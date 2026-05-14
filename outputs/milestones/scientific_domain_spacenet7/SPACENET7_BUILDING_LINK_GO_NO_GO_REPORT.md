# SpaceNet 7 Building-Link Certification

This milestone is an Earth-observation scientific-domain go/no-go pilot for PARC-style release-time certification. It uses SpaceNet 7 `labels_match` building footprints to form adjacent-month building-link candidates. Raw SpaceNet labels, imagery, and large derived candidate universes are not redistributed.

## Universe

- AOIs: 18
- Candidate building links: 6,341,788
- GT-supported same-building links: 2,050,769
- AOI-time blocks: 138
- Candidate source: geometry linker over adjacent-month building footprints, top-3 targets per source building plus true same-ID links.

## Go/No-Go Finding

The geometry linker is a positive Earth-observation anchor at `alpha=0.20`: it produces non-empty certified releases for small-to-medium release requests with empirical actual FTR far below the target. The randomized-linker stress variant is a certified-refusal case: raw top-M false-link rates are about 66--68%, and PARC releases zero links across the tested budgets.

### Geometry Linker, rho=1.0, alpha=0.20

| source | dataset | domain | alpha | rho | M | seeds | nonempty_seeds | released_mean | actual_FTR_mean | actual_FTR_max | raw_topM_actual_FTR_mean | best_mass_ratio_mean | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| geometry_linker | SpaceNet7 | earth_observation_building_links | 0.2 | 1.0 | 100 | 20 | 17 | 81.75 | 0.003 | 0.01 | 0.003 | 1.123165723 | positive_certified_release |
| geometry_linker | SpaceNet7 | earth_observation_building_links | 0.2 | 1.0 | 300 | 20 | 11 | 165.0 | 0.002333333 | 0.006666667 | 0.002333333 | 0.987844324 | positive_certified_release |
| geometry_linker | SpaceNet7 | earth_observation_building_links | 0.2 | 1.0 | 500 | 20 | 10 | 240.35 | 0.001364081 | 0.004761905 | 0.0018 | 0.941650803 | positive_certified_release |
| geometry_linker | SpaceNet7 | earth_observation_building_links | 0.2 | 1.0 | 5000 | 20 | 0 | 0.0 | 0.0 | 0.0 | 0.00184 | 0.262509328 | certified_refusal_stress |

### Randomized Linker Stress, rho=1.0, alpha=0.20

| source | dataset | domain | alpha | rho | M | seeds | nonempty_seeds | released_mean | actual_FTR_mean | actual_FTR_max | raw_topM_actual_FTR_mean | best_mass_ratio_mean | interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| randomized_linker_stress | SpaceNet7 | earth_observation_building_links | 0.2 | 1.0 | 100 | 20 | 0 | 0.0 | 0.0 | 0.0 | 0.6575 | 0.07272718 | certified_refusal_stress |
| randomized_linker_stress | SpaceNet7 | earth_observation_building_links | 0.2 | 1.0 | 300 | 20 | 0 | 0.0 | 0.0 | 0.0 | 0.681 | 0.055048051 | certified_refusal_stress |
| randomized_linker_stress | SpaceNet7 | earth_observation_building_links | 0.2 | 1.0 | 500 | 20 | 0 | 0.0 | 0.0 | 0.0 | 0.678 | 0.052430109 | certified_refusal_stress |
| randomized_linker_stress | SpaceNet7 | earth_observation_building_links | 0.2 | 1.0 | 5000 | 20 | 0 | 0.0 | 0.0 | 0.0 | 0.67567 | 0.049431157 | certified_refusal_stress |

## Paper Positioning

Use this result as a second positive scientific-domain application alongside CTC: biomedical cell-link release and Earth-observation building-link release. The randomized stress variant should be written as a safe-refusal control, not as a failed SpaceNet application.
