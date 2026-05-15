# P0 Supplemental Closeout

## Materials Modern-Model Sensitivity

Added a public ALIGNN-FF WBM prediction source as a modern learned materials
model sensitivity row.  The protocol reuses the same WBM candidate universe,
composition-family blocks, rho=0.10, alpha=0.10, seeds 0..19, and K grid used by
the CGCNN flagship.

Table: `outputs/milestones/scientific_domain_materials/table_materials_modern_model_sensitivity.csv`

## Minimal PU / Selective-Conformal Baselines

Added a compact supplement table for a PU plug-in classifier and two selective
conformal variants.  The table explicitly marks whether the method provides a
finite set-level release guarantee under one-sided verification.

Table: `outputs/milestones/release_story/paper_diagnostics/table_pu_selective_conformal_minimal_baselines.csv`

## PU / Selective-Conformal Benchmark

Added a full alpha=0.10, K=100 supplement benchmark for CTC, materials
discovery, and iWildCam.  It includes a PyTorch nnPU classifier and a Bao-style
post-selection selective conformal adaptation, plus raw top-K, oracle-label
diagnostics, and PARC reference points for the Table 2b frontier.

Tables:

- `outputs/milestones/release_story/paper_diagnostics/table_pu_selective_conformal_benchmark.csv`
- `outputs/milestones/release_story/paper_diagnostics/table_pu_selective_conformal_benchmark_seed_rows.csv`
- `outputs/milestones/release_story/paper_diagnostics/figure_table2b_baseline_frontier.csv`

Paper wording: these baselines target a different object from PARC's compatible
finite release set.  Use "different target object (concrete demonstration in
Supplement X)" when describing the comparison.

## iWildCam Second-Review Package

Prepared the blind second-review template for all release candidates, all
calibration negatives, a random 300 calibration positives, and all raw top-K
candidates.  No inter-rater agreement is claimed until independent labels are
filled.

Template: `outputs/milestones/scientific_domain_iwildcam_human_audit/second_review_blind_template.csv`

Status: `outputs/milestones/scientific_domain_iwildcam_human_audit/table_iwildcam_second_review_status.csv`

## Runtime / Compute Overhead

Added a compact domain-level runtime and compute-overhead table.  The table
separates PARC table-level certification from upstream proposal inference.

Table: `outputs/milestones/release_story/paper_diagnostics/table_runtime_compute_overhead_scientific_domains.csv`
