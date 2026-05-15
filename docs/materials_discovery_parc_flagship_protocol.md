# Materials Discovery PARC Flagship Protocol

## Scope

This protocol instantiates PARC on a non-visual scientific candidate-release task:
certified release of DFT-stable inorganic crystal candidates from a learned
materials model under one-sided partial verification.

The experiment is retrospective: public Matbench Discovery / WBM DFT labels are
masked to create observed one-sided stable positives for PARC, while the full DFT
labels are used only after release to compute actual FTR.

## Candidate Unit

One candidate is one inorganic crystal structure from the WBM benchmark test set.
The target event is:

`Y=1`: the candidate is DFT-stable, with `e_above_hull <= 0 eV/atom`.

`Y=0`: the candidate is DFT-unstable.

## Proposal Sources

Primary source:

- CGCNN 10-member ensemble public WBM IS2RE predictions.
- Score: negative predicted energy above hull.
- Predicted energy above hull is computed from the public predicted formation
  energy and the WBM hull-reference energy, matching the Matbench Discovery
  stability-evaluation convention.

Controls:

- MEGNet public WBM IS2RE predictions as a weaker learned source.
- Random-score control on the same candidate universe.

No model weights or raw crystal structures are redistributed in the public
artifact.

## Partial Verification

PARC observes only a masked subset of DFT-stable positives:

- `rho in {0.05, 0.10}`.
- Primary observed-positive strategy: top-score stable candidates.
- Unobserved candidates are not trusted negatives; they remain in the null
  superset.

The full DFT stability labels are used only for held-out actual-FTR evaluation.

## Blocks

Primary block:

- `composition_family_pair = n_elements | first_two_sorted_elements`.

This is a chemistry-aware coarsening of exact chemical-system blocks.  Exact
chemical-system blocks are too sparse for a stable negative control and are
therefore reported as sensitivity rather than the primary operating point.

Sensitivity blocks:

- exact chemical system;
- Wyckoff-family block.

Random blocks are not used as a primary validity claim.

## Predeclared Endpoints

Primary strict endpoint:

- source: CGCNN ensemble;
- block: `composition_family_pair`;
- `rho=0.10`;
- `alpha=0.10`;
- `K=100`;
- pass gate: at least 18/20 non-empty seeds and mean actual FTR <= 0.10.

Stronger sensitivity endpoint:

- same as primary, but `K=300`;
- reported as sensitivity unless it also satisfies actual FTR <= 0.10.

Operational endpoint:

- `alpha=0.20`, larger K values;
- used only as sensitivity, not as the strict flagship.

## Leakage Controls

The public tables must report:

- prediction source and SHA256 of local downloaded inputs;
- that DFT target labels are not used for ranking;
- that full DFT labels are used only for observed-positive masking and final
  actual-FTR evaluation;
- that the WBM hull reference is used only to transform public formation-energy
  predictions into predicted energy-above-hull scores;
- random-score and weak-model controls;
- block sensitivity.

## Paper Framing

If the primary strict endpoint passes, this result may be described as a strict
materials-discovery candidate-release flagship.

It must not be described as discovering new materials, improving a materials
model, or validating experimental synthesizability.
