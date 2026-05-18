#!/usr/bin/env bash
set -euo pipefail
SESSION="${SESSION:-a3_qe_parc_release}"
RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
tmux has-session -t "$SESSION" 2>/dev/null && {
  echo "tmux session already exists: $SESSION" >&2
  exit 3
}
tmux new-session -d -s "$SESSION" "cd '$RUN_DIR' && NP=${NP:-4} MAX_PARALLEL=${MAX_PARALLEL:-3} bash '$RUN_DIR/run_qe_batch_tmux.sh' PARC-release-full"
echo "$SESSION"
