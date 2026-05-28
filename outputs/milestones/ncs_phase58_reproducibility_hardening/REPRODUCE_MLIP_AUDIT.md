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
- Phase60 PARC-V support-gate feasibility audit.
- Phase61 PARC-M multi-evidence fusion feasibility audit.

The Phase53 CHGNet/MACE columns are raw energy-per-atom score proxies, not
reference-hull e_above_hull values. They support a queue-level release-vs-tail
score contrast and must not be cited as DFT evidence, strict t1 alpha control,
or prospective materials discovery.

Run:

```bash
make reproduce-ncs-phase60-parc-v-version-aware-release
```

to regenerate the PARC-V support-gate feasibility audit. Phase60 is a no-go
for a headline version-aware release claim: CHGNet/MACE support-gating is
non-empty but does not materially lower current-MP t1 FTR and is not a full SCS
rerun.

Run:

```bash
make reproduce-ncs-phase61-parc-m-multi-evidence-fusion
```

to regenerate the PARC-M fusion audit. Phase61 gives a medium empirical signal
but is not claim-ready: the auxiliary CHGNet/MACE components are queue-level
score proxies, not full null-superset calibration e-values.
