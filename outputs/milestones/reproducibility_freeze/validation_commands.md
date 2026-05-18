# Validation Commands

```bash
python scripts/build_experimental_finalization_milestones.py
pytest -q tests
make validate-public-bundle
sha256sum -c MANIFEST_SHA256.txt
```

The A1/A2 materials prospective-validation rows remain protocol-only until
timestamped public-label snapshots or independent DFT joins are supplied.
