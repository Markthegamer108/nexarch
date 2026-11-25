#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Legacy Gen 5 launch script (h2048/h4096). Superseded by launch-train-g5-h1024.sh.

set -euo pipefail
cd "$(dirname "$0")/.."

NAME=${G5_LAUNCH_NAME:-nexarch-train-g5}
LOG=kaggle-out/launch-$NAME.log
mkdir -p kaggle-out
. kaggle/lib.sh
RESERVE=${G5_LAUNCH_RESERVE:-4}
MAXMIN=${G5_LAUNCH_MAXMIN:-660}
MINBUDGET=${G5_LAUNCH_MIN_BUDGET:-240}
ONLY=${G5_LAUNCH_ONLY:-g5-a}
case "$ONLY" in
  g5-a|g5-b|both) ;;
  *) say "G5_LAUNCH_ONLY must be g5-a, g5-b or both"; exit 1 ;;
esac
SETS=(
  --dataset markthegamer108/nexarch-graded-g3
  --dataset markthegamer108/nexarch-t80-2024-01-jan
  --dataset markthegamer108/nexarch-t80-2024-02-feb
  --dataset markthegamer108/nexarch-t80-2024-03-mar
  --dataset markthegamer108/nexarch-lichess-evals
  --dataset markthegamer108/nexarch-fishnet-2025-01
  --dataset markthegamer108/nexarch-selfplay-2026-11-22
  --dataset markthegamer108/nexarch-g5-starts
)
if [ -n "${G5_LAUNCH_BUDGET:-}" ]; then
  BUDGET=$G5_LAUNCH_BUDGET
  say "$NAME: budget forced to ${BUDGET} min per candidate"
else
  REM=$( .venv/bin/kaggle quota 2>/dev/null | awk '$1 == "GPU" {print $3}' | tr -d 'h' )
  [ -n "$REM" ] || { say "could not read the GPU quota: not launching $NAME"; exit 1; }
  BUDGET=$( .venv/bin/python -c "
r = float('$REM')
print(max(30, min($MAXMIN, int((r - $RESERVE) * 30))))
" )
  say "$NAME: GPU quota left ${REM}h, reserving ${RESERVE}h: ${BUDGET} min per candidate"
fi
ST=$(kernel_state "$NAME")
if [ -n "$ST" ]; then
  say "$NAME already exists ($ST): watching it instead of pushing again"
else
  [ "$ONLY" = g5-a ] || [ ! -f kaggle-out/.primary-g5 ] || {
    say "primary h2048 experiment is active: refusing to start $ONLY"
    exit 1
  }
  [ "$BUDGET" -ge "$MINBUDGET" ] || {
    say "not launching $NAME: ${BUDGET} min is below the ${MINBUDGET} min minimum"
    exit 1
  }
  CAND=1
  [ "$ONLY" = both ] && CAND=2
  REM_MIN=$( .venv/bin/kaggle quota 2>/dev/null | awk '$1 == "GPU" {print $3}' | tr -d 'h' \
    | .venv/bin/python -c 'import sys; x = sys.stdin.read().strip(); print(int(float(x) * 60) if x else 0)' )
  NEED=$(( CAND * BUDGET + CAND * 15 + 60 ))
  [ "${REM_MIN:-0}" -ge "$NEED" ] || {
    say "not launching $NAME: $ONLY needs ${NEED} min (${CAND} x ${BUDGET} min training, ${CAND} x 15 min checkpoint and export, 60 min reserve), quota has ${REM_MIN:-0} min"
    exit 1
  }
  say "quota check: ${REM_MIN} min left, ${NEED} min required for $ONLY"
  [ "$ONLY" = g5-a ] && date -u +%FT%TZ > kaggle-out/.primary-g5
  push_kernel "$NAME" 40 .venv/bin/python kaggle/job.py --name "$NAME" --gpu --internet \
    "${SETS[@]}" --cmd "G5_BUDGET=$BUDGET G5_EPOCHS=${G5_LAUNCH_EPOCHS:-8} G5_ONLY=$ONLY bash kaggle/train-g5.sh {out} {cpus}" \
    --push || { say "could not launch $NAME"; exit 1; }
fi
bash kaggle/ensure-kernel.sh "$NAME"
say "$NAME finished: $(head -1 kaggle-out/$NAME.done 2>/dev/null)"
say "candidates: $(ls kaggle-out/$NAME/g5-[ab].nnue 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')"
