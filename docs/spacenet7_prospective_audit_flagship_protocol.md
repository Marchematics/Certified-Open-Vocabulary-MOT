# SpaceNet 7 Prospective Audited Release Trial Protocol

This document freezes the protocol for a prospective SpaceNet 7 building-link release trial. The goal is to test whether PARC can operate with real one-sided human partial verification in a second scientific domain, rather than promoting the previous K=50 diagnostic audit after seeing its labels.

## Scope

- Domain: Earth-observation building monitoring.
- Release unit: a candidate link between a building footprint at month `t` and a building footprint at month `t+1`.
- Candidate source: a learned-geometry SpaceNet 7 building-link scorer trained on AOIs disjoint from the certification AOIs and frozen before PARC certification.
- Primary outcome: human-audited false-link fraction on released candidates.
- Raw imagery, raw SpaceNet annotations and large candidate universes are not included in public packages.

## Candidate Source

The trial uses a lightweight learned scorer over precomputed building-link candidates. The scorer may use only proposal-side link features:

- footprint bounding-box IoU;
- centroid-distance score;
- area ratio;
- base geometry score;
- deterministic candidate noise used only as a proposal-source perturbation;
- frame/month metadata that does not encode the official same-building label.

Forbidden fields:

- building identifiers as model features;
- `is_unmatched`, official match flags or same-building labels;
- human audit labels;
- PARC release labels;
- any held-out FTR or release-audit information.

The model is trained on a fixed AOI split and certified on disjoint AOIs. Normalization and model fitting are performed only on the training AOIs. Held-out official labels are used for planning/proxy diagnostics and leakage checks, not as human-audit evidence.

## Audit Sets

All prospective audit candidates must be disjoint from earlier SpaceNet 7 audit candidates by `path_id`. The preferred trial is AOI-disjoint from the old audit when enough blocks are available; if this is underpowered, the trial uses candidate-disjoint held-out AOIs with the limitation recorded.

Three audit sets are generated:

1. Calibration audit: block-balanced top-score queue, target `n=1,200`.
2. Release audit: all unique released candidates if at most 300; otherwise 300 candidates stratified by rank/block.
3. Raw top-K audit: 250 candidates from the same source, disjoint from calibration and release audit candidates.

Annotators are blinded to source score, release status, official labels, seed and endpoint. Labels are:

- `same_building`;
- `not_same_building`;
- `uncertain`.

Only human-confirmed `same_building` labels enter PARC as `A=1` observed positives. `not_same_building`, `uncertain` and disagreements remain unverified and are never used as trusted negatives.

## Predeclared Endpoints

Run the following endpoints after calibration labels are frozen:

- strict endpoint: `K=50`, `alpha=0.10`;
- strict fallback: `K=25`, `alpha=0.10`;
- operational endpoint: `K=50`, `alpha=0.20`;
- safety endpoints: `K=100`, `alpha={0.10,0.20}` and randomized/score-control sources.

Seeds are `0..19`. Blocks are AOI-time windows inherited from the SpaceNet 7 building-link universe.

## Go / No-Go Rule

The trial is a second flagship only if at least one predeclared endpoint satisfies:

- non-empty seeds at least `18/20`;
- mean release size at least 20 for strict endpoint or 30 for operational endpoint;
- human FTR no larger than the endpoint alpha;
- conservative human FTR, counting uncertain as false, no larger than the endpoint alpha;
- disagreement policy remains one-sided and conservative.

If the trial does not satisfy these rules, it remains a real-audit refusal or operating check and is not promoted to a primary positive result.
