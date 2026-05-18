#!/usr/bin/env bash
set -euo pipefail

REPO=/home/waas/paper_experiments/github/Certified-Open-Vocabulary-MOT
MATTERGEN_REPO=/home/waas/paper_experiments/private/mattergen_repo
MATTERGEN_BIN=/home/waas/paper_experiments/private/mattergen_v4_conda/bin/mattergen-generate
GEN_ROOT=/home/waas/paper_experiments/private/mattergen_v4_generation
GEN_DIR=${GEN_ROOT}/pilot_5k_tmux
OUT_DIR=${REPO}/outputs/milestones/mattergen_parc_prospective_dft_followup
LOG_DIR=${GEN_ROOT}/pilot_5k_tmux_logs
LOG=${LOG_DIR}/run.log
STATUS=${LOG_DIR}/status.txt

mkdir -p "${GEN_DIR}" "${LOG_DIR}"
cd "${REPO}"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "${LOG}"
}

compute_apps_count() {
  nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | sed '/^$/d' | wc -l
}

log "MatterGen 5k pilot runner started."
log "Generation directory: ${GEN_DIR}"
log "Waiting for GPU compute contexts to clear."
for attempt in $(seq 1 180); do
  count=$(compute_apps_count)
  if [[ "${count}" == "0" ]]; then
    log "GPU compute contexts are clear."
    break
  fi
  log "GPU busy (${count} compute contexts); waiting 60s. attempt=${attempt}/180"
  sleep 60
  if [[ "${attempt}" == "180" ]]; then
    log "GPU wait timed out."
    echo failed_gpu_wait_timeout > "${STATUS}"
    exit 20
  fi
done

log "Starting MatterGen generation: batch_size=20 num_batches=250 target=5000."
cd "${MATTERGEN_REPO}"
CUDA_VISIBLE_DEVICES=0 "${MATTERGEN_BIN}" "${GEN_DIR}" \
  --pretrained_name=mattergen_base \
  --batch_size=20 \
  --num_batches=250 \
  --record_trajectories=False \
  --sampling_config_path="${MATTERGEN_REPO}/sampling_conf" \
  >> "${LOG}" 2>&1

log "MatterGen generation finished."
if [[ ! -f "${GEN_DIR}/generated_crystals_cif.zip" ]]; then
  log "Missing generated_crystals_cif.zip after generation."
  echo failed_missing_cif_zip > "${STATUS}"
  exit 21
fi

cd "${REPO}"
log "Parsing generated CIF metadata into public-safe artifact."
python scripts/parse_mattergen_generation_smoke.py \
  --generation-dir "${GEN_DIR}" \
  --out-dir "${OUT_DIR}" \
  --stage pilot_5k \
  --requested-candidates 5000 \
  --pretrained-name mattergen_base \
  --batch-size 20 \
  --num-batches 250 \
  >> "${LOG}" 2>&1

log "Running public-label exclusion and CHGNet/MACE consensus scoring diagnostic."
python scripts/run_mattergen_smoke_exclusion_scoring.py \
  --generation-dir "${GEN_DIR}" \
  --out-dir "${OUT_DIR}" \
  --max-calibration-rows 240 \
  --max-sites 80 \
  --device cuda \
  >> "${LOG}" 2>&1

log "MatterGen 5k pilot pipeline finished."
echo completed > "${STATUS}"
