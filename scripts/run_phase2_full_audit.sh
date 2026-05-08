#!/usr/bin/env bash
set -euo pipefail

cd /home/waas/paper_experiments
source /home/waas/paper_experiments/env.sh

export PYTHONPATH=/home/waas/paper_experiments/code/parc_track
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"

python_bin=/home/waas/paper_experiments/.venv/bin/python

exec "$python_bin" -m parc_track.cli audit sample \
  --config /home/waas/paper_experiments/configs/phase2_audit_full.yaml \
  --dataset OVT-B \
  --out /home/waas/paper_experiments/outputs/phase2_full/audit_candidates.csv
