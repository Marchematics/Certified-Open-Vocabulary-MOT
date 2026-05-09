#!/usr/bin/env bash
set -euo pipefail

cd /home/waas/paper_experiments
source /home/waas/paper_experiments/env.sh

token_file="${1:-}"

exec /home/waas/paper_experiments/.venv/bin/python \
  /home/waas/paper_experiments/scripts/download_tao_hf_trainval.py \
  ${token_file:+--token-file "$token_file"} \
  --local-dir /home/waas/paper_experiments/data/TAO \
  --manifest /home/waas/paper_experiments/outputs/phase3_tao/tao_hf_trainval_download_manifest.json
