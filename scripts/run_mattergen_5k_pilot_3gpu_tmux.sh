#!/usr/bin/env bash
set -euo pipefail

REPO=/home/waas/paper_experiments/github/Certified-Open-Vocabulary-MOT
MATTERGEN_REPO=/home/waas/paper_experiments/private/mattergen_repo
MATTERGEN_BIN=/home/waas/paper_experiments/private/mattergen_v4_conda/bin/mattergen-generate
GEN_ROOT=/home/waas/paper_experiments/private/mattergen_v4_generation
RUN_NAME=pilot_5k_3gpu
GEN_DIR=${GEN_ROOT}/${RUN_NAME}
MERGED_DIR=${GEN_ROOT}/${RUN_NAME}_merged
OUT_DIR=${REPO}/outputs/milestones/mattergen_parc_prospective_dft_followup
LOG_DIR=${GEN_ROOT}/${RUN_NAME}_logs
LOG=${LOG_DIR}/run.log
STATUS=${LOG_DIR}/status.txt

mkdir -p "${LOG_DIR}"
: > "${LOG}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "${LOG}"
}

log "MatterGen 5k three-GPU pilot runner started."
log "Generation root: ${GEN_DIR}"
log "Merged generation directory: ${MERGED_DIR}"

rm -rf "${GEN_DIR}" "${MERGED_DIR}"
mkdir -p "${GEN_DIR}" "${MERGED_DIR}"

declare -a GPUS=(0 1 2)
declare -a BATCHES=(84 83 83)
declare -a PIDS=()

wait_for_sampling() {
  local shard_name="$1"
  local shard_log="$2"
  local child_pid="$3"
  local max_wait_sec="${4:-900}"
  local waited=0
  while [[ "${waited}" -lt "${max_wait_sec}" ]]; do
    if grep -q "Generating samples" "${shard_log}" 2>/dev/null; then
      log "${shard_name} entered sampling loop after ${waited}s."
      return 0
    fi
    if ! kill -0 "${child_pid}" 2>/dev/null; then
      log "${shard_name} exited before sampling loop. See ${shard_log}"
      return 1
    fi
    sleep 10
    waited=$((waited + 10))
  done
  log "${shard_name} did not enter sampling loop within ${max_wait_sec}s. See ${shard_log}"
  return 1
}

cd "${MATTERGEN_REPO}"
for idx in 0 1 2; do
  shard="shard${idx}"
  shard_dir="${GEN_DIR}/${shard}"
  shard_log="${LOG_DIR}/${shard}.log"
  mkdir -p "${shard_dir}"
  log "Launching ${shard} on GPU ${GPUS[$idx]}: batch_size=20 num_batches=${BATCHES[$idx]}."
  (
    set -euo pipefail
    export CUDA_VISIBLE_DEVICES="${GPUS[$idx]}"
    export HF_HUB_OFFLINE=1
    export TRANSFORMERS_OFFLINE=1
    export OMP_NUM_THREADS=1
    export MKL_NUM_THREADS=1
    "${MATTERGEN_BIN}" "${shard_dir}" \
      --pretrained_name=mattergen_base \
      --batch_size=20 \
      --num_batches="${BATCHES[$idx]}" \
      --record_trajectories=False \
      --sampling_config_path="${MATTERGEN_REPO}/sampling_conf"
    test -f "${shard_dir}/generated_crystals_cif.zip"
  ) >> "${shard_log}" 2>&1 &
  PIDS+=("$!")
  wait_for_sampling "${shard}" "${shard_log}" "${PIDS[$idx]}" 900
done

failed=0
for idx in 0 1 2; do
  if wait "${PIDS[$idx]}"; then
    log "shard${idx} completed."
  else
    log "shard${idx} failed. See ${LOG_DIR}/shard${idx}.log"
    failed=1
  fi
done

if [[ "${failed}" != "0" ]]; then
  echo failed_generation_shard > "${STATUS}"
  exit 30
fi

log "Merging shard CIF zip files."
python - <<'PY' "${GEN_DIR}" "${MERGED_DIR}" >> "${LOG}" 2>&1
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import sys

gen_dir = Path(sys.argv[1])
merged_dir = Path(sys.argv[2])
merged_dir.mkdir(parents=True, exist_ok=True)
out_zip = merged_dir / "generated_crystals_cif.zip"
count = 0
with ZipFile(out_zip, "w", compression=ZIP_DEFLATED) as zout:
    for shard_dir in sorted(gen_dir.glob("shard*")):
        zip_path = shard_dir / "generated_crystals_cif.zip"
        if not zip_path.exists():
            raise FileNotFoundError(zip_path)
        with ZipFile(zip_path) as zin:
            for name in zin.namelist():
                if not name.endswith(".cif"):
                    continue
                arcname = f"{shard_dir.name}_{Path(name).name}"
                zout.writestr(arcname, zin.read(name))
                count += 1
print(f"merged_cif_count={count}")
if count < 5000:
    raise SystemExit(f"expected at least 5000 CIFs, found {count}")
PY

cd "${REPO}"
log "Parsing merged generated CIF metadata into public-safe artifact."
python scripts/parse_mattergen_generation_smoke.py \
  --generation-dir "${MERGED_DIR}" \
  --out-dir "${OUT_DIR}" \
  --stage pilot_5k_3gpu \
  --requested-candidates 5000 \
  --pretrained-name mattergen_base \
  --batch-size 20 \
  --num-batches 250 \
  >> "${LOG}" 2>&1

log "Running public-label exclusion and CHGNet/MACE consensus scoring diagnostic."
CUDA_VISIBLE_DEVICES=0 python scripts/run_mattergen_smoke_exclusion_scoring.py \
  --generation-dir "${MERGED_DIR}" \
  --out-dir "${OUT_DIR}" \
  --max-calibration-rows 240 \
  --max-sites 80 \
  --device cuda \
  >> "${LOG}" 2>&1

log "MatterGen 5k three-GPU pilot pipeline finished."
echo completed > "${STATUS}"
