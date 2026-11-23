#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/pipeline.log
say() { echo "$(date '+%F %T') $*" >> "$LOG"; }
say "pipeline start"

pick_next_month() {
  local last next
  last=$(ls -1 data/fishnet/*.done 2>/dev/null | sed 's/.*fishnet-//;s/\.done//' | grep -E '^[0-9]{4}-[0-9]{2}$' | sort | tail -1)
  next=$(date -d "${last:-2024-06}-15 +1 month" '+%Y-%m' 2>/dev/null) || return 1
  echo "$next"
}

if pgrep -f 'kaggle/fishnet-backlog\.sh' >/dev/null; then
  say "backlog already running"
else
  NEXT=$(pick_next_month) || { say "cannot compute next month"; exit 1; }
  say "starting backlog at $NEXT"
  setsid nohup systemd-inhibit --what=idle:sleep:handle-lid-switch --who=nexarch --mode=block \
    --why="fishnet backlog" bash -c "HF_REPO=mark43233/nexarch-positions bash kaggle/fishnet-backlog.sh $NEXT 2025-03 1" \
    </dev/null >> kaggle-out/fishnet-backlog.run.log 2>&1 &
  sleep 5
fi

say "pipeline start done"
