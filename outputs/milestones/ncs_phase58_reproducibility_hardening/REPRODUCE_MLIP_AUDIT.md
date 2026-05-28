# Reproduce Candidate-Level MLIP Audits

Run:

```bash
make reproduce-materials-mlip-audit
```

This target rebuilds two scoped materials audit layers:

- Phase51 candidate-level explanation with ALIGNN-FF, CGCNN and MEGNet
  model-zoo scores.
- Phase53 candidate-level CHGNet/MACE score-support audit when the local
  private WBM raw-structure cache is available.

The Phase53 CHGNet/MACE columns are raw energy-per-atom score proxies, not
reference-hull e_above_hull values. They support a queue-level release-vs-tail
score contrast and must not be cited as DFT evidence, strict t1 alpha control,
or prospective materials discovery.
