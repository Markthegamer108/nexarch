#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/save-selfplay-day.log
mkdir -p kaggle-out
. kaggle/lib.sh
say "waiting for the laptop and the five Kaggle self-play shards"
while [ ! -f data/selfplay-day.done ]; do sleep 60; done
for i in 0 1 2 3 4; do
  while [ ! -f kaggle-out/nexarch-sp-g2e-$i.done ]; do sleep 60; done
done
OUT=data/selfplay-2026-11-22.bin
: > "$OUT"
for f in data/data-g2e-day-local.bin data/data-g3a-day-local.bin kaggle-out/nexarch-sp-g2e-{0..4}/data-g2e-k*.bin; do
  [ -s "$f" ] && cat "$f" >> "$OUT"
done
N=$(( $(stat -c %s "$OUT") / 32 ))
say "merged $N positions into $OUT"
D=$HOME/.cache/nexarch-kds/nexarch-selfplay-2026-11-22
mkdir -p "$D"
ln -f "$OUT" "$D/selfplay-2026-11-22.bin" 2>/dev/null || cp "$OUT" "$D/selfplay-2026-11-22.bin"
printf '{"title":"nexarch-selfplay-2026-11-22","id":"markthegamer108/nexarch-selfplay-2026-11-22","licenses":[{"name":"other"}]}\n' > "$D/dataset-metadata.json"
upload_dataset nexarch-selfplay-2026-11-22 "$D" "Self-play on 2026-11-22, $N positions, Gen 2 and Gen 3 networks" \
  || { say "UPLOAD FAILED: the local file is still in $OUT"; exit 1; }
touch data/selfplay-2026-11-22.done
say "ready: markthegamer108/nexarch-selfplay-2026-11-22, $N positions"
