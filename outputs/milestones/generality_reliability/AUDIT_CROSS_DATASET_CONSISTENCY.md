# Audit Cross-Dataset Consistency

The Audit2000 benchmark shows that high-score official-unmatched paths are frequently human-valid across all three tracking datasets. This supports treating official-unmatched predictions as unknown rather than as reliable negatives.

- Shared human-valid interval across available datasets: `0.936-0.979`.
- Source: `outputs/milestones/reliability_fortress/audit_labels_2000_human_reviewed.csv`.

See `table_audit_cross_dataset_consistency.csv` for dataset-level counts and rates.
