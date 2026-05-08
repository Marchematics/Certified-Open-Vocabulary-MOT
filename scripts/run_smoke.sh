#!/usr/bin/env bash
set -euo pipefail

cd /home/waas/paper_experiments
source /home/waas/paper_experiments/env.sh
source /home/waas/paper_experiments/.venv/bin/activate

python -m parc_track.cli smoke --config /home/waas/paper_experiments/configs/smoke.yaml
