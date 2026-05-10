#!/usr/bin/env bash
set -euo pipefail

# Run OVTR official inference in an isolated OVTR environment.
#
# Required env:
#   DATASET=tao|ovtb
#
# Optional env:
#   ROOT=/home/waas/paper_experiments
#   GPUS=1
#   CUDA_VISIBLE_DEVICES=0
#   PORT=29591
#   OVTR_ENV_ACTIVATE='source /path/to/env/bin/activate'
#   OVTR_PRETRAIN=/path/to/ovtr_5_frame.pth
#   OVTR_CONFIG_OVERRIDE=/path/to/custom_ovtb_config.py

ROOT="${ROOT:-/home/waas/paper_experiments}"
DATASET="${DATASET:-tao}"
GPUS="${GPUS:-1}"
PORT="${PORT:-29591}"
REPO="${ROOT}/repos/OVTR"
STAMP="$(date +%Y%m%d_%H%M%S)"

if [[ ! -d "${REPO}/ovtr" ]]; then
  echo "Missing OVTR repo: ${REPO}" >&2
  exit 2
fi

if [[ -n "${OVTR_ENV_ACTIVATE:-}" ]]; then
  # shellcheck disable=SC1090
  eval "${OVTR_ENV_ACTIVATE}"
fi

case "${DATASET}" in
  tao)
    CONFIG="${OVTR_CONFIG_OVERRIDE:-./config/ovtr_lite_train_val.py}"
    ;;
  ovtb)
    if [[ -z "${OVTR_CONFIG_OVERRIDE:-}" ]]; then
      OUT_DIR="${ROOT}/outputs/phase8_published_trackers/ovtr/ovtb"
      mkdir -p "${OUT_DIR}"
      cat > "${OUT_DIR}/official_command_log.md" <<'EOF'
# OVTR on OVT-B

Status: unsupported_without_custom_config

The official OVTR repository ships TAO validation/test configs.  To run OVT-B,
provide `OVTR_CONFIG_OVERRIDE=/path/to/ovtb_config.py` that points OVTR's
dataset config to OVT-B annotations/frames.  No OVT-B prediction is fabricated.
EOF
      echo "OVTR OVT-B requires OVTR_CONFIG_OVERRIDE; wrote ${OUT_DIR}/official_command_log.md" >&2
      exit 2
    fi
    CONFIG="${OVTR_CONFIG_OVERRIDE}"
    ;;
  *)
    echo "Unsupported DATASET for OVTR: ${DATASET}" >&2
    exit 2
    ;;
esac

PRETRAIN="${OVTR_PRETRAIN:-${REPO}/model_zoo/ovtr_5_frame.pth}"
if [[ ! -s "${PRETRAIN}" ]]; then
  echo "Missing OVTR checkpoint: ${PRETRAIN}" >&2
  echo "Run scripts/phase8_download_published_tracker_weights.sh first." >&2
  exit 2
fi

OUT_DIR="${ROOT}/outputs/phase8_published_trackers/ovtr/${DATASET}"
RAW_DIR="${OUT_DIR}/official_inference/${STAMP}"
mkdir -p "${RAW_DIR}"

LOG="${OUT_DIR}/official_command_log.md"
{
  echo "## ${STAMP}"
  echo
  echo "- tracker: ovtr"
  echo "- dataset: ${DATASET}"
  echo "- repo: ${REPO}"
  echo "- config: ${CONFIG}"
  echo "- checkpoint: ${PRETRAIN}"
  echo "- gpus: ${GPUS}"
  echo "- raw_dir: ${RAW_DIR}"
  echo
  echo '```bash'
  printf 'cd %q\n' "${REPO}/ovtr"
  printf 'python -m torch.distributed.launch --master_port=%q --nproc_per_node=%q --use_env ./eval.py --config_file %q --pretrain %q --output_dir %q --result_path_track %q --vis_output %q\n' \
    "${PORT}" "${GPUS}" "${CONFIG}" "${PRETRAIN}" "${RAW_DIR}/output" "${RAW_DIR}/teta_results" "${RAW_DIR}/vis_output"
  echo '```'
  echo
} >> "${LOG}"

cd "${REPO}/ovtr"
python -m torch.distributed.launch --master_port="${PORT}" --nproc_per_node="${GPUS}" \
  --use_env \
  ./eval.py \
  --config_file "${CONFIG}" \
  --dataset_file lvis_generated_img_seqs \
  --epochs 16 \
  --with_box_refine \
  --two_stage \
  --lr 4e-5 \
  --lr_backbone 4e-6 \
  --lr_drop 13 \
  --pretrain "${PRETRAIN}" \
  --output_dir "${RAW_DIR}/output" \
  --num_workers 32 \
  --batch_size 1 \
  --sample_mode random_interval \
  --sample_interval 1 \
  --sampler_steps 4 7 14 \
  --sampler_lengths 2 3 4 5 \
  --merger_dropout 0 \
  --random_drop 0.1 \
  --fp_ratio 0.3 \
  --track_query_iteration CIP \
  --calculate_negative_samples \
  --score_thresh 0.20 0.17 0.17 0.20 0.17 0.20 0.17 \
  --filter_score_thresh 0.20 0.17 0.17 0.20 0.17 0.20 0.17 \
  --ious_thresh 0.5 0.45 0.5 0.4 0.45 0.45 0.45 \
  --miss_tolerance 5 5 5 5 5 5 5 \
  --maximum_quantity 160 \
  --result_path_track "${RAW_DIR}/teta_results" \
  --vis_output "${RAW_DIR}/vis_output" \
  2>&1 | tee "${RAW_DIR}/official_inference.log"

echo "[phase8] OVTR inference complete: ${RAW_DIR}"
