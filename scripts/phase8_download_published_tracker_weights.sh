#!/usr/bin/env bash
set -euo pipefail

# Download only official published-tracker weights/embeddings needed to produce
# derived prediction files.  Raw datasets and caches are intentionally not
# touched here.

ROOT="${ROOT:-/home/waas/paper_experiments}"
OVTRACK_REPOS=(
  "${ROOT}/repos/ovtrack"
  "${ROOT}/repos/OVT-B-Dataset"
)
OVTR_REPO="${ROOT}/repos/OVTR"

if ! python - <<'PY' >/dev/null 2>&1
import gdown
PY
then
  echo "[phase8] Installing gdown into the active Python environment..." >&2
  python -m pip install gdown
fi

download_drive() {
  local file_id="$1"
  local out_path="$2"
  mkdir -p "$(dirname "${out_path}")"
  if [[ -s "${out_path}" ]]; then
    echo "[phase8] exists: ${out_path}"
    return 0
  fi
  echo "[phase8] downloading Google Drive id=${file_id} -> ${out_path}"
  python -m gdown "https://drive.google.com/uc?id=${file_id}" -O "${out_path}"
}

# OVTrack / OVT-B baseline share the official OVTrack checkpoint.
for repo in "${OVTRACK_REPOS[@]}"; do
  if [[ -d "${repo}" ]]; then
    download_drive "1vDAFRmuNMCwhKtW7KHONpzkooLysU8nX" "${repo}/saved_models/ovtrack_detpro_prompt.pth"
  else
    echo "[phase8] missing repo, skip OVTrack weights: ${repo}" >&2
  fi
done

if [[ -d "${OVTR_REPO}" ]]; then
  download_drive "10GKAIBxAseTiXnJXV1MnxnJBTmOHVFh5" "${OVTR_REPO}/model_zoo/ovtr_5_frame.pth"
  download_drive "1x6DciXsRIOzT24typcuryqmtdVJKnXZI" "${OVTR_REPO}/model_zoo/ovtr_lite.pth"
  download_drive "1x5RQ5m6XlLYB_iOPDnbeEKSYQeT4HVwo" "${OVTR_REPO}/model_zoo/ovtr_det_pretrain.pth"
  download_drive "1OYvyCQ_y65oq6SDJQKrVm3syzvXStL-0" "${OVTR_REPO}/model_zoo/iou_neg5_ens.pth"
  download_drive "1j5l-BPv-f43fb953hmIijxQ4gSUduWWe" "${OVTR_REPO}/model_zoo/clip_image_embedding_all.pt"
else
  echo "[phase8] missing OVTR repo: ${OVTR_REPO}" >&2
fi

echo "[phase8] weight download/check complete"
