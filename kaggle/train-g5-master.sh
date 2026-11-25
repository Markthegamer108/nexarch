#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Master training script for ALL data sources.
# Accepts DATA_GLOBS array and trains h1024 on everything.

set -euo pipefail
cd "$(dirname "$0")/.."

NAME=${1:-master-train}
CPUS=${2:-40}
OUT="/kaggle/working/$NAME"
mkdir -p "$OUT"

echo "=== MASTER TRAIN: $NAME ==="
echo "CPUs: $CPUS"
echo "Data globs: ${#DATA_GLOBS[@]}"

# Collect all matching files
ALL_FILES=()
for glob in "${DATA_GLOBS[@]}"; do
    for f in $glob; do
        [ -f "$f" ] && ALL_FILES+=("$f")
    done
done

echo "Total files: ${#ALL_FILES[@]}"
for f in "${ALL_FILES[@]}"; do
    echo "  $f ($(du -h "$f" | cut -f1))"
done

if [ ${#ALL_FILES[@]} -eq 0 ]; then
    echo "ERROR: No data files found!"
    exit 1
fi

# Resume from checkpoint
RESUME=$(find /kaggle/input -name '*.pt' -print -quit | head -1)
if [ -z "$RESUME" ] || [ ! -f "$RESUME" ]; then
    RESUME="/kaggle/input/nexarch-confirm-g4/nexarch-g4.pt"
fi
echo "Resuming from: $RESUME"

# Training config
HIDDEN=${HIDDEN:-1024}
EPOCHS=${EPOCHS:-10}
BUDGET=${BUDGET:-600}
LR=${LR:-0.00025}
BATCH=${BATCH:-8192}
STREAM=${STREAM:-16000000}

echo "Config: hidden=$HIDDEN epochs=$EPOCHS budget=${BUDGET}min lr=$LR batch=$BATCH stream=$STREAM"

# Run training
CUDA_VISIBLE_DEVICES=0 python trainer/train.py \
    --data "${ALL_FILES[@]}" \
    --resume "$RESUME" \
    --hidden "$HIDDEN" \
    --epochs "$EPOCHS" \
    --time-budget "$BUDGET" \
    --batch "$BATCH" \
    --lr "$LR" \
    --stream "$STREAM" \
    --wdl 0.4 \
    --out "$OUT/nexarch-master.nnue" \
    2>&1 | tee "$OUT/train.log"

# Verify output
if [ -f "$OUT/nexarch-master.nnue" ]; then
    echo "Training complete: $OUT/nexarch-master.nnue"
    printf 'setoption name EvalFile value %s\nnnuecheck 100\n' "$OUT/nexarch-master.nnue" | ./engine/nexarch | tail -1
    cp "$OUT/nexarch-master.nnue" "/kaggle/working/nexarch-master.nnue"
else
    echo "ERROR: No output net produced"
    exit 1
fi