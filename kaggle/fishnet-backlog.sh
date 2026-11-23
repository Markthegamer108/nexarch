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
  Y=${M%-*}; MON=${M#*-}
  N=$(date -d "$Y-$MON-15 +1 month" '+%Y-%m' 2>/dev/null) || { say "bad month $M"; exit 1; }
  say "=== $M ==="
  bash kaggle/prepare-fishnet.sh "$M" "$EVERY" || { say "$M failed, stopping here"; exit 1; }
  [ "$M" = "$TO" ] && break
  M=$N
done
say "fishnet backlog finished: $FROM to $TO"
touch data/fishnet/backlog.done
