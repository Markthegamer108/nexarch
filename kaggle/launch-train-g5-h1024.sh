#!/bin/bash
set -u
cd "$(dirname "$0")/.."
NAME=${G5_H1024_NAME:-nexarch-train-g5-h1024}
LOG=kaggle-out/launch-$NAME.log
mkdir -p kaggle-out
. kaggle/lib.sh
BUDGET=${G5_H1024_BUDGET:-600}
EPOCHS=${G5_H1024_EPOCHS:-8}
ST=$(kernel_state "$NAME")
if [ -n "$ST" ]; then
  say "$NAME already exists ($ST): watching it instead of pushing again"
else
  REM_MIN=$( .venv/bin/kaggle quota 2>/dev/null | awk '$1 == "GPU" {print $3}' | tr -d 'h' \
    | .venv/bin/python -c 'import sys; x = sys.stdin.read().strip(); print(int(float(x) * 60) if x else 0)' )
  NEED=$(( BUDGET + 15 + 60 ))
  [ "${REM_MIN:-0}" -ge "$NEED" ] || {
    say "$NAME: needs ${NEED} min (${BUDGET} training, 15 checkpoint, 60 reserve), quota has ${REM_MIN:-0} min"
    exit 1
  }
  say "$NAME: quota check ${REM_MIN} min left, ${NEED} min required"
  push_kernel "$NAME" 40 .venv/bin/python kaggle/job.py --name "$NAME" --gpu \
    --source markthegamer108/nexarch-confirm-g4 \
    --dataset markthegamer108/nexarch-graded-g3 \
    --dataset markthegamer108/nexarch-t80-2024-01-jan \
    --dataset markthegamer108/nexarch-t80-2024-02-feb \
    --dataset markthegamer108/nexarch-t80-2024-03-mar \
    --dataset markthegamer108/nexarch-lichess-evals \
    --dataset markthegamer108/nexarch-fishnet-2025-01 \
    --dataset markthegamer108/nexarch-selfplay-2026-11-22 \
    --dataset markthegamer108/nexarch-selfplay-aws-2026-11-23 \
    --dataset markthegamer108/nexarch-selfplay-2026-11-24 \
    --cmd 'G5_MODE=h1024 G5_BUDGET='"$BUDGET"' G5_EPOCHS='"$EPOCHS"' G5_A_LR=0.0002 G5_B_LR=0.0004 bash kaggle/train-g5.sh {out} {cpus}' \
    --push || { say "could not launch $NAME"; exit 1; }
fi
bash kaggle/ensure-kernel.sh "$NAME"
say "$NAME finished"
say "candidates: $(ls kaggle-out/$NAME/g5-[ab].nnue 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')"
