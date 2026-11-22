#!/bin/bash
set -u
cd "$(dirname "$0")/.."
MONTH=${1:?month, e.g. 2024-01-jan}
EVERY=${2:-10}
LOG=kaggle-out/prepare-t80-$MONTH.log
mkdir -p kaggle-out data/lc0
. kaggle/lib.sh
YEAR=${MONTH%%-*}
FILE=test80-$MONTH-2tb7p.min-v2.v6.binpack.zst
URL=https://huggingface.co/datasets/linrock/test80-$YEAR/resolve/main/$FILE
DL=$HOME/.cache/nexarch-binpack/t80/$FILE
OUT=data/lc0/t80-$MONTH.bin
CONV=${BUILD_DIR:-$HOME/.cache/nexarch-binpack/build}/binpack2nexarch
[ -x "$CONV" ] || bash tools/binpack/build.sh >> "$LOG" 2>&1 || { say "converter build failed"; exit 1; }

SIZE=$(curl -sIL "$URL" | grep -i '^content-length' | tail -1 | tr -dc '0-9')
[ -n "$SIZE" ] || { say "cannot reach $URL"; exit 1; }
say "downloading $FILE ($((SIZE / 1000000)) MB)"
for i in 1 2 3 4 5; do
  [ "$(stat -c %s "$DL" 2>/dev/null || echo 0)" = "$SIZE" ] && break
  curl -sSfL -C - --retry 5 -o "$DL" "$URL" >> "$LOG" 2>&1 || { say "download interrupted (try $i), resuming"; sleep 30; }
done
[ "$(stat -c %s "$DL" 2>/dev/null || echo 0)" = "$SIZE" ] || { say "DOWNLOAD FAILED"; exit 1; }
zstd -tq "$DL" || { say "DOWNLOAD CORRUPT (zstd test failed)"; exit 1; }
say "downloaded and verified"

if [ ! -f "$OUT.rescaled" ]; then
  rm -f "$OUT"
  zstd -dc "$DL" | "$CONV" /dev/stdin "$OUT" every="$EVERY" >> "$LOG" 2>&1
  RC=("${PIPESTATUS[@]}")
  [ "${RC[0]}" = 0 ] && [ "${RC[1]}" = 0 ] || { say "CONVERSION FAILED (zstd ${RC[0]}, converter ${RC[1]})"; exit 1; }
  say "converted: $(( $(stat -c %s "$OUT") / 32 )) positions -> $OUT"
  .venv/bin/python tools/rescale_scores.py "$OUT" >> "$LOG" 2>&1 || { say "RESCALE FAILED"; exit 1; }
fi

D=$HOME/.cache/nexarch-kds/nexarch-t80-$MONTH
mkdir -p "$D"
ln -f "$OUT" "$D/t80-$MONTH.bin" 2>/dev/null || cp "$OUT" "$D/t80-$MONTH.bin"
printf '{"title":"nexarch-t80-%s","id":"markthegamer108/nexarch-t80-%s","licenses":[{"name":"DbCL-1.0"}]}\n' "$MONTH" "$MONTH" > "$D/dataset-metadata.json"
upload_dataset "nexarch-t80-$MONTH" "$D" "Leela T80 $MONTH, 1 in $EVERY positions, Nexarch format, scores on Nexarch's scale" \
  || { say "UPLOAD FAILED"; exit 1; }
touch "data/lc0/t80-$MONTH.done"
say "ready: markthegamer108/nexarch-t80-$MONTH"
