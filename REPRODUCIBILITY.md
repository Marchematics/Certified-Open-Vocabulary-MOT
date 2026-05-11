# Reproducibility Guide

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e code/parc_track
pip install numpy scipy pandas opencv-python pyyaml tqdm pytest motmetrics pycocotools pillow matplotlib
pytest -q tests
```

## 2. Verify Tiny Fixture

```bash
python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api
```

Expected outputs include candidate schema files, an audit-label fixture, and API documentation.

## 3. Verify Frozen Tables

The final public milestone is:

```text
outputs/milestones/tpami_reliability_fortress_v2/
```

Check file integrity with:

```bash
sha256sum -c MANIFEST_SHA256.txt
```

## 4. Re-run with External Datasets

The configs are sanitized and may contain `${PARC_TRACK_ROOT}` placeholders. Materialize a local runnable copy:

```bash
python scripts/materialize_configs.py --root /path/to/local/parc-track --out configs_local
```

Then place or symlink external datasets and candidate universes according to the target config. Example commands:

```bash
python -m parc_track.cli phase3 matrix --config configs_local/phase3_ovtb_full_matrix.yaml
python -m parc_track.cli phase9 freeze-tpami-v2 --output-dir outputs/milestones/tpami_reliability_fortress_v2_rerun
```

## 5. External Proposal Generators

PARC-Track expects candidate-path CSV/JSON tables, not raw model internals. Use official detector/tracker repositories for inference, then convert predictions into the schema in `docs/API.md`.

## 6. Public Safety

Do not commit raw videos, raw annotations, weights, cache directories, or private credentials. The included `scripts/validate_public_bundle.py` checks common leakage patterns.
