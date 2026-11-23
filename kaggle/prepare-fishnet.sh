#!/bin/bash
set -u
cd "$(dirname "$0")/.."
MONTH=${1:?month, e.g. 2025-01}
EVERY=${2:-1}
LOG=kaggle-out/prepare-fishnet-$MONTH.log
mkdir -p kaggle-out data/fishnet
. kaggle/lib.sh
FILE=standard_rated_${MONTH/-/_}.parquet
URL=https://huggingface.co/datasets/Lichess/fishnet-evals/resolve/main/$FILE
DL=$HOME/.cache/nexarch-fishnet/$FILE
OUT=data/fishnet/fishnet-standard_rated_${MONTH/-/_}.bin

SIZE=$(curl -sIL "$URL" | grep -i '^content-length' | tail -1 | tr -dc '0-9')
[ -n "$SIZE" ] || { say "cannot reach $URL"; exit 1; }
say "downloading $FILE ($((SIZE / 1000000)) MB)"
for i in 1 2 3 4 5; do
  [ "$(stat -c %s "$DL" 2>/dev/null || echo 0)" = "$SIZE" ] && break
  curl -sSfL -C - --retry 5 -o "$DL" "$URL" >> "$LOG" 2>&1 || { say "download interrupted (try $i), resuming"; sleep 30; }
done
[ "$(stat -c %s "$DL" 2>/dev/null || echo 0)" = "$SIZE" ] || { say "DOWNLOAD FAILED"; exit 1; }
say "downloaded and verified"

if [ ! -f "$OUT.rescaled" ]; then
  rm -f "$OUT"
  .venv/bin/python tools/fishnet_evals.py "$DL" --out-dir data/fishnet --every "$EVERY" --batch 500000 >> "$LOG" 2>&1 \
    || { say "CONVERSION FAILED"; exit 1; }
  say "converted: $(( $(stat -c %s "$OUT") / 32 )) positions -> $OUT"
  .venv/bin/python tools/rescale_scores.py "$OUT" --calibration nets/lichess-calibration.json >> "$LOG" 2>&1 \
    || { say "RESCALE FAILED"; exit 1; }
fi

N=$(( $(stat -c %s "$OUT") / 32 ))
D=$HOME/.cache/nexarch-kds/nexarch-fishnet-$MONTH
mkdir -p "$D"
ln -f "$OUT" "$D/fishnet-$MONTH.bin" 2>/dev/null || cp "$OUT" "$D/fishnet-$MONTH.bin"
printf '{"title":"nexarch-fishnet-%s","id":"markthegamer108/nexarch-fishnet-%s","licenses":[{"name":"CC0-1.0"}]}\n' "$MONTH" "$MONTH" > "$D/dataset-metadata.json"
upload_dataset nexarch-fishnet-$MONTH "$D" "Lichess fishnet evaluations $MONTH, 1 in $EVERY, $N positions, Nexarch format" \
  || { say "UPLOAD FAILED"; exit 1; }
touch "data/fishnet/fishnet-$MONTH.done"
say "ready: markthegamer108/nexarch-fishnet-$MONTH, $N positions"
