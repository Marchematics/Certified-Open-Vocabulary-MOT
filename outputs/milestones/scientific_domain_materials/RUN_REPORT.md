# Materials Discovery PARC Flagship Closeout

Decision: **GO_strict_alpha010_K100_materials_flagship**.

This milestone instantiates PARC on a non-visual scientific candidate-release task:
certified release of DFT-stable inorganic crystal candidates from public Matbench
Discovery / WBM predictions.

Primary endpoint:

- Source: CGCNN 10-member learned graph-neural-network ensemble.
- Unit: one inorganic crystal candidate.
- Verification: masked DFT-stable positives; full DFT labels are used only for
  held-out actual-FTR evaluation.
- Primary block: `composition_family_pair`, a chemistry-aware coarsening of
  chemical systems.
- `rho=0.10`, `alpha=0.10`, `K=100`: 20/20
  non-empty seeds, mean release 100.00, mean
  actual FTR 0.0300, raw top-K actual FTR
  0.0300.

The stronger `K=300` endpoint is reported as sensitivity, not the flagship gate:
20/20 non-empty seeds with mean actual FTR
0.0916.  Random-score and weak-model controls
are included to show source quality and block design matter.

Additional robustness closeouts:

- `table_materials_stability_threshold_robustness.csv` reruns the materials
  release under exact stability, 25 meV/atom tolerance-positive labels,
  margin-excluded labels, and conservative clear-stable observed positives.
- `table_materials_gamma_sensitivity.csv` reruns the primary materials rows
  under a fixed gamma grid from 0.05 to 0.50. The fixed-gamma grid is a
  sensitivity diagnostic, not a replacement for the preregistered
  finite-resolution gamma rule.

Scope note: this is a retrospective Matbench Discovery release simulation using
public DFT labels.  It is not a claim of new materials discovery, and raw
structures/model weights are not redistributed.
