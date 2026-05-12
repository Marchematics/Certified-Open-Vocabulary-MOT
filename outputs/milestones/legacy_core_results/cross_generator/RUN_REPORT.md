# OWLv2 GPU Run Report

- Start time: 2026-05-08T19:39:47+08:00
- Host: waas
- Working directory: <PARC_ROOT>
- Python: Python 3.12.4
- parc-track: <PARC_ROOT>/.venv/bin/parc-track

## GPU
0, NVIDIA A10G, 24564 MiB, 590.44.01

## Commands
- `parc-track phase2 propose --config configs/phase3_ovtb_owlv2_audit.yaml`
- `parc-track phase2 propose --config configs/phase3_tao_owlv2_audit.yaml`
- `parc-track phase3 matrix --config configs/phase3_ovtb_owlv2_matrix.yaml`
- `parc-track phase3 matrix --config configs/phase3_tao_owlv2_matrix.yaml`
- `parc-track phase3 export-release-audit --config configs/phase3_ovtb_owlv2_matrix.yaml --unsupported-only`
- `parc-track phase3 export-release-audit --config configs/phase3_tao_owlv2_matrix.yaml --unsupported-only`
- `parc-track phase3 cross-generator-report --config configs/phase3_cross_generator_report.yaml`

- End time: 2026-05-08T22:40:00+08:00
- SHA256 manifest: <PARC_ROOT>/outputs/milestones/cross_generator/MANIFEST_SHA256.txt

- Post-run note: regenerated OWLv2 CPU matrices and cross-generator table after conservative FTR metric cleanup at 2026-05-08T22:43:42+08:00
