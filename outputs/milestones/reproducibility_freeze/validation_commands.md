# Validation Commands

```bash
python scripts/build_experimental_finalization_milestones.py
pytest -q tests
make validate-public-bundle
sha256sum -c MANIFEST_SHA256.txt
```

A1 remains protocol-only until timestamped public-label snapshots are supplied.
A2 contains a completed low-coverage OQMD exact-structure diagnostic and is not
promoted as primary independent validation evidence.
