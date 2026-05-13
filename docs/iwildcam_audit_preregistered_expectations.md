# iWildCam Blind Audit Pre-Registered Expectations

This note records the iWildCam audit expectations before human labels are
entered. It is intended to make the downstream narrative auditable rather than
selected after observing labels.

## Batch Design

The blind audit batch contains 500 unique iWildCam candidate detections. The
annotator receives a shuffled template identified by blind IDs and does not see
the stratum, release policy, score, or official-support fields. The analysis key
is stored separately in the experiment workspace.

The intended strata were A=200, B=100, C=100, and D=100. The realized iWildCam
frontier is smaller: the relaxed M=50, alpha=0.30 frontier produced 156 unique
released paths, and the alpha=0.20 frontier is a subset of that set. In addition,
all raw top-50 candidates overlap with the relaxed PARC frontier. The batch
therefore keeps all available non-overlapping A/B/D paths, uses the nearest
high-score raw non-PARC contrast set for C, and fills the remaining rows with a
score-spectrum unmatched supplement.

## Realized Stratum Counts

| Stratum | Rows | Role |
|---|---:|---|
| A: PARC M=50, alpha=0.30 unique released | 59 | Primary relaxed frontier |
| B: PARC M=50, alpha=0.20 unique released | 47 | Lower-risk frontier point |
| C: high-score raw candidates not released by PARC | 100 | No-certificate contrast |
| D: raw top-50 and PARC-released overlap | 50 | Same-pool overlap comparison |
| E: score-spectrum unmatched supplement | 244 | Broader unmatched validity characterization |

## Expected Ranges

- A: expected audited FTR around 0.15--0.25 and below alpha=0.30.
- B: expected audited FTR around 0.10--0.18 and below alpha=0.20, with wider
  uncertainty because only 47 unique non-overlap paths are available.
- C: expected audited FTR around 0.40--0.60; this is the no-certificate
  baseline contrast.
- D: expected audited FTR below C and comparable to A/B, supporting the claim
  that PARC identifies safer high-evidence paths within a raw candidate pool.
- E: descriptive only; used to characterize official-unmatched path validity
  across a broader score range.

If A exceeds alpha=0.30 or B exceeds alpha=0.20, the iWildCam result should be
reported as an assumption-boundary or audit-sensitive result rather than as
final human-audited FTR evidence.
