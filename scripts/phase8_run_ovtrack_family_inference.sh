#!/usr/bin/env bash
set -euo pipefail

# Run OVTrack-family official inference in the tracker repo environment.
#
# Required env:
#   TRACKER=ovtrack|ovtb_baseline
#   DATASET=ovtb|tao
#
# Optional env:
#   ROOT=/home/waas/paper_experiments
#   GPUS=4
#   PORT=29581
#   CUDA_VISIBLE_DEVICES=0,1,2,3
#   OVTRACK_ENV_ACTIVATE='source /path/to/env/bin/activate'
#   OVTRACK_CKPT=/path/to/ovtrack_detpro_prompt.pth

ROOT="${ROOT:-/home/waas/paper_experiments}"
TRACKER="${TRACKER:-ovtrack}"
DATASET="${DATASET:-ovtb}"
GPUS="${GPUS:-4}"
PORT="${PORT:-29581}"
STAMP="$(date +%Y%m%d_%H%M%S)"

case "${TRACKER}:${DATASET}" in
  ovtrack:tao)
    REPO="${ROOT}/repos/ovtrack"
    CONFIG="configs/ovtrack-tao/ovtrack_r50.py"
    EVAL_OPTIONS=("resfile_path=results/phase8_ovtrack_tao_${STAMP}/" "use_tao_metric=True")
    ;;
  ovtrack:ovtb)
    # SysCV/ovtrack does not ship an OVT-B config; Coo1Sea/OVT-B-Dataset
    # provides the benchmark-aligned OVTrack config.
    REPO="${ROOT}/repos/OVT-B-Dataset"
    CONFIG="configs/ovtrack-teta/ovtb/ovtrack_r50.py"
    EVAL_OPTIONS=("resfile_path=results/phase8_ovtrack_ovtb_${STAMP}/")
    ;;
  ovtb_baseline:tao)
    REPO="${ROOT}/repos/OVT-B-Dataset"
    CONFIG="configs/ovtrack-teta/ov_tao_val/ovtrack_plus.py"
    EVAL_OPTIONS=("resfile_path=results/phase8_ovtb_baseline_tao_${STAMP}/")
    ;;
  ovtb_baseline:ovtb)
    REPO="${ROOT}/repos/OVT-B-Dataset"
    CONFIG="configs/ovtrack-teta/ovtb/ovtrack_plus.py"
    EVAL_OPTIONS=("resfile_path=results/phase8_ovtb_baseline_ovtb_${STAMP}/")
    ;;
  *)
    echo "Unsupported TRACKER/DATASET pair: ${TRACKER}/${DATASET}" >&2
    exit 2
    ;;
esac

if [[ ! -d "${REPO}" ]]; then
  echo "Missing tracker repo: ${REPO}" >&2
  exit 2
fi

if [[ -n "${OVTRACK_ENV_ACTIVATE:-}" ]]; then
  # shellcheck disable=SC1090
  eval "${OVTRACK_ENV_ACTIVATE}"
fi

CKPT="${OVTRACK_CKPT:-${REPO}/saved_models/ovtrack_detpro_prompt.pth}"
if [[ ! -s "${CKPT}" ]]; then
  echo "Missing OVTrack checkpoint: ${CKPT}" >&2
  echo "Run scripts/phase8_download_published_tracker_weights.sh first." >&2
  exit 2
fi

OUT_DIR="${ROOT}/outputs/phase8_published_trackers/${TRACKER}/${DATASET}"
RAW_DIR="${OUT_DIR}/official_inference/${STAMP}"
mkdir -p "${RAW_DIR}"

LOG="${OUT_DIR}/official_command_log.md"
{
  echo "## ${STAMP}"
  echo
  echo "- tracker: ${TRACKER}"
  echo "- dataset: ${DATASET}"
  echo "- repo: ${REPO}"
  echo "- config: ${CONFIG}"
  echo "- checkpoint: ${CKPT}"
  echo "- gpus: ${GPUS}"
  echo "- raw_dir: ${RAW_DIR}"
  echo
  echo '```bash'
  printf 'cd %q\n' "${REPO}"
  printf './tools/dist_test.sh %q %q %q %q --out %q --eval track --eval-options' "${CONFIG}" "${CKPT}" "${GPUS}" "${PORT}" "${RAW_DIR}/raw_outputs.pkl"
  printf ' %q' "${EVAL_OPTIONS[@]}"
  echo
  echo '```'
  echo
} >> "${LOG}"

cd "${REPO}"
./tools/dist_test.sh "${CONFIG}" "${CKPT}" "${GPUS}" "${PORT}" \
  --out "${RAW_DIR}/raw_outputs.pkl" \
  --eval track \
  --eval-options "${EVAL_OPTIONS[@]}" \
  2>&1 | tee "${RAW_DIR}/official_inference.log"

echo "[phase8] official OVTrack-family inference complete: ${RAW_DIR}"
echo "[phase8] Next: convert a COCO-VID/TETA prediction JSON/PKL if the official evaluator emitted one."
