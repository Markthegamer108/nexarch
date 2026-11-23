#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/fishnet-backlog.log
mkdir -p kaggle-out
. kaggle/lib.sh
FROM=${1:-2024-06}
TO=${2:-2025-03}
EVERY=${3:-5}
say "fishnet backlog: $FROM to $TO, every=$EVERY"
M=$FROM
while true; do
  if [ -f "data/fishnet/fishnet-$M.done" ]; then
    say "$M already done, skipping"
  else
    say "=== $M ==="
    bash kaggle/prepare-fishnet.sh "$M" "$EVERY" >> "$LOG" 2>&1 || { say "$M failed, stopping here"; exit 1; }
    say "$M: $(grep -o 'ready: .*' "$LOG" | tail -1)"
  fi
  [ "$M" = "$TO" ] && break
  M=$(date -d "${M}-15 +1 month" '+%Y-%m') || { say "cannot step past $M"; exit 1; }
done
say "fishnet backlog finished: $FROM to $TO"
touch data/fishnet/backlog.done
