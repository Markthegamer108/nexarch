#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p kaggle-out
exec 8>kaggle-out/.supervise-g5.lock
flock -n 8 || exit 0
exec >>kaggle-out/supervise-g5.log 2>&1
date -Is
awk '/^(MemAvailable|SwapFree):/ {print}' /proc/meminfo
cat /proc/pressure/memory
ps -eo pid,rss,comm --sort=-rss | head -7
df -h --output=avail . | tail -1
failed=0
for name in nexarch-train-g5-a nexarch-holdout-g5; do
  printf '%s ' "$name"
  bash kaggle/collect-g5-job.sh "$name" || failed=1
done
exit "$failed"
