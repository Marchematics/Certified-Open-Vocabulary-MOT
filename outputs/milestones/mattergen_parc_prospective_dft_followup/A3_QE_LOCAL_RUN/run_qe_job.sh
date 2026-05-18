#!/usr/bin/env bash
set -euo pipefail
JOB_ID="${1:?job id required}"
NP="${2:-4}"
RUN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT_DIR="$RUN_DIR/qe_inputs/$JOB_ID"
OUTPUT_DIR="$RUN_DIR/qe_outputs/$JOB_ID"
mkdir -p "$OUTPUT_DIR"
export OMPI_ALLOW_RUN_AS_ROOT=1
export OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1
cd "$INPUT_DIR"
"${MPIRUN_CMD:-mpirun.openmpi}" --allow-run-as-root -np "$NP" "${PWX_CMD:-pw.x}" -in pw.vc-relax.in > "$OUTPUT_DIR/pw.vc-relax.out" 2> "$OUTPUT_DIR/pw.vc-relax.err"
