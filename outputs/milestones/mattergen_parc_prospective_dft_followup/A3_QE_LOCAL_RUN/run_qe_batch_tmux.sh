#!/usr/bin/env bash
set -euo pipefail
ARM="${1:-PARC-release-full}"
NP="${NP:-4}"
MAX_PARALLEL="${MAX_PARALLEL:-3}"
LIMIT="${LIMIT:-0}"
RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOB_LIST="$RUN_DIR/job_lists/$ARM.txt"
if [ ! -f "$JOB_LIST" ]; then
  echo "missing job list: $JOB_LIST" >&2
  exit 2
fi
count=0
while read -r job_id; do
  [ -z "$job_id" ] && continue
  if [ "$LIMIT" -gt 0 ] && [ "$count" -ge "$LIMIT" ]; then
    break
  fi
  while [ "$(jobs -rp | wc -l)" -ge "$MAX_PARALLEL" ]; do
    sleep 10
  done
  echo "$(date -Is) starting $job_id arm=$ARM np=$NP"
  bash "$RUN_DIR/run_qe_job.sh" "$job_id" "$NP" &
  count=$((count + 1))
done < "$JOB_LIST"
wait
echo "$(date -Is) completed batch arm=$ARM count=$count"
