#!/bin/bash
# Wait for a Kaggle kernel to finish, then download its whole output to kaggle-out/<name>.
#   bash kaggle/watch-job.sh nexarch-grade-g2-lc0     (log: kaggle-out/<name>.watch.log, marker: kaggle-out/<name>.done)
cd "$(dirname "$0")/.."
K=markthegamer108/$1
OUT=kaggle-out/$1
mkdir -p "$OUT"
rm -f "$OUT.done"
while true; do
  S=$(.venv/bin/kaggle kernels status "$K" 2>&1 | tail -1 | grep -o '"[^"]*"')
  echo "$(TZ=Europe/Berlin date +%H:%M) $S" >> "$OUT.watch.log"
  case "$S" in *COMPLETE*|*ERROR*|*CANCEL*) break ;; esac
  sleep 120
done
for i in 1 2 3; do .venv/bin/kaggle kernels output "$K" -p "$OUT" -o -q >> "$OUT.watch.log" 2>&1 && break; sleep 60; done
{ echo "status: $S"; ls -la "$OUT"; grep -v '^PASS' "$OUT/run.log" 2>/dev/null | grep -vE '^\s*$' | tail -25; } > "$OUT.done"
