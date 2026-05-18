# Public Outputs

This directory contains public-safe derived artifacts only.

- `milestones/reliability_fortress/`: final frozen experiment/result bundle.
- `milestones/generality_reliability/`: non-tracking generality and stratified reliability artifacts.
- `milestones/release_story/`: compact release/refusal story tables and qualitative-example manifest.
- `milestones/scientific_domain_ctc/`: biomedical cell-link certification on public Cell Tracking Challenge training data.
- `milestones/scientific_domain_ctc_learned/`: learned-hybrid, appearance-assisted CTC link proposal source certified on held-out sequences, with leakage, reverse-split, and negative-control checks.
- `milestones/ctc_strict_human_audit/`: human-confirmed CTC strict-audit closeout; the simulated strict-release queue has human FTR 0.0 and conservative uncertain-as-false FTR 0.0.
- `milestones/scientific_domain_spacenet7/`: Earth-observation building-link certification on public SpaceNet 7 labels.
- `milestones/scientific_domain_spacenet7_prospective/`: prospective SpaceNet 7 audit-trial package and no-go closeout.
- `milestones/scientific_domain_iwildcam_human_audit/`: prospective iWildCam animal-present human-audit package; operational `alpha=0.20, K=50` human-confirmed ecology release with strict `alpha=0.10` refusal.
- `milestones/scientific_domain_materials/`: Matbench Discovery / WBM materials-candidate release package; CGCNN learned model strict `alpha=0.10, K=100` release with DFT-label holdout evaluation, controls, and paper-ready threshold/gamma/raw-vs-PARC figures.
- `milestones/scientific_release_success_map/`: consolidated domain-of-success evidence map and practitioner diagnostics across completed release, refusal, boundary, and protocol-only rows, including refusal/ILP aggregate diagnostics, verified-positive-removal load-bearing reruns, a descriptive success-domain predictor, and validity assumptions by domain.
- `milestones/no_human_scientific_consequence/`: no-new-human-label consequence package using public WBM/Matbench labels, public model prediction CSVs, CTC official GT labels, and SpaceNet 7 official building identities; includes paper-facing Figure 6 sources and impact-first manuscript/cover-letter text.
- `milestones/materials_computational_followup_trial/`: quasi-prospective materials computational follow-up replay using frozen public model queues, pre-release partial DFT-positive verification, and held-out public DFT labels for follow-up evaluation; no new DFT calculations or synthesis claim.
- `milestones/official_downstream_consequence/`: official-label downstream artifact metrics for CTC and SpaceNet 7. CTC reports lineage-edge false-link, conflict, component-corruption, and TRA/AOGM-style edit-burden proxies; SpaceNet reports building-persistence false-link, chain, and map-edit proxies. These are not official challenge leaderboard scores.
- `milestones/release_certification_benchmark/`: community-facing scientific AI release-card package. It standardizes completed CTC, materials, iWildCam, SpaceNet, and downstream-artifact evidence into release cards, a track registry, a field schema, and a governance checklist; no protocol-only row is promoted as completed evidence.
- `milestones/block_heterogeneity_robustness/`: Phase25 block-size heterogeneity diagnostics. Materials rows use candidate-level block/score/label artifacts for size-stratified, size-matched, and downsampled block-max stress checks; CTC and SpaceNet rows are scoped aggregate/audit-sample diagnostics because the public package does not include their full candidate-level universes.
- `milestones/materials_prospective_validation_protocols/`: A1 temporal-split and A2 independent-DFT preregistration protocols with feasibility/go-no-go cards. These files are protocol/feasibility artifacts only and do not report a completed prospective materials result.
- `milestones/materials_prospective_dft_followup/`: A3 prospective in-silico DFT follow-up protocol freeze. It fixes the ALIGNN-FF `alpha=0.10, K=500` design, 40/40/40 arm plan, public-label exclusion schema, novelty-crossmatch schema, DFT failure policy, and empty selection/job schemas. It is a blocked/protocol-only record and is not completed DFT evidence.
- `milestones/materials_prospective_dft_followup_chgnet_v2/`: A3-v2 locally executable CHGNet scorer gate on PGCGM candidates. It scores WBM calibration representatives and PGCGM candidates but exports no DFT jobs because the predeclared PARC release arm is empty.
- `milestones/materials_prospective_dft_followup_chgnet_v3/`: A3-v3 near-hull isovalent/chemically similar substitution gate. It generates 5,000 public-label-excluded candidates, scores them with CHGNet, evaluates strict and operational endpoints, and exports no DFT jobs because all endpoints refuse.
- `milestones/mattergen_parc_prospective_dft_followup/`: A3-v4 frontier-generator protocol gate. It records a local MatterGen import/CLI smoke check and MACE-MP smoke check, then freezes the MatterGen + CHGNet/MACE consensus scoring protocol. Candidate generation has not been run, so public-label exclusion, consensus scoring, PARC selection, and DFT manifests remain empty and no positive result is claimed.
- `benchmarks/parc_certification_benchmark/`: compact community benchmark package with audit labels, result tables, schemas, and a tiny fixture.

Raw videos, raw annotations, model weights, detector caches, frame caches, and montage images are intentionally excluded.
