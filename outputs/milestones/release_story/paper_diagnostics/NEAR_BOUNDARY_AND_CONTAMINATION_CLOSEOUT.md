# Near-Boundary Release and Audit-Contamination Closeout

## Near-Boundary Release Value

The main near-boundary practice-benefit row is intentionally non-random and
comes from the materials-discovery source.  CTC learned-hybrid and SpaceNet 7
geometry rows are included in the screening table as clean-slice positives, not
as near-boundary raw-risk evidence.  This prevents using a randomized source as
the main practice-benefit claim.

Primary table: `outputs/milestones/release_story/paper_diagnostics/table_near_boundary_release_value.csv`

Domain screening table: `outputs/milestones/release_story/paper_diagnostics/table_near_boundary_domain_screening.csv`

## Audit-Contamination Sensitivity

The CTC sensitivity deliberately violates the one-sided reliability assumption
on a high-volume structured-link stress row (K=1000, alpha=0.20) by marking
calibration-block high-score false links as verified positives at rates epsilon
in {0%, 1%, 3%, 5%, 10%}.  These rows are not formal guarantees; they measure
how release rate, release size, actual FTR, violation rate, and mass ratio
change when the theorem assumption is broken.

Summary table: `outputs/milestones/release_story/paper_diagnostics/table_ctc_audit_contamination_sensitivity.csv`

Figure-ready CSV: `outputs/milestones/release_story/paper_diagnostics/figure_ctc_audit_contamination_sensitivity.csv`
