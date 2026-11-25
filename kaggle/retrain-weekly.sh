#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Weekly retrain on ALL accumulated data (supervised + curated self-play).
# Run every Saturday after self-play fleet completes.
# Trains h1024 (or configured width) for 8-12 epochs on full dataset.

set -euo pipefail
cd "$(dirname "$0")/.."

WEEK=$(date -u +%Y-W%V)
NAME="nexarch-retrain-${WEEK}"
LOG="kaggle-out/retrain-${WEEK}.log"
mkdir -p kaggle-out

. kaggle/lib.sh

say "=== Weekly Retrain $WEEK ==="

# Check GPU quota
REM_MIN=$( .venv/bin/kaggle quota 2>/dev/null | awk '$1 == "GPU" {print $3}' | tr -d 'h' \
    | .venv/bin/python -c 'import sys; x = sys.stdin.read().strip(); print(int(float(x) * 60) if x else 0)' )
NEED=720  # 12 hours buffer
[ "${REM_MIN:-0}" -ge "$NEED" ] || {
    say "Insufficient GPU quota: ${REM_MIN:-0} min < ${NEED} min needed"
    exit 1
}

# Dataset list: all supervised + all self-play datasets
DATASETS=(
    markthegamer108/nexarch-graded-g3
    markthegamer108/nexarch-t80-2024-01-jan
    markthegamer108/nexarch-t80-2024-02-feb
    markthegamer108/nexarch-t80-2024-03-mar
    markthegamer108/nexarch-lichess-evals
    markthegamer108/nexarch-fishnet-2025-01
    markthegamer108/nexarch-selfplay-2026-11-22
    markthegamer108/nexarch-selfplay-aws-2026-11-23
    markthegamer108/nexarch-selfplay-2026-11-24
)
# Auto-discover new self-play datasets
for ds in $(.venv/bin/kaggle datasets list -m 2>/dev/null | awk '$1 ~ /^markthegamer108\/nexarch-selfplay-/ {print $1}'); do
    if [[ ! " ${DATASETS[@]} " =~ " ${ds} " ]]; then
        DATASETS+=("$ds")
        say "Adding new self-play dataset: $ds"
    fi
done

# Build --dataset args
DS_ARGS=()
for ds in "${DATASETS[@]}"; do
    DS_ARGS+=(--dataset "$ds")
done

# Resume from latest checkpoint if available, else from Gen 4
RESUME=$(find kaggle-out -name '*.pt' -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
if [ -z "$RESUME" ] || [ ! -f "$RESUME" ]; then
    RESUME="nets/nexarch-g4.pt"
    say "No checkpoint found, resuming from Gen 4: $RESUME"
else
    say "Resuming from checkpoint: $RESUME"
fi

# Training config
HIDDEN=${RETRAIN_HIDDEN:-1024}
EPOCHS=${RETRAIN_EPOCHS:-10}
BUDGET=${RETRAIN_BUDGET:-600}
LR=${RETRAIN_LR:-0.00025}
BATCH=${RETRAIN_BATCH:-8192}
STREAM=${RETRAIN_STREAM:-16000000}

say "Config: hidden=$HIDDEN epochs=$EPOCHS budget=${BUDGET}min lr=$LR batch=$BATCH"

# Build data globs from train_sources.txt (convert to Kaggle input paths)
# The Kaggle job mounts datasets at /kaggle/input/<dataset-name>/
# We need to pass globs that match the mounted files
DATA_GLOBS=()
for ds in "${DATASETS[@]}"; do
    ds_name=$(basename "$ds")
    DATA_GLOBS+=("/kaggle/input/$ds_name/**/*.bin")
    DATA_GLOBS+=("/kaggle/input/$ds_name/**/*.pgn")
    DATA_GLOBS+=("/kaggle/input/$ds_name/**/*.zst")
done
# Also add acquired data (will be mounted separately)
for f in data/acquired/fishtest/*.bin data/acquired/lc0/*.bin data/acquired/games/*.bin data/acquired/games/*.pgn data/acquired/games/*.zst data/acquired/distilled/*.pgn 2>/dev/null; do
    [ -f "$f" ] && DATA_GLOBS+=("$f")
done

say "Data globs: ${#DATA_GLOBS[@]} patterns"

push_kernel "$NAME" 40 .venv/bin/python kaggle/job.py --name "$NAME" --gpu \
    --source markthegamer108/nexarch-confirm-g4 \
    "${DS_ARGS[@]}" \
    --cmd "G5_MODE=h1024 G5_BUDGET=$BUDGET G5_EPOCHS=$EPOCHS G5_A_LR=$LR G5_B_LR=$LR G5_RESUME=\$(find /kaggle/input -name '*.pt' -print -quit | head -1) DATA_GLOBS=($(printf '"%s" ' "${DATA_GLOBS[@]}")) bash kaggle/train-g5-master.sh {out} {cpus}" \
    --push || { say "Failed to launch $NAME"; exit 1; }

bash kaggle/ensure-kernel.sh "$NAME"

say "$NAME finished"
OUT_NNUE=$(ls kaggle-out/$NAME/g5-*.nnue 2>/dev/null | head -1)
if [ -n "$OUT_NNUE" ]; then
    say "New net: $OUT_NNUE"
    
    # Publish as latest net for next week's self-play
    LATEST_DIR=$(mktemp -d)
    cp "$OUT_NNUE" "$LATEST_DIR/nexarch.nnue"
    cat > "$LATEST_DIR/dataset-metadata.json" <<EOF
{"title":"nexarch-latest-net","id":"markthegamer108/nexarch-latest-net","licenses":[{"name":"MIT"}]}
EOF
    echo "MIT License..." > "$LATEST_DIR/LICENSE"
    .venv/bin/kaggle datasets version -p "$LATEST_DIR" -m "Weekly retrain $WEEK" 2>&1 | tail -3
    say "Published as markthegamer108/nexarch-latest-net"
    
    # Also copy to nets/ for local testing
    cp "$OUT_NNUE" "nets/nexarch-g5-${WEEK}.nnue"
    say "Local copy: nets/nexarch-g5-${WEEK}.nnue"
else
    say "WARNING: No output net found in kaggle-out/$NAME/"
fi