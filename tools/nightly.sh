#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/nightly.log
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
say "nightly start"
FREE=$(df -BG /home/mark | tail -1 | awk '{gsub(/G/,"",$4); print $4}')
say "disk free ${FREE}G"
if [ "$FREE" -lt 40 ]; then
  say "low disk: clearing caches"
  rm -rf ~/.cache/nexarch-eval/*.parquet ~/.cache/nexarch-binpack/sf/*.binpack 2>/dev/null
fi
if [ -f kaggle-out/.primary-g5 ]; then
  say "primary h2048 experiment active: not starting the backlog"
elif pgrep -f 'fishnet-backlog.sh' >/dev/null; then
  say "backlog already running"
else
  LAST=$(ls -1 data/fishnet/*.done 2>/dev/null | sed 's/.*fishnet-//;s/\.done//' | grep -E '^[0-9]{4}-[0-9]{2}$' | sort | tail -1)
  NEXT=$(date -d "${LAST:-2024-06}-15 +1 month" '+%Y-%m' 2>/dev/null || echo 2024-07)
  say "restarting backlog at $NEXT"
  setsid nohup systemd-inhibit --what=idle:sleep:handle-lid-switch --who=nexarch --mode=block \
    --why="fishnet backlog" bash -c "HF_REPO=mark43233/nexarch-positions bash kaggle/fishnet-backlog.sh $NEXT 2025-03 1" \
    </dev/null >> kaggle-out/fishnet-backlog.run.log 2>&1 &
fi
.venv/bin/python tools/status.py >> "$LOG" 2>&1
say "nightly done"
