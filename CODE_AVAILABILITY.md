# Code Availability

The PARC-Track implementation is available under `code/parc_track`.

Core modules include:

- `calibration.py`: block calibration and e-value utilities.
- `selector.py`: SCS-Greedy self-consistent release selection.
- `diagnostics.py`, `reports.py`, `metrics.py`: UTR/FTR diagnostics and report export.
- `phase2.py` through `phase10.py`: reproducibility entry points for the experiment pipeline.
- `ovtrack_adapter.py`: published-tracker output conversion helpers.
- `cli.py`: command line entry point.

Detector/tracker inference implementations are not vendored. Use each detector/tracker's official repository and convert outputs to the PARC schema described in `docs/API.md`.

## Reproducibility Entry Points

- Tiny fixture:

  ```bash
  PYTHONPATH=code/parc_track python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api
  ```

- Cross-domain success map:

  ```bash
  PYTHONPATH=code/parc_track python -m parc_track.cli phase19 success-domain
  ```

- Experiment-finalization milestones:

  ```bash
  python scripts/build_experimental_finalization_milestones.py
  ```

  This script consolidates completed evidence and explicitly marks A1/A2/A3
  unfinished rows as protocol-only or diagnostic. It does not run new DFT or
  promote protocol gates into completed evidence.

- Tests:

  ```bash
  PYTHONPATH=code/parc_track python -m pytest -q tests
  ```

## Public-Safe Scripts

Scripts under `scripts/` build derived tables, closeout reports, bundle checks,
and audit packages.  They intentionally operate on candidate-universe tables and
public-safe derived artifacts rather than raw videos/images or model internals.

## Continuous Integration

The GitHub Actions workflow in `.github/workflows/tests.yml` installs the
package, runs the test suite, validates selected public bundles, and verifies
the root SHA256 manifest.
