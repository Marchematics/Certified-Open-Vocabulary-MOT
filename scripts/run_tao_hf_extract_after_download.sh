#!/usr/bin/env bash
set -euo pipefail

cd /home/waas/paper_experiments
source /home/waas/paper_experiments/env.sh

download_pid_file="/home/waas/paper_experiments/outputs/phase3_tao/tao_hf_trainval_download.pid"
extract_log="/home/waas/paper_experiments/outputs/phase3_tao/logs/tao_hf_trainval_extract.log"
mkdir -p "$(dirname "$extract_log")"

if [[ -f "$download_pid_file" ]]; then
  download_pid="$(cat "$download_pid_file")"
  if [[ -n "$download_pid" ]]; then
    while kill -0 "$download_pid" 2>/dev/null; do
      sleep 60
    done
  fi
fi

/home/waas/paper_experiments/.venv/bin/python \
  /home/waas/paper_experiments/scripts/extract_tao_hf_trainval.py \
  --local-dir /home/waas/paper_experiments/data/TAO \
  --download-manifest /home/waas/paper_experiments/outputs/phase3_tao/tao_hf_trainval.json \
  --extract-manifest /home/waas/paper_experiments/outputs/phase3_tao/tao_hf_trainval.json \
  >> "$extract_log" 2>&1

/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli dataset inspect \
  --config /home/waas/paper_experiments/configs/phase3_tao_full_train_inspect.yaml \
  --out /home/waas/paper_experiments/outputs/phase3_tao/dataset_adapter_report_tao_full_train.json \
  >> "$extract_log" 2>&1

/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli dataset inspect \
  --config /home/waas/paper_experiments/configs/phase3_tao_full_val_inspect.yaml \
  --out /home/waas/paper_experiments/outputs/phase3_tao/dataset_adapter_report_tao_full_val.json \
  >> "$extract_log" 2>&1
