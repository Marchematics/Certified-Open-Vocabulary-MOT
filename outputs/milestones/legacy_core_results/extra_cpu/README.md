# IJCV Extra CPU v1

Frozen on 2026-05-09.

This milestone contains CPU/post-processing IJCV add-on experiments beyond the core Phase-4 bundle:

- TrackEval HOTA/CLEAR/Identity tables for OVT-B and TAO supported-subset.
- Confidence calibration baselines: raw threshold, temperature-scaled threshold, Platt threshold, and Platt top-M no-risk.
- Cell-aware Mondrian granularity ablation: global/category/query/category+occ without silent global fallback.

Caveats:

- Confidence baselines have no finite-sample risk certificate.
- TAO TrackEval is supported-subset scaffold, not dense federated TAO evaluation.
- Cell-aware Mondrian ablation is a diagnostic runner; the main real-cert scaffold uses global fallback unless explicitly configured otherwise.

Verification: `pytest -q <PARC_ROOT>/tests` -> 45 passed, 1 warning.
