#!/usr/bin/env bash
# Public-safe local environment helper. Override PARC_TRACK_ROOT before sourcing if needed.
export PARC_TRACK_ROOT="${PARC_TRACK_ROOT:-$(pwd)}"
export TMPDIR="${TMPDIR:-$PARC_TRACK_ROOT/tmp}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$PARC_TRACK_ROOT/cache}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PARC_TRACK_ROOT/cache/pip}"
export HF_HOME="${HF_HOME:-$PARC_TRACK_ROOT/cache/huggingface}"
export HUGGINGFACE_HUB_CACHE="${HUGGINGFACE_HUB_CACHE:-$HF_HOME/hub}"
export HF_DATASETS_CACHE="${HF_DATASETS_CACHE:-$HF_HOME/datasets}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME/transformers}"
export TORCH_HOME="${TORCH_HOME:-$PARC_TRACK_ROOT/cache/torch}"
export WANDB_DIR="${WANDB_DIR:-$PARC_TRACK_ROOT/cache/wandb}"
export PYTHONPATH="$PARC_TRACK_ROOT/code/parc_track:${PYTHONPATH:-}"
