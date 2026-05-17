# Phase20 Paper Integration: Scientific Consequences Without New Human Annotation

This note converts `outputs/milestones/no_human_scientific_consequence/` from a reproducibility milestone into paper-facing impact evidence. It is downstream-only: no new human labels, no new experimental rows, and no protocol-only rows are promoted.

## Four Headline Numbers

1. **Materials follow-up queue.** ALIGNN-FF raw top-500 would send 163.4 unstable candidates to computational follow-up per seed (32.7% raw FTR). PARC releases 90.8 candidates with 5.2 unstable candidates (4.8% FTR), preventing 158.3 unstable follow-ups per seed.
2. **Materials high-volume refusal.** ALIGNN-FF raw top-5000 would send 2,577.4 unstable candidates to follow-up per seed (51.5% raw FTR). PARC refuses the unsupported high-volume request, preventing 2,577.4 unstable follow-ups per seed under the release/refusal interpretation.
3. **CTC lineage consequence.** In the noisy high-volume CTC link queue, raw K=5000 inserts 2,907.5 false lineage edges and 6,899.6 component-corruption proxy units per seed; PARC refuses before those edges enter the lineage graph.
4. **SpaceNet map consequence.** In the randomized SpaceNet same-building stress source, raw K=5000 inserts 3,381 false persistence links (67.6% raw false-link fraction), quantifying avoidable building-persistence map pollution under refusal.

## Proposed Results Section

### Release decisions change downstream scientific artifacts

We next asked whether the release-or-refuse decision changes downstream scientific objects without introducing new human audit. We therefore evaluated consequence-level endpoints using only public labels, official ground truth or existing model predictions. In materials discovery, the endpoint is the composition of a computational follow-up queue; in CTC, it is false lineage-edge insertion and component corruption; and in SpaceNet 7, it is false same-building persistence links. These analyses do not create new annotation sources. They translate the same certified release/refusal decisions into the scientific artifacts that would be passed downstream.

In the materials follow-up analysis, PARC reduced the number of unstable candidates that would enter the follow-up queue relative to the raw top-K decision, while preserving the distinction between certified release and certified refusal. Across the model-zoo frontier, CGCNN, ALIGNN-FF and MEGNet showed different raw-risk and power profiles, but the same release interface applied: supported budgets produced certified queues and unsupported high-volume requests were refused. In CTC, raw high-volume link lists inserted false lineage edges and corrupted lineage components, whereas PARC refused or restricted release before those edges entered the lineage graph. In SpaceNet 7, the same logic quantified false persistence links that can enter building-change maps under unsupported sources.

Thus the main consequence of PARC is not improved upstream prediction, but a changed scientific decision: which candidates are allowed to enter a downstream workflow under partial verification.

## Abstract Last-Sentence Replacement

PARC converts unconstrained ranked lists into auditable release-or-refuse decisions, preventing unsupported AI candidates from entering downstream scientific workflows when partial verification is insufficient.

## Figure 6 Caption Draft

**Figure 6 | Scientific consequences without new human annotation.** a, Materials follow-up queues under public WBM/Matbench labels: raw top-K unstable candidates, PARC-release unstable candidates and unstable follow-ups prevented for ALIGNN-FF at K=500 and K=5000. b, Materials model-zoo release/refusal frontier for locally available public prediction files (CGCNN, ALIGNN-FF and MEGNet) at alpha=0.10. Contemporary models without local public prediction files are listed as not-run in the supplement, not as completed evidence. c, CTC official-GT lineage consequence: false lineage edges prevented when high-volume or uninformative link queues are refused. d, SpaceNet 7 official-GT map consequence: false same-building persistence links quantified for geometry and randomized sources. All panels use completed public/official-label diagnostics and introduce no new human labels.

## Cover Letter Impact Block

Scientific AI systems increasingly produce candidate objects that can enter downstream workflows before exhaustive verification is available. This manuscript addresses the release decision itself: which AI-generated candidates should be published, and when should a system refuse to publish any candidate set?

We introduce PARC, a release-time certification layer for one-sided partial verification. PARC does not replace the upstream model. It converts a frozen ranked candidate list into either a certified release set or a certified refusal.

The manuscript now includes consequence-level analyses that require no new human annotation: public WBM/Matbench labels show how PARC changes materials follow-up queues; official CTC ground truth quantifies false lineage edges avoided; and SpaceNet building identities quantify false persistence links avoided. These analyses show that PARC changes the scientific artifacts passed downstream, not merely a benchmark score.

## Model-Zoo Provenance Language

The model-zoo frontier uses public prediction sources available in the local reproducibility package: CGCNN, ALIGNN-FF and MEGNet. Other contemporary sources are listed as not-run when public prediction files were not locally available under the same provenance constraints.

## Paper-Facing Tables

- `table_no_human_consequence_summary.csv`
- `figure_no_human_consequence_main.csv`
- `figure_no_human_consequence_main.pdf`
- `figure_materials_model_zoo_frontier.csv`
- `figure_materials_model_zoo_frontier.pdf`
