# Release-Certification Success-Domain Closeout

This artifact reframes cross-domain generality as a domain-of-success map rather than a claim that PARC releases in every domain. Rows are reportable only when the source table already contains completed evidence; proposed future audits and new domains are explicitly marked as protocol-only.

## Summary

- Main flagship evidence rows: 3
- Control/refusal/diagnostic rows: 4
- Generated tables: 25

## Paper-facing claim

PARC is a general release-certification interface for finite scientific AI candidate universes under one-sided partial verification. It releases when reliable one-sided positives, covered exchangeable blocks, sufficient evidence mass, and manageable compatibility conflicts are present; it refuses otherwise.

## Generated artifacts

- `outputs/milestones/scientific_release_success_map/table_cross_domain_evidence_matrix.csv`
- `outputs/milestones/scientific_release_success_map/table_success_domain_features.csv`
- `outputs/milestones/scientific_release_success_map/table_success_domain_summary_by_domain.csv`
- `outputs/milestones/scientific_release_success_map/table_practitioner_success_checklist.csv`
- `outputs/milestones/scientific_release_success_map/table_strict_real_audit_protocols.csv`
- `outputs/milestones/scientific_release_success_map/table_materials_stability_threshold_robustness_plan.csv`
- `outputs/milestones/scientific_release_success_map/table_materials_stability_threshold_robustness.csv`
- `outputs/milestones/scientific_release_success_map/table_materials_gamma_sensitivity.csv`
- `outputs/milestones/scientific_release_success_map/table_candidate_new_domain_protocols.csv`
- `outputs/milestones/scientific_release_success_map/table_block_coverage_exchangeability_diagnostics.csv`
- `outputs/milestones/scientific_release_success_map/table_near_boundary_practical_value.csv`
- `outputs/milestones/scientific_release_success_map/table_audit_contamination_sensitivity.csv`
- `outputs/milestones/scientific_domain_materials/materials_threshold_robustness_figure.csv`
- `outputs/milestones/scientific_domain_materials/materials_threshold_robustness_figure.pdf`
- `outputs/milestones/scientific_domain_materials/materials_gamma_sensitivity_heatmap.csv`
- `outputs/milestones/scientific_domain_materials/materials_gamma_sensitivity_heatmap.pdf`
- `outputs/milestones/scientific_domain_materials/materials_raw_vs_parc_ftr_panel.csv`
- `outputs/milestones/scientific_domain_materials/materials_raw_vs_parc_ftr_panel.pdf`
- `outputs/milestones/scientific_release_success_map/table_refusal_diagnosis_ilp.csv`
- `outputs/milestones/scientific_release_success_map/REFUSAL_DIAGNOSIS_ILP_CLOSEOUT.md`
- `outputs/milestones/scientific_release_success_map/table_success_domain_predictor.csv`
- `outputs/milestones/scientific_release_success_map/table_success_domain_rules.csv`
- `outputs/milestones/scientific_release_success_map/figure_success_domain_map.csv`
- `outputs/milestones/scientific_release_success_map/figure_success_domain_map.pdf`
- `outputs/milestones/scientific_release_success_map/table_validity_assumptions_by_domain.csv`

## Guardrails

- CTC and materials strict rows are controlled partial-verification results unless a real human/experimental audit is completed.
- Materials threshold and fixed-gamma sensitivity rows are completed reruns when the corresponding tables are present in `scientific_domain_materials`.
- Materials paper-ready figure artifacts are completed diagnostics derived from existing robustness, gamma, and near-boundary CSVs.
- Refusal ILP rows use a conservative aggregate oracle: ILP infeasibility is asserted only for rows that fail before graph compatibility (`max_e < required_e` or `Phi < 1`).
- iWildCam is the current real-human-audit operational release row; strict alpha=0.10 remains refusal unless additional audit coverage changes the evidence mass.
- SpaceNet K=50 remains diagnostic, while K=100 real-audit primary request is a certified refusal.
- Molecular/protein domains are protocol-only here and must not be cited as completed evidence.
