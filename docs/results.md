# PARC-Track Results Overview

This document is a compact pointer to the final public result tables. It does
not supersede the CSV artifacts; the CSV files are the source of truth.

## Source-Of-Truth Tables

- Audit and agreement:
  `outputs/milestones/reliability_fortress/audit_labels_2000_human_reviewed.csv`,
  `outputs/milestones/reliability_fortress/second_rater_agreement_summary.csv`
- Main certification and stress:
  `outputs/milestones/reliability_fortress/table_blackbox_generator_certification.csv`,
  `outputs/milestones/reliability_fortress/table_nonexchangeability_severe_actual_results.csv`,
  `outputs/milestones/reliability_fortress/table_null_inflation_verified_removal_actual_results.csv`
- Generality:
  `outputs/milestones/generality_reliability/table_lvis_detection_certification.csv`,
  `outputs/milestones/generality_reliability/table_ovvis_mask_certification.csv`,
  `outputs/milestones/generality_reliability/table_stratified_reliability.csv`
- Historical OVT-B/TAO/BURST matrices:
  `outputs/milestones/legacy_core_results/`

## Reporting Protocol

The main protocol remains fixed global `M=150`. Best-M tables are diagnostic
only. Each proposal source is calibrated independently; raw detector scores are
not compared across generators.

## Metric Scope

PARC-Track is reported as a post-hoc certified release layer rather than a
standalone HOTA-maximizing tracker. TrackEval/HOTA/IDF1/MOTA tables are included
as empirical tracking-quality context, while the main formal claim is false
tracklet release certification under partial annotations.
