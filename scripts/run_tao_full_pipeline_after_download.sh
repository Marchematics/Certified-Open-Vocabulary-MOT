#!/usr/bin/env bash
set -euo pipefail

cd /home/waas/paper_experiments
source /home/waas/paper_experiments/env.sh

status_file="/home/waas/paper_experiments/outputs/phase3_tao/tao_hf_extract_watcher_status.json"
log_file="/home/waas/paper_experiments/outputs/phase3_tao_full/logs/tao_full_pipeline.log"
mkdir -p "$(dirname "$log_file")"

echo "[tao-full] waiting for TAO download/extract completion" >> "$log_file"
while true; do
  if [[ -f "$status_file" ]]; then
    status="$(
      /home/waas/paper_experiments/.venv/bin/python - <<'PY'
import json
p='/home/waas/paper_experiments/outputs/phase3_tao/tao_hf_extract_watcher_status.json'
try:
    print(json.load(open(p)).get('status',''))
except Exception:
    print('')
PY
    )"
    if [[ "$status" == "completed" ]]; then
      break
    fi
    if [[ "$status" == "failed" || "$status" == "download_not_complete" ]]; then
      echo "[tao-full] upstream watcher status=$status; aborting" >> "$log_file"
      exit 3
    fi
  fi
  sleep 120
done

echo "[tao-full] merging TAO train/validation annotations" >> "$log_file"
/home/waas/paper_experiments/.venv/bin/python \
  /home/waas/paper_experiments/scripts/merge_tao_train_val_annotations.py \
  >> "$log_file" 2>&1

echo "[tao-full] inspecting trainval layout" >> "$log_file"
/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli dataset inspect \
  --config /home/waas/paper_experiments/configs/phase3_tao_trainval_inspect.yaml \
  --out /home/waas/paper_experiments/outputs/phase3_tao_full/dataset_adapter_report_tao_trainval.json \
  >> "$log_file" 2>&1

echo "[tao-full] running GroundingDINO TAO full candidate generation" >> "$log_file"
/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli audit sample \
  --config /home/waas/paper_experiments/configs/phase3_tao_full_audit.yaml \
  --dataset TAO \
  --out /home/waas/paper_experiments/outputs/phase3_tao_full/audit_candidates.csv \
  >> "$log_file" 2>&1

echo "[tao-full] summarizing TAO audit template" >> "$log_file"
/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli audit summarize \
  --candidates /home/waas/paper_experiments/outputs/phase3_tao_full/audit_candidates.csv \
  --labels /home/waas/paper_experiments/outputs/phase3_tao_full/audit_labels.csv \
  --out /home/waas/paper_experiments/outputs/phase3_tao_full/audit_summary.csv \
  >> "$log_file" 2>&1 || true

echo "[tao-full] running TAO alpha/seed/M matrix using shared real-data matrix engine" >> "$log_file"
/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli real ovtb-matrix \
  --config /home/waas/paper_experiments/configs/phase3_tao_full_matrix.yaml \
  >> "$log_file" 2>&1
cp -f /home/waas/paper_experiments/outputs/phase3_tao_full/ovtb_alpha_seed_m_matrix.csv \
  /home/waas/paper_experiments/outputs/phase3_tao_full/tao_alpha_seed_m_matrix.csv
cp -f /home/waas/paper_experiments/outputs/phase3_tao_full/ovtb_matrix_summary.json \
  /home/waas/paper_experiments/outputs/phase3_tao_full/tao_matrix_summary.json

echo "[tao-full] running TAO tune-M selection" >> "$log_file"
/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli real tune-m \
  --config /home/waas/paper_experiments/configs/phase3_tao_full_matrix.yaml \
  >> "$log_file" 2>&1

echo "[tao-full] freezing TAO IJCV milestone bundle" >> "$log_file"
/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli report tpami-core \
  --config /home/waas/paper_experiments/configs/phase3_paper_export_tao_full.yaml \
  >> "$log_file" 2>&1

echo "[tao-full] completed" >> "$log_file"
