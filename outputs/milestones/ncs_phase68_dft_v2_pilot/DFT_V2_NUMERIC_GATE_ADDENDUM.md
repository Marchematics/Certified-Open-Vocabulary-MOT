# DFT v2 Numeric Gate Addendum

Status: frozen after local VASP execution had begun, before any `e_above_hull`
or `stable_exact` outcome table was available.

Timing disclosure: at the time this addendum was written, the local queue had
recorded 9 `completed` VASP jobs and 2 `failed` VASP jobs in
`vasp_queue_status.csv`. This early execution signal is disclosed because the
workflow-failure gate below is being frozen after observing those execution
statuses. No DFT stability outcome was available: `VASP_DONE` means a single
structure calculation produced VASP output, not that a reference-hull
`e_above_hull` or `stable_exact` label has been computed.

This addendum does not modify the blinded manifest, arm assignment, CIF files,
candidate selection, or DFT outcome template. It only freezes how the DFT v2
pilot may be interpreted after outcomes are eventually constructed.

## Primary conservative interpretation

The original conservative policy remains primary:

1. `completed && stable_exact` counts as certified stable.
2. `completed && !stable_exact` counts as false.
3. failed, missing, invalid, duplicate, unconverged, or missing-hull jobs count
   as not-certified-stable / false in the primary conservative FTR.
4. completed-only FTR is secondary and may not be used as a headline if the
   workflow-validity gate below fails.

## Workflow-validity gate

DFT v2 may be promoted to main-text positive evidence only if all of the
following hold after the outcome table is frozen:

1. The overall workflow failure fraction among jobs included in the primary
   DFT v2 analysis is at most 10%.
2. The PARC release core arm has workflow failure fraction at most 10%.
3. The raw-only extra-tail comparator arm has workflow failure fraction at most
   10%.
4. The absolute failure-fraction difference between the PARC release core and
   raw-only extra-tail arms is at most 10 percentage points.

If any item fails, DFT v2 is reported as workflow-limited and may appear only as
Supplementary feasibility or sensitivity evidence. In that case, completed-only
FTR may be shown as a diagnostic but must not be used as the paper's clean
positive validation claim.

## Efficacy gate

If the workflow-validity gate passes, DFT v2 can support a main-text positive
only if the PARC release core arm satisfies:

```text
primary conservative FTR <= alpha = 0.10
```

The strongest positive role additionally requires raw-only extra-tail to have a
primary conservative FTR at least 10 percentage points higher than the PARC
release core arm. If PARC release core passes alpha but the raw-only contrast is
weak, DFT v2 is a limited validation of release stability, not a strong
release-vs-tail utility claim.

## Paper-timeline rule

The manuscript is not allowed to wait on DFT v2. Until the workflow and efficacy
gates pass, DFT v2 remains a pending bonus arm. The main paper spine should rest
on the completed durability-risk prediction, PARC-A active verification,
versioned certificate accounting, and completed materials release-card audits.

