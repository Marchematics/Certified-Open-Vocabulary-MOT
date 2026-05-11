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
