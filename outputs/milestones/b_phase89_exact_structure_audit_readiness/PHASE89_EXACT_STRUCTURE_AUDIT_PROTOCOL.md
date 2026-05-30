# Phase89 Exact-Structure Audit Protocol

Inputs:

- Phase87 frozen registry.
- Phase88 low-cost current-reference smoke.
- GNoME by-id zip endpoint: `https://storage.googleapis.com/gdm_materials_discovery/gnome_data/by_id.zip`.
- Materials Project current API credentials read from environment only.

Current phase boundary:

- No current-reference verdicts are produced.
- No exact-structure claim-decay metric is produced.
- Formula-only or id-only links are not counted as exact matches.

Next executable step:

```bash
python scripts/build_b_phase89_exact_structure_audit_readiness.py --download-gnome-zip
```

The downloaded zip remains outside version control.
