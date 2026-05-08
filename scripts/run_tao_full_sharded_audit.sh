#!/usr/bin/env bash
set -euo pipefail

ROOT=/home/waas/paper_experiments
BASE_CONFIG=${BASE_CONFIG:-"$ROOT/configs/phase3_tao_full_audit.yaml"}
OUT_DIR=${OUT_DIR:-"$ROOT/outputs/phase3_tao_full"}
SHARD_ROOT=${SHARD_ROOT:-"$OUT_DIR/shards"}
SHARDS=${SHARDS:-3}
DEVICES_STR=${CUDA_DEVICES:-"0 1 2"}
TOTAL_SAMPLES=${TOTAL_SAMPLES:-500}
TOP_B_PER_CELL=${TOP_B_PER_CELL:-15}

source "$ROOT/env.sh"
source "$ROOT/.venv/bin/activate"

# GroundingDINO/torch otherwise opens hundreds of CPU worker threads per process.
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-4}
export MKL_NUM_THREADS=${MKL_NUM_THREADS:-4}
export OPENBLAS_NUM_THREADS=${OPENBLAS_NUM_THREADS:-4}
export NUMEXPR_NUM_THREADS=${NUMEXPR_NUM_THREADS:-4}
export TOKENIZERS_PARALLELISM=false

rm -rf "$SHARD_ROOT"
mkdir -p "$SHARD_ROOT" "$OUT_DIR/logs"

python - "$BASE_CONFIG" "$SHARD_ROOT" "$SHARDS" <<'PY'
import sys
from pathlib import Path
import yaml

base_config = Path(sys.argv[1])
shard_root = Path(sys.argv[2])
shards = int(sys.argv[3])
cfg = yaml.safe_load(base_config.read_text())

for idx in range(shards):
    shard_dir = shard_root / f"shard_{idx:02d}"
    shard_dir.mkdir(parents=True, exist_ok=True)
    out_cfg = yaml.safe_load(yaml.safe_dump(cfg))
    proposal = out_cfg.setdefault("proposal", {})
    proposal["video_stride"] = shards
    proposal["video_offset"] = idx
    proposal["progress_every"] = int(proposal.get("progress_every", 25))
    out_cfg.setdefault("groundingdino", {})["device"] = "cuda:0"
    audit_export = out_cfg.setdefault("audit_export", {})
    audit_export["output_viewer"] = str(shard_dir / "audit_viewer")
    audit_export["montage_dir"] = str(shard_dir / "audit_viewer" / "montages")
    audit_export["clip_dir"] = str(shard_dir / "audit_viewer" / "clips")
    output = out_cfg.setdefault("output", {})
    output["candidates"] = str(shard_dir / "audit_candidates.csv")
    output["labels"] = str(shard_dir / "audit_labels.csv")
    output["manifest"] = str(shard_dir / "audit_manifest.json")
    output["summary"] = str(shard_dir / "audit_summary.csv")
    output["candidate_universe"] = str(shard_dir / "candidate_universe.csv")
    output["candidate_scores"] = str(shard_dir / "candidate_scores.csv")
    output["candidate_nodes"] = str(shard_dir / "candidate_nodes.csv")
    shard_cfg = shard_dir / "config.yaml"
    shard_cfg.write_text(yaml.safe_dump(out_cfg, sort_keys=False))
    print(shard_cfg)
PY

read -r -a DEVICES <<< "$DEVICES_STR"
pids=()
idx=0
for cfg in "$SHARD_ROOT"/shard_*/config.yaml; do
  shard_dir=$(dirname "$cfg")
  device=${DEVICES[$((idx % ${#DEVICES[@]}))]}
  echo "[tao-sharded] starting shard $idx on CUDA_VISIBLE_DEVICES=$device: $cfg"
  (
    cd "$ROOT"
    CUDA_VISIBLE_DEVICES="$device" python -m parc_track.cli audit sample \
      --config "$cfg" \
      --dataset TAO \
      --out "$shard_dir/audit_candidates.csv"
  ) > "$shard_dir/audit.log" 2>&1 &
  pids+=("$!")
  idx=$((idx + 1))
done

failed=0
for pid in "${pids[@]}"; do
  if ! wait "$pid"; then
    failed=1
  fi
done
if [[ "$failed" -ne 0 ]]; then
  echo "[tao-sharded] one or more shards failed; inspect $SHARD_ROOT/shard_*/audit.log" >&2
  exit 1
fi

python "$ROOT/scripts/merge_audit_shards.py" \
  --shard-root "$SHARD_ROOT" \
  --out-dir "$OUT_DIR" \
  --total-samples "$TOTAL_SAMPLES" \
  --top-b-per-cell "$TOP_B_PER_CELL"

python -m parc_track.cli audit summarize \
  --candidates "$OUT_DIR/audit_candidates.csv" \
  --labels "$OUT_DIR/audit_labels.csv" \
  --out "$OUT_DIR/audit_summary.csv"
