#!/bin/bash
set -u
cd "$(dirname "$0")/.."
NAME=${G5_LAUNCH_NAME:-nexarch-train-g5}
LOG=kaggle-out/launch-$NAME.log
mkdir -p kaggle-out
. kaggle/lib.sh
RESERVE=${G5_LAUNCH_RESERVE:-4}
MAXMIN=${G5_LAUNCH_MAXMIN:-690}
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
  push_kernel "$NAME" 40 .venv/bin/python kaggle/job.py --name "$NAME" --gpu --internet \
    "${SETS[@]}" --cmd "G5_BUDGET=$BUDGET G5_EPOCHS=${G5_LAUNCH_EPOCHS:-8} G5_ONLY=${G5_LAUNCH_ONLY:-both} bash kaggle/train-g5.sh {out} {cpus}" \
    --push || { say "could not launch $NAME"; exit 1; }
fi
bash kaggle/ensure-kernel.sh "$NAME"
say "$NAME finished: $(head -1 kaggle-out/$NAME.done 2>/dev/null)"
say "candidates: $(ls kaggle-out/$NAME/g5-[ab].nnue 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')"
