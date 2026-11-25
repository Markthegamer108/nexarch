#!/bin/bash
set -u
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy

set -euo pipefail
cd "$(dirname "$0")/.."
DATE=${1:-$(TZ=Europe/Berlin date +%F)}
LOG=kaggle-out/save-selfplay-day.log
mkdir -p kaggle-out
. kaggle/lib.sh
say "waiting for the laptop and the Kaggle self-play shards ($DATE)"
while [ ! -f data/selfplay-day.done ]; do sleep 60; done
K=kaggle-out/sp-g4a-kernels.txt
if [ -s "$K" ]; then
  while read -r name; do
    [ -n "$name" ] || continue
    while [ ! -f "kaggle-out/$name.done" ]; do sleep 60; done
  done < "$K"
fi
OUT=data/selfplay-$DATE.bin
: > "$OUT"
for f in data/data-g4a-day-local.bin data/data-g3a-day-local.bin data/data-g2e-day-local.bin kaggle-out/nexarch-sp-g4a-{0..4}/data-g4a-k*.bin; do
  [ -s "$f" ] && cat "$f" >> "$OUT"
done
N=$(( $(stat -c %s "$OUT") / 32 ))
say "merged $N positions into $OUT"
D=$HOME/.cache/nexarch-kds/nexarch-selfplay-$DATE
mkdir -p "$D"
ln -f "$OUT" "$D/selfplay-$DATE.bin" 2>/dev/null || cp "$OUT" "$D/selfplay-$DATE.bin"
printf '{"title":"nexarch-selfplay-%s","id":"markthegamer108/nexarch-selfplay-%s","licenses":[{"name":"MIT"}]}\n' "$DATE" "$DATE" > "$D/dataset-metadata.json"
mit_license "$D"
upload_dataset nexarch-selfplay-$DATE "$D" "Self-play on $DATE, $N positions, Gen 2 to Gen 4 networks" \
  || { say "UPLOAD FAILED: the local file is still in $OUT"; exit 1; }
touch data/selfplay-$DATE.done
say "ready: markthegamer108/nexarch-selfplay-$DATE, $N positions"
