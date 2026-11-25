#!/bin/bash
set -u
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy

set -euo pipefail
cd "$(dirname "$0")/.."
LOG=kaggle-out/prepare-lichess.log
mkdir -p kaggle-out data/lichess
. kaggle/lib.sh
P=$HOME/.cache/nexarch-lichess/parquet
mkdir -p "$P"
BASE=https://huggingface.co/datasets/Lichess/chess-position-evaluations/resolve/main/data
curl -sS "https://huggingface.co/api/datasets/Lichess/chess-position-evaluations/tree/main/data" \
  | .venv/bin/python -c 'import json,sys; [print(e["path"].split("/")[-1], e["size"]) for e in json.load(sys.stdin) if e["path"].endswith(".parquet")]' \
  > "$P/files.txt" || { say "cannot list the dataset"; exit 1; }
say "$(wc -l < "$P/files.txt") parquet files listed"
while read -r name size; do
  for i in 1 2 3 4 5; do
    [ "$(stat -c %s "$P/$name" 2>/dev/null || echo 0)" = "$size" ] && break
    curl -sSfL -C - --retry 5 -o "$P/$name" "$BASE/$name" >> "$LOG" 2>&1 || { say "$name interrupted (try $i)"; sleep 30; }
  done
  [ "$(stat -c %s "$P/$name" 2>/dev/null || echo 0)" = "$size" ] || { say "DOWNLOAD FAILED: $name"; exit 1; }
  .venv/bin/python tools/lichess_evals.py "$P/$name" --out-dir data/lichess >> "$LOG" 2>&1 || { say "CONVERSION FAILED: $name"; exit 1; }
done < "$P/files.txt"
say "all files converted: $(cat data/lichess/*.bin | wc -c | awk '{print $1 / 32}') positions"

while [ ! -s nets/lichess-calibration.json ]; do sleep 60; done
.venv/bin/python tools/rescale_scores.py data/lichess/lichess-*.bin --calibration nets/lichess-calibration.json >> "$LOG" 2>&1 \
  || { say "RESCALE FAILED"; exit 1; }
D=$HOME/.cache/nexarch-kds/nexarch-lichess-evals
mkdir -p "$D"
for f in data/lichess/lichess-*.bin; do ln -f "$f" "$D/$(basename "$f")" 2>/dev/null || cp "$f" "$D/"; done
printf '{"title":"nexarch-lichess-evals","id":"markthegamer108/nexarch-lichess-evals","licenses":[{"name":"MIT"}]}\n' > "$D/dataset-metadata.json"
mit_license "$D"
upload_dataset nexarch-lichess-evals "$D" "Lichess evaluation database (CC0), best line of the deepest evaluation, converted to Nexarch format by Mark Ivanovskyy (MIT)" \
  || { say "UPLOAD FAILED"; exit 1; }
touch data/lichess/lichess.done
say "ready: markthegamer108/nexarch-lichess-evals"
