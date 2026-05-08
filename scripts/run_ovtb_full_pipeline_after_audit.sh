#!/usr/bin/env bash
set -euo pipefail

cd /home/waas/paper_experiments
source /home/waas/paper_experiments/env.sh
export PYTHONPATH=/home/waas/paper_experiments/code/parc_track

pid_file=/home/waas/paper_experiments/outputs/phase2_full/full_audit.pid
audit_manifest=/home/waas/paper_experiments/outputs/phase2_full/audit_manifest.json
log_dir=/home/waas/paper_experiments/outputs/phase3_ovtb_full/logs
mkdir -p "$log_dir"

if [[ -f "$pid_file" ]]; then
  pid="$(cat "$pid_file")"
  while kill -0 "$pid" 2>/dev/null; do
    sleep 60
  done
fi

if [[ ! -f "$audit_manifest" ]]; then
  echo "missing audit manifest: $audit_manifest" >&2
  exit 2
fi

status="$(/home/waas/paper_experiments/.venv/bin/python - <<'PY'
import json
p='/home/waas/paper_experiments/outputs/phase2_full/audit_manifest.json'
print(json.load(open(p)).get('status',''))
PY
)"
if [[ "$status" != "completed" ]]; then
  echo "audit manifest status is not completed: $status" >&2
  exit 3
fi

/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli real ovtb-matrix \
  --config /home/waas/paper_experiments/configs/phase3_ovtb_full_matrix.yaml \
  > "$log_dir/ovtb_full_matrix.log" 2>&1

/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli real tune-m \
  --config /home/waas/paper_experiments/configs/phase3_ovtb_full_matrix.yaml \
  > "$log_dir/ovtb_full_tune_m.log" 2>&1

/home/waas/paper_experiments/.venv/bin/python -m parc_track.cli report tpami-core \
  --config /home/waas/paper_experiments/configs/phase3_paper_export_full.yaml \
  > "$log_dir/ovtb_full_report.log" 2>&1
