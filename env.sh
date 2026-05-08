#!/usr/bin/env bash

export EXP_ROOT=/home/waas/paper_experiments

export TMPDIR="$EXP_ROOT/tmp"
export XDG_CACHE_HOME="$EXP_ROOT/cache"
export PIP_CACHE_DIR="$EXP_ROOT/cache/pip"
export HF_HOME="$EXP_ROOT/cache/huggingface"
export HUGGINGFACE_HUB_CACHE="$EXP_ROOT/cache/huggingface/hub"
export HF_DATASETS_CACHE="$EXP_ROOT/cache/huggingface/datasets"
export TRANSFORMERS_CACHE="$EXP_ROOT/cache/huggingface/transformers"
export TORCH_HOME="$EXP_ROOT/cache/torch"
export WANDB_DIR="$EXP_ROOT/cache/wandb"

export GH_CONFIG_DIR="$EXP_ROOT/.config/gh"
export PATH="$EXP_ROOT/tools/bin:$PATH"

export CUDA_VISIBLE_DEVICES=0,1,2
