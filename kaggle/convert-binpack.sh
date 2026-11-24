#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/.."
NAME=${1:?binpack name without .binpack}
FILTER=${2:-0}
MAXP=${3:-0}
LOG=kaggle-out/convert-binpack-$NAME.log
exec 9>"kaggle-out/.convert-binpack-$NAME.lock"
flock -n 9 || { echo "$NAME is already being converted" >> "$LOG"; exit 1; }
mkdir -p kaggle-out data/binpacks
. kaggle/lib.sh
TOOL=$HOME/.cache/nexarch-binpack/build/binpack2nexarch
SRC=$HOME/.cache/nexarch-binpack/sf/$NAME.binpack
OUT=data/binpacks/$NAME.bin
MAN=data/binpacks/$NAME.manifest.json
URL=https://huggingface.co/datasets/official-stockfish/master-binpacks/resolve/main/$NAME.binpack
[ -x "$TOOL" ] || { say "missing $TOOL: run tools/binpack/build.sh"; exit 1; }

SIZE=$(curl -sIL "$URL" | grep -i '^content-length' | tail -1 | tr -dc '0-9')
[ -n "$SIZE" ] || { say "cannot reach $URL"; exit 1; }
say "downloading $NAME.binpack ($((SIZE / 1000000)) MB)"
for i in 1 2 3 4 5; do
  [ "$(stat -c %s "$SRC" 2>/dev/null || echo 0)" = "$SIZE" ] && break
  curl -sSfL -C - --retry 5 -o "$SRC" "$URL" >> "$LOG" 2>&1 || { say "download interrupted (try $i), resuming"; sleep 30; }
done
[ "$(stat -c %s "$SRC" 2>/dev/null || echo 0)" = "$SIZE" ] || { say "DOWNLOAD FAILED"; exit 1; }
say "downloaded and verified"

if [ "$MAXP" -le 0 ]; then
  FREE=$(df -B1 . | awk 'NR == 2 {print $4}')
  MAXP=$(( (FREE - 20 * 1024 * 1024 * 1024) / 32 ))
fi
[ "$MAXP" -gt 0 ] || { say "not enough disk for another binpack"; exit 1; }
say "converting up to $MAXP positions, filter=$FILTER"
"$TOOL" "$SRC" "$OUT" max="$MAXP" filter="$FILTER" >> "$LOG" 2>&1 || { say "CONVERSION FAILED"; exit 1; }
BYTES=$(stat -c %s "$OUT")
N=$(( BYTES / 32 ))
if [ $((BYTES % 32)) -ne 0 ]; then
  say "trimming a partial record"
  truncate -s $((N * 32)) "$OUT"
  BYTES=$((N * 32))
fi
say "converted $N positions -> $OUT"
[ "$N" -lt "$MAXP" ] || say "note: conversion reached the disk budget, so this file is a prefix"
.venv/bin/python - <<PY >> "$LOG" 2>&1
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, 'tools')
from audit_holdout import read_records, malformed
p = Path('$OUT')
h = hashlib.sha256()
with p.open('rb') as f:
    for block in iter(lambda: f.read(1 << 24), b''):
        h.update(block)
with p.open('rb') as f:
    head = f.read(32 * 200000)
    f.seek(max(0, p.stat().st_size - 32 * 200000))
    tail = f.read(32 * 200000)
for label, data in (('head', head), ('tail', tail)):
    r, w = read_records(data)
    bad = int(malformed(r, w).sum())
    if bad:
        raise SystemExit(f'{label}: {bad} malformed records')
manifest = {
    'name': '$NAME',
    'source': 'https://huggingface.co/datasets/official-stockfish/master-binpacks/resolve/main/$NAME.binpack',
    'license': 'ODbL-1.0',
    'records': p.stat().st_size // 32,
    'bytes': p.stat().st_size,
    'sha256': h.hexdigest(),
    'filter': int('$FILTER'),
    'max': int('$MAXP'),
    'capped': (p.stat().st_size // 32) >= int('$MAXP'),
    'converter': 'tools/binpack/binpack2nexarch.cpp',
    'created': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
}
if manifest['capped']:
    manifest['note'] = 'prefix of the source binpack: the conversion stopped at the local disk budget'

Path('$MAN').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest))
PY
[ -s "$MAN" ] || { say "MANIFEST FAILED"; exit 1; }
SHA=$( .venv/bin/python -c "import json; print(json.load(open('$MAN'))['sha256'])" )
.venv/bin/hf upload mark43233/nexarch-binpacks "$OUT" "binpacks/$NAME.bin" --repo-type dataset >> "$LOG" 2>&1 \
  || { say "HF UPLOAD FAILED"; exit 1; }
.venv/bin/hf upload mark43233/nexarch-binpacks "$MAN" "binpacks/$NAME.manifest.json" --repo-type dataset >> "$LOG" 2>&1 \
  || say "manifest upload failed (continuing)"
REMOTE=$( .venv/bin/python - <<PY
from huggingface_hub import HfApi
info = HfApi().dataset_info('mark43233/nexarch-binpacks', files_metadata=True)
print(next((s.size for s in info.siblings if s.rfilename == 'binpacks/$NAME.bin'), 0))
PY
)
[ "$REMOTE" = "$BYTES" ] || { say "VERIFY FAILED: remote $REMOTE != local $BYTES"; exit 1; }
say "verified: https://huggingface.co/datasets/mark43233/nexarch-binpacks/binpacks/$NAME.bin, $N positions, sha256 $SHA"
if [ "${KEEP:-0}" != 1 ]; then
  rm -f "$OUT" "$SRC"
  say "cleaned local copies of $NAME"
fi
