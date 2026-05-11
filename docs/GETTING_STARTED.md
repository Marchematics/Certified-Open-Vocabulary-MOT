# Getting Started

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e code/parc_track
pip install numpy scipy pandas opencv-python pyyaml tqdm pytest motmetrics pycocotools pillow matplotlib
```

## Run Tests

```bash
pytest -q tests
```

## Run Tiny Fixture

```bash
python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api
```

## Use Your Own Tracker

1. Export your tracker predictions as paths or per-frame rows.
2. Convert them to `candidate_universe.csv` and `candidate_nodes.csv` following `docs/API.md`.
3. Provide optional audit labels for known reliable positives.
4. Run the relevant `parc_track.cli` command or import the calibration/selector modules directly.
