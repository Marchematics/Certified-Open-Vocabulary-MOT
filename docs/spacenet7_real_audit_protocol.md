# SpaceNet 7 Real Partial-Verification Audit Protocol

Status: pre-registered protocol for review-ready audit batch generation.

This protocol tests whether PARC can operate with a real partial-verification
workflow on SpaceNet 7 building links, rather than only with masked official
ground-truth labels.

## Scope

- Domain: Earth-observation building persistence links.
- Dataset: SpaceNet 7 training labels (`labels_match`); raw imagery and raw
  labels are not redistributed in this repository.
- Candidate source: frozen `geometry_linker` candidate universe.
- Release unit: adjacent-month candidate building link.
- Primary operating point: `alpha=0.20`, `M=100`, seeds `0..19`.
- Strict-risk extension: `alpha=0.10`, `M in {25, 50, 75, 100}`, seeds `0..19`.

## Two Disjoint Audit Sets

The audit has two non-overlapping parts.

### A. Calibration Audit Set

Purpose: produce one-sided observed positives for PARC calibration.

Sampling:

- Source: SpaceNet 7 geometry-linker candidate universe.
- Queue: high-score candidates, stratified by AOI-time block (`video_id`).
- Target size: 800 candidate links.
- Sampling is performed before reading or using release outcomes.

Annotation task:

```text
same_building / not_same_building / uncertain
```

Verified-positive rule:

- Only links confirmed as `same_building` after human review may enter `A=1`.
- `not_same_building`, `uncertain`, missing, or disputed labels remain
  unverified.
- Unverified links are never used as trusted negatives.

### B. Release Audit Set

Purpose: estimate released-set FTR after PARC selection.

Procedure:

1. Run PARC using only calibration-audit verified positives as observed
   positives.
2. Form the release set under the primary operating point.
3. Sample up to 200 unique released links for blind audit.
4. Release-audit labels must not flow back into calibration.

If fewer than 100 unique released links exist, audit all released links and
report the sample-size limitation.

## Blinding Rules

Annotators should not see:

- official same-building identity;
- PARC release status;
- seed;
- score value;
- method condition;
- whether the candidate belongs to the calibration or release set.

Annotators may see:

- AOI identifier;
- source and target months;
- candidate source/target footprints or a review image overlay produced from
  raw SpaceNet imagery;
- candidate source and target footprint metadata needed for inspection.

## Review-Ready Initial Labels

The script may generate review-ready initial labels from the official
same-building identifier to speed internal checking. These labels are not
paper-facing human audit labels until a human reviewer confirms them. Public
tables must distinguish:

```text
requires_human_confirmation
human_confirmed
```

Only `human_confirmed` labels may be reported as real audit evidence.

## Primary Success Gate

The audit loop is considered a positive real partial-verification validation if:

- calibration audit contains at least 100 human-confirmed verified positives;
- verified-positive precision is at least 0.95 under conservative review;
- release audit covers at least 100 released links when available;
- primary setting has at least 15/20 non-empty seeds;
- mean release is at least 30;
- audited FTR point estimate is at most `alpha`;
- official-GT FTR is consistent with audited FTR.

## Outputs

Expected files:

```text
outputs/spacenet7_real_audit/audit_manifest.csv
outputs/spacenet7_real_audit/calibration_audit_blind_template.csv
outputs/spacenet7_real_audit/calibration_audit_review_prefill.csv
outputs/spacenet7_real_audit/release_audit_blind_template.csv
outputs/spacenet7_real_audit/release_audit_review_prefill.csv
outputs/spacenet7_real_audit/raw_topk_audit_blind_template.csv
outputs/spacenet7_real_audit/raw_topk_audit_review_prefill.csv
outputs/spacenet7_real_audit/table_spacenet7_real_audit_seed_results.csv
outputs/spacenet7_real_audit/table_spacenet7_real_audit_summary.csv
outputs/spacenet7_real_audit/RUN_REPORT.md
```

## Paper Positioning

Until human confirmation is complete, these artifacts are review-preparation
materials rather than paper-facing real-audit evidence. After confirmation, the
calibration audit can be described as actual partial verification entering
PARC, and the release audit can be described as separate blind evaluation of
released-set FTR.

## Transparent Diagnostic Amendment

If the primary operating point (`alpha=0.20`, `M=100`) produces an empty
release under the reviewed calibration positives, the audit package may also
export a release-audit set from a non-empty budget in the same pre-defined
grid. Such rows must be reported as diagnostic release-audit material after
primary refusal, not as primary operating-point success evidence.
