#!/bin/bash
cd "$(dirname "$0")/.."
K=markthegamer108/$1
OUT=kaggle-out/$1
POLL=${WATCH_POLL:-120}
MISSING_LIMIT=${WATCH_MISSING_LIMIT:-30}
mkdir -p "$OUT"
rm -f "$OUT.done"
missing=0
while true; do
  R=$(.venv/bin/kaggle kernels status "$K" 2>&1 | tail -1)
  S=$(grep -o '"[^"]*"' <<<"$R")
  echo "$(TZ=Europe/Berlin date +%H:%M) ${S:-$R}" | cut -c1-200 >> "$OUT.watch.log"
  case "$S" in *COMPLETE*|*ERROR*|*CANCEL*) break ;; esac
  if [ -z "$S" ] && grep -q 'Cannot access kernel' <<<"$R"; then missing=$((missing + 1)); else missing=0; fi
  if [ "$missing" -ge "$MISSING_LIMIT" ]; then S="MISSING (kernel not found for $((MISSING_LIMIT * POLL / 60)) min)"; break; fi
  sleep "$POLL"
done
case "$S" in
  MISSING*) ;;
  *) for i in 1 2 3 4 5 6; do .venv/bin/kaggle kernels output "$K" -p "$OUT" -o -q >> "$OUT.watch.log" 2>&1 && break; sleep 120; done ;;
esac
{ echo "status: $S"; ls -la "$OUT"; grep -v '^PASS' "$OUT/run.log" 2>/dev/null | grep -vE '^\s*$' | tail -25; } > "$OUT.done"
