# Reproducibility Guide

## 1. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e code/parc_track
pip install numpy scipy pandas opencv-python pyyaml tqdm pytest motmetrics pycocotools pillow matplotlib shapely tifffile imagecodecs
pytest -q tests
```

Equivalent Makefile entry:

```bash
make test PYTHON=python
```

## 2. Verify Tiny Fixture

```bash
python -m parc_track.cli phase9 certification-api --output-dir outputs/tmp_cert_api
```

Expected outputs include candidate schema files, an audit-label fixture, and API documentation.

## 3. Verify Frozen Tables

The core public milestones are:

```text
outputs/milestones/reliability_fortress/
outputs/milestones/scientific_domain_ctc/
outputs/milestones/scientific_domain_ctc_learned/
outputs/milestones/scientific_domain_spacenet7/
outputs/milestones/scientific_domain_spacenet7_prospective/
outputs/milestones/scientific_domain_materials/
outputs/milestones/scientific_release_success_map/
outputs/milestones/generality_reliability/
outputs/milestones/release_story/
outputs/benchmarks/parc_certification_benchmark/
```

Check file integrity with:

```bash
sha256sum -c MANIFEST_SHA256.txt
```

Public-bundle safety checks:

```bash
make validate-public-bundle PYTHON=python
make verify-manifest
```

The learned-hybrid CTC milestone includes public-safe leakage and robustness checks:

```text
outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_leakage_audit.csv
outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_reverse_split.csv
outputs/milestones/scientific_domain_ctc_learned/table_ctc_learned_negative_control.csv
```

The materials-discovery milestone can be regenerated from the public WBM summary
and public Matbench Discovery prediction CSVs once those files are available
locally:

```bash
python scripts/run_materials_discovery_parc_flagship.py
```

The script writes only public-safe tables to
`outputs/milestones/scientific_domain_materials/`; raw crystal structures and
model weights are not needed.

Regenerate the current paper-facing release/refusal tables:

```bash
make reproduce-main-tables PYTHON=python
```

The cross-domain success/refusal map can also be regenerated directly:

```bash
python -m parc_track.cli phase19 success-domain
```

## 4. Re-run with External Datasets

The configs are sanitized and may contain `${PARC_TRACK_ROOT}` placeholders. Materialize a local runnable copy:

```bash
python scripts/materialize_configs.py --root /path/to/local/parc-track --out configs_local
```

Then place or symlink external datasets and candidate universes according to the target config. Example commands:

```bash
python -m parc_track.cli phase3 matrix --config configs_local/phase3_ovtb_full_matrix.yaml
python -m parc_track.cli phase9 reliability-bundle --output-dir outputs/milestones/reliability_fortress_rerun
```

## 5. External Proposal Generators

PARC-Track expects candidate-path CSV/JSON tables, not raw model internals. Use official detector/tracker repositories for inference, then convert predictions into the schema in `docs/API.md`.

## 6. Parallel Certification Safety

Candidate universes should be treated as immutable inputs. During the iWildCam
parallel deployment we identified that an earlier certification path normalized
split/audit state and wrote it back to the input `candidate_universe.csv`, which
is unsafe when multiple risk levels or budgets share the same file in parallel.
The current code writes that normalized state to a per-run
`normalized_candidate_universe.csv` sidecar and leaves the input file unchanged.
The regression test `test_real_certify_does_not_write_back_to_input_candidate_universe`
checks this behavior.

## 7. Public Safety

Do not commit raw videos, raw annotations, weights, cache directories, or private credentials. The included `scripts/validate_public_bundle.py` checks common leakage patterns.
