# PARC-Track Clean Results Bundle

Created: 2026-05-08T18:48:45

## Cleaning Policy

Included:
- Source code, tests, configs, scripts, docs.
- Paper figures.
- Current clean milestones: full OVT-B, clean TAO, cross-dataset v6.
- Current derived experiment outputs for phase2/phase3 OVT-B and TAO: CSV/JSON/YAML/MD/TEX/PDF/PNG.

Excluded as contamination/noise:
- Raw datasets under `data/`.
- Virtualenvs, pip/HF caches, temp downloads, third-party repos, tools.
- Model weights, archive downloads, wheels.
- `__pycache__`, `.pyc`, logs, watcher pid/status files.
- Stale backup labels such as `audit_labels.before_*`.
- Obsolete milestone bundles v1-v5 where superseded by v6.

Security cleaning:
- Token-shaped Hugging Face values were redacted in staged text files.
- Final staged scan found 0 raw HF-token pattern matches.

TAO audit cleaning:
- `outputs/milestones/ijcv_tao_full_v2_clean/audit_summary_clean.csv` counts only the original 500 TAO audit candidates.
- Supplemental released-unsupported labels remain in `outputs/phase3_tao_full/audit_labels.csv`, but are not used to inflate the 500-candidate audit rate denominator.

Validation:
- Latest test run before this clean bundle: `36 passed`.
- Use `MANIFEST_SHA256.txt` for file-level verification.
