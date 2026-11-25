#!/bin/bash
set -u
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy

set -euo pipefail
cd "$(dirname "$0")/.."
LOG=kaggle-out/evalset.log
mkdir -p kaggle-out nets data/eval
. kaggle/lib.sh
MONTH=${1:-2024-05}
N=${2:-250000}
say "building a frozen evaluation set from fishnet $MONTH"

if [ ! -f "data/eval/frozen-$MONTH.bin" ]; then
  PARQ=$HOME/.cache/nexarch-eval/standard_rated_${MONTH/-/_}.parquet
  if [ ! -f "$PARQ" ]; then
    TOK=$(cat "$HOME/.cache/huggingface/token")
    curl -sSfL -C - --retry 5 -H "Authorization: Bearer $TOK" -o "$PARQ" \
      "https://huggingface.co/datasets/Lichess/fishnet-evals/resolve/main/standard_rated_${MONTH/-/_}.parquet" >> "$LOG" 2>&1 \
      || { say "download failed"; exit 1; }
  fi
  rm -f "data/eval/all-$MONTH.bin" "data/eval/all-$MONTH.bin.done"
  .venv/bin/python tools/fishnet_evals.py "$PARQ" --out-dir data/eval --every 40 >> "$LOG" 2>&1 \
    || { say "conversion failed"; exit 1; }
  SRC=$(ls data/eval/fishnet-standard_rated_${MONTH/-/_}.bin 2>/dev/null | head -1)
  [ -n "$SRC" ] || { say "converted file missing"; exit 1; }
  .venv/bin/python tools/dedupe_eval.py --in "$SRC" --out "data/eval/unique-$MONTH.bin" --want "$N" >> "$LOG" 2>&1 \
    || { say "dedupe failed"; exit 1; }
  .venv/bin/python tools/make_evalset.py --bin "data/eval/unique-$MONTH.bin" --out "data/eval/frozen-$MONTH.bin" --positions "$N" --month "$MONTH" >> "$LOG" 2>&1 \
    || { say "sampling failed"; exit 1; }
  rm -f "data/eval/unique-$MONTH.bin"
  rm -f "$SRC" "$SRC.done"
fi

POS=$(( $(stat -c %s "data/eval/frozen-$MONTH.bin") / 32 ))
[ "$POS" -gt 0 ] || { say "empty eval set"; exit 1; }
say "eval set: $POS unique positions"

D=$HOME/.cache/nexarch-kds/nexarch-evalset-$MONTH
mkdir -p "$D"
ln -f "data/eval/frozen-$MONTH.bin" "$D/eval-$MONTH.bin" 2>/dev/null || cp "data/eval/frozen-$MONTH.bin" "$D/eval-$MONTH.bin"
cp -f "data/eval/frozen-$MONTH.bin.json" "$D/" 2>/dev/null || true
printf '{"title":"nexarch-evalset-%s","id":"markthegamer108/nexarch-evalset-%s","licenses":[{"name":"MIT"}]}\n' "$MONTH" "$MONTH" > "$D/dataset-metadata.json"
upload_dataset nexarch-evalset-$MONTH "$D" "Frozen evaluation set from Lichess fishnet $MONTH, never used in training, $POS positions" \
  || { say "upload failed"; exit 1; }

TOK=$(cat ~/.kaggle/access_token)
REMOTE=$(curl -s -H "Authorization: Bearer $TOK" "https://www.kaggle.com/api/v1/datasets/list/markthegamer108/nexarch-evalset-$MONTH" \
  | .venv/bin/python -c "import json,sys; d=json.load(sys.stdin); print((d.get('datasetFiles') or [{}])[0].get('totalBytes', 0))")
[ "$REMOTE" = "$(stat -c %s data/eval/frozen-$MONTH.bin)" ] || { say "verify failed: remote $REMOTE"; exit 1; }
say "verified: markthegamer108/nexarch-evalset-$MONTH, $POS positions"
touch data/eval/.done
