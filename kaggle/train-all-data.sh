#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Train on ALL acquired data (local or Kaggle).
# Usage: bash kaggle/train-all-data.sh [output_name] [hidden] [epochs] [budget_min] [lr]

set -euo pipefail
cd "$(dirname "$0")/.."

NAME=${1:-nexarch-all-data}
HIDDEN=${2:-1024}
EPOCHS=${3:-10}
BUDGET=${4:-600}
LR=${5:-0.00025}
BATCH=${6:-8192}
STREAM=${7:-16000000}

OUT="nets/$NAME"
mkdir -p "$OUT"
LOG="$OUT/train.log"

echo "=== TRAIN ALL DATA: $NAME ==="
echo "Hidden: $HIDDEN, Epochs: $EPOCHS, Budget: ${BUDGET}min, LR: $LR"

# Build file list from master sources
MASTER_SOURCES="data/acquired/master/train_sources.txt"
if [ ! -f "$MASTER_SOURCES" ]; then
    echo "ERROR: $MASTER_SOURCES not found. Run acquire-all-data.sh first."
    exit 1
fi

FILES=()
while IFS= read -r line; do
    [ -n "$line" ] && [ -f "$line" ] && FILES+=("$line")
done < "$MASTER_SOURCES"

# Also add any .bin files in acquired directories
for f in data/acquired/fishtest/*.bin data/acquired/lc0/*.bin data/acquired/games/*.bin data/acquired/distilled/*.bin 2>/dev/null; do
    [ -f "$f" ] && FILES+=("$f")
done

# Deduplicate
FILES=($(printf '%s\n' "${FILES[@]}" | sort -u))

echo "Training files (${#FILES[@]}):"
for f in "${FILES[@]}"; do
    echo "  $f ($(du -h "$f" 2>/dev/null | cut -f1 || echo "N/A"))"
done

if [ ${#FILES[@]} -eq 0 ]; then
    echo "ERROR: No training files found"
    exit 1
fi

# Find latest checkpoint
RESUME=$(ls -t nets/*.pt 2>/dev/null | head -1)
if [ -z "$RESUME" ] || [ ! -f "$RESUME" ]; then
    RESUME="nets/nexarch-g4.pt"
fi
echo "Resuming from: $RESUME"

# Check if we have GPU
if command -v nvidia-smi &>/dev/null && nvidia-smi -L 2>/dev/null | grep -q GPU; then
    echo "GPU detected: $(nvidia-smi -L)"
    CUDA_VISIBLE_DEVICES=0 python trainer/train.py \
        --data "${FILES[@]}" \
        --resume "$RESUME" \
        --hidden "$HIDDEN" \
        --epochs "$EPOCHS" \
        --time-budget "$BUDGET" \
        --batch "$BATCH" \
        --lr "$LR" \
        --stream "$STREAM" \
        --wdl 0.4 \
        --out "$OUT.nnue" \
        2>&1 | tee "$LOG"
else
    echo "No GPU detected, using CPU (will be slow)"
    python trainer/train.py \
        --data "${FILES[@]}" \
        --resume "$RESUME" \
        --hidden "$HIDDEN" \
        --epochs "$EPOCHS" \
        --time-budget "$BUDGET" \
        --batch "$BATCH" \
        --lr "$LR" \
        --stream "$STREAM" \
        --wdl 0.4 \
        --out "$OUT.nnue" \
        2>&1 | tee "$LOG"
fi

if [ -f "$OUT.nnue" ]; then
    echo "SUCCESS: $OUT.nnue"
    printf 'setoption name EvalFile value %s\nnnuecheck 100\n' "$OUT.nnue" | ./engine/nexarch | tail -1
else
    echo "FAILED: No output"
    exit 1
fi