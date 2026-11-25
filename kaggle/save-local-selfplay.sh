#!/bin/bash
set -u
cd "$(dirname "$0")/.."
FILE=${1:?self-play .bin file}
DATE=${2:-$(TZ=Europe/Berlin date +%F)}
LOG=kaggle-out/save-local-selfplay.log
mkdir -p kaggle-out
. kaggle/lib.sh
[ -s "$FILE" ] || { say "missing $FILE"; exit 1; }
SIZE=$(stat -c %s "$FILE")
N=$((SIZE / 32))
if [ $((SIZE % 32)) -ne 0 ]; then
  say "trimming a partial record from $FILE"
  truncate -s $((N * 32)) "$FILE"
  SIZE=$((N * 32))
fi
say "auditing $FILE ($N positions)"
.venv/bin/python tools/audit_data.py "$(dirname "$FILE")" --glob "$(basename "$FILE")" >> "$LOG" 2>&1 \
  || { say "AUDIT FAILED"; exit 1; }
D=$HOME/.cache/nexarch-kds/nexarch-selfplay-$DATE
mkdir -p "$D"
ln -f "$FILE" "$D/selfplay-$DATE.bin" 2>/dev/null || cp "$FILE" "$D/selfplay-$DATE.bin"
printf '{"title":"nexarch-selfplay-%s","id":"markthegamer108/nexarch-selfplay-%s","licenses":[{"name":"MIT"}]}\n' "$DATE" "$DATE" > "$D/dataset-metadata.json"
mit_license "$D"
upload_dataset nexarch-selfplay-$DATE "$D" "Self-play on $DATE, $N positions, Nexarch" \
  || { say "UPLOAD FAILED: the local file is still in $FILE"; exit 1; }
touch "data/selfplay-$DATE.done"
say "ready: markthegamer108/nexarch-selfplay-$DATE, $N positions"
