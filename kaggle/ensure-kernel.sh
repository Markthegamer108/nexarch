#!/bin/bash
cd "$(dirname "$0")/.."
N=$1
while [ ! -f "kaggle-out/$N.done" ]; do
  if pgrep -f "watch-job\.sh $N\$" >/dev/null; then sleep 60; else bash kaggle/watch-job.sh "$N"; fi
done
