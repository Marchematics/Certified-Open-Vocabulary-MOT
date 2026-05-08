#!/usr/bin/env bash
set -euo pipefail

EXP_ROOT=${EXP_ROOT:-/home/waas/paper_experiments}
cd "$EXP_ROOT"

source "$EXP_ROOT/env.sh"
source "$EXP_ROOT/.venv/bin/activate"

export HF_HOME="$EXP_ROOT/cache/huggingface"
export HUGGINGFACE_HUB_CACHE="$EXP_ROOT/cache/huggingface/hub"
export HF_DATASETS_CACHE="$EXP_ROOT/cache/huggingface/datasets"
export TRANSFORMERS_CACHE="$EXP_ROOT/cache/huggingface/transformers"
export HF_HUB_DISABLE_XET=1
export TORCH_HOME="$EXP_ROOT/cache/torch"
export TMPDIR="$EXP_ROOT/tmp"

MILESTONE="$EXP_ROOT/outputs/milestones/ijcv_cross_generator_v1"
mkdir -p "$MILESTONE"

RUN_REPORT="$MILESTONE/RUN_REPORT.md"
START_TIME=$(date -Is)

{
  echo "# OWLv2 GPU Run Report"
  echo
  echo "- Start time: $START_TIME"
  echo "- Host: $(hostname)"
  echo "- Working directory: $EXP_ROOT"
  echo "- Python: $(python --version 2>&1)"
  echo "- parc-track: $(command -v parc-track || true)"
  echo
  echo "## GPU"
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=index,name,memory.total,driver_version --format=csv,noheader || true
  else
    echo "nvidia-smi not found"
  fi
  echo
  echo "## Commands"
} > "$RUN_REPORT"

run_logged() {
  local cmd="$*"
  echo "- \`$cmd\`" | tee -a "$RUN_REPORT"
  eval "$cmd"
}

run_logged "parc-track phase2 propose --config configs/phase3_ovtb_owlv2_audit.yaml"
run_logged "parc-track phase2 propose --config configs/phase3_tao_owlv2_audit.yaml"
run_logged "parc-track phase3 matrix --config configs/phase3_ovtb_owlv2_matrix.yaml"
run_logged "parc-track phase3 matrix --config configs/phase3_tao_owlv2_matrix.yaml"
run_logged "parc-track phase3 export-release-audit --config configs/phase3_ovtb_owlv2_matrix.yaml --unsupported-only"
run_logged "parc-track phase3 export-release-audit --config configs/phase3_tao_owlv2_matrix.yaml --unsupported-only"
run_logged "parc-track phase3 cross-generator-report --config configs/phase3_cross_generator_report.yaml"

cp configs/phase3_ovtb_owlv2_audit.yaml "$MILESTONE/"
cp configs/phase3_tao_owlv2_audit.yaml "$MILESTONE/"
cp configs/phase3_ovtb_owlv2_matrix.yaml "$MILESTONE/"
cp configs/phase3_tao_owlv2_matrix.yaml "$MILESTONE/"
cp configs/phase3_cross_generator_report.yaml "$MILESTONE/"

MANIFEST="$MILESTONE/MANIFEST_SHA256.txt"
find \
  "$EXP_ROOT/outputs/phase3_ovtb_owlv2" \
  "$EXP_ROOT/outputs/phase3_tao_owlv2" \
  "$MILESTONE" \
  "$EXP_ROOT/configs/phase3_ovtb_owlv2_audit.yaml" \
  "$EXP_ROOT/configs/phase3_tao_owlv2_audit.yaml" \
  "$EXP_ROOT/configs/phase3_ovtb_owlv2_matrix.yaml" \
  "$EXP_ROOT/configs/phase3_tao_owlv2_matrix.yaml" \
  "$EXP_ROOT/configs/phase3_cross_generator_report.yaml" \
  -type f \
  ! -path "*/cache/*" \
  ! -path "*/audit_viewer/*" \
  ! -name "MANIFEST_SHA256.txt" \
  -print0 | sort -z | xargs -0 sha256sum > "$MANIFEST"

END_TIME=$(date -Is)
{
  echo
  echo "- End time: $END_TIME"
  echo "- SHA256 manifest: $MANIFEST"
} >> "$RUN_REPORT"

echo "OWLv2 GPU plan completed. Deliverables are under:"
echo "  $EXP_ROOT/outputs/phase3_ovtb_owlv2"
echo "  $EXP_ROOT/outputs/phase3_tao_owlv2"
echo "  $MILESTONE"
