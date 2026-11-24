#!/bin/bash
set -u
cd "$(dirname "$0")/.."
MONTH=${1:?month, e.g. 2025-01}
EVERY=${2:-1}
LOG=kaggle-out/prepare-fishnet-$MONTH.log
exec 9>"kaggle-out/.fishnet-$MONTH.lock"
flock -n 9 || { echo "$MONTH is already being prepared by another process" >> "$LOG"; exit 1; }
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
  rm -f "$OUT" "$OUT.done" "$OUT.rescaled"
  .venv/bin/python tools/fishnet_evals.py "$DL" --out-dir data/fishnet --every "$EVERY" --batch 500000 >> "$LOG" 2>&1 \
    || { say "CONVERSION FAILED"; exit 1; }
  say "converted: $(( $(stat -c %s "$OUT") / 32 )) positions -> $OUT"
  .venv/bin/python tools/rescale_scores.py "$OUT" --calibration nets/lichess-calibration.json >> "$LOG" 2>&1 \
    || { say "RESCALE FAILED"; exit 1; }
fi

N=$(( $(stat -c %s "$OUT") / 32 ))
BYTES=$(stat -c %s "$OUT")
.venv/bin/python tools/write_manifest.py --bin "$OUT" --month "$MONTH" --every "$EVERY" \
  --source "https://huggingface.co/datasets/Lichess/fishnet-evals/resolve/main/standard_rated_${MONTH/-/_}.parquet" \
  --out "data/fishnet/fishnet-$MONTH.manifest.json" >> "$LOG" 2>&1 || { say "MANIFEST FAILED"; exit 1; }
.venv/bin/python tools/audit_data.py data/fishnet --glob "fishnet-$MONTH.bin" >> "$LOG" 2>&1 \
  || { say "AUDIT FAILED"; exit 1; }
if [ -n "${HF_REPO:-}" ]; then
  .venv/bin/hf upload "$HF_REPO" "$OUT" "fishnet-$MONTH.bin" --repo-type dataset >> "$LOG" 2>&1 \
    || { say "HF UPLOAD FAILED"; exit 1; }
  .venv/bin/hf upload "$HF_REPO" "data/fishnet/fishnet-$MONTH.manifest.json" "fishnet-$MONTH.manifest.json" --repo-type dataset >> "$LOG" 2>&1 \
    || say "manifest upload failed (continuing)"
  REMOTE=$(.venv/bin/python -c "
import json, urllib.request
u = 'https://huggingface.co/api/datasets/$HF_REPO/tree/main?recursive=true'
d = json.load(urllib.request.urlopen(u, timeout=90))
print(next((((x.get('lfs') or {}).get('size') or x.get('size') or 0) for x in d if x.get('path') == 'fishnet-$MONTH.bin'), 0))
")
  if [ "$REMOTE" != "$BYTES" ]; then
    sleep 45
    REMOTE=$(.venv/bin/python -c "
import json, urllib.request
u = 'https://huggingface.co/api/datasets/$HF_REPO/tree/main?recursive=true'
d = json.load(urllib.request.urlopen(u, timeout=90))
print(next((((x.get('lfs') or {}).get('size') or x.get('size') or 0) for x in d if x.get('path') == 'fishnet-$MONTH.bin'), 0))
")
  fi
  [ "$REMOTE" = "$BYTES" ] || { say "VERIFY FAILED: remote $REMOTE != local $BYTES"; exit 1; }
  say "verified: https://huggingface.co/datasets/$HF_REPO/fishnet-$MONTH.bin, $N positions, $BYTES bytes"
else
  D=$HOME/.cache/nexarch-kds/nexarch-fishnet-$MONTH
  mkdir -p "$D"
  ln -f "$OUT" "$D/fishnet-$MONTH.bin" 2>/dev/null || cp "$OUT" "$D/fishnet-$MONTH.bin"
  printf '{"title":"nexarch-fishnet-%s","id":"markthegamer108/nexarch-fishnet-%s","licenses":[{"name":"MIT"}]}\n' "$MONTH" "$MONTH" > "$D/dataset-metadata.json"
  mit_license "$D"
  upload_dataset nexarch-fishnet-$MONTH "$D" "Lichess fishnet evaluations $MONTH (CC0), 1 in $EVERY, $N positions, converted to Nexarch format by Mark Ivanovskyy (MIT)" \
    || { say "UPLOAD FAILED"; exit 1; }
  say "ready: markthegamer108/nexarch-fishnet-$MONTH, $N positions"
fi
if [ "${FISHNET_KEEP:-0}" != 1 ]; then
  rm -f "$OUT" "$DL" "$OUT.rescaled"
  say "cleaned local copies of $MONTH"
fi
