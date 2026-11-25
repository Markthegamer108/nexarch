#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Launch Gen 5 full-data continuation from h2048 checkpoint.

set -euo pipefail
cd "$(dirname "$0")/.."

NAME=${G5_FULL_NAME:-nexarch-train-g5-full-a}
LOG=kaggle-out/launch-$NAME.log
mkdir -p kaggle-out
. kaggle/lib.sh
BUDGET=${G5_FULL_BUDGET:-600}
D=kaggle-out/nexarch-train-g5-a
if [ ! -f "$D/collected/remote-status" ]; then
  say "$NAME: the h2048 run is not complete yet"
  exit 1
fi
S=$(cat "$D/collected/remote-status")
{ [ "$S" = COMPLETE ] || [ "$S" = COMPLETE_PARTIAL ]; } || {
  say "$NAME: the h2048 run ended as $S"
  exit 1
}
PT=$(find "$D" -name 'g5-a.pt' -print -quit)
[ -n "$PT" ] || { say "$NAME: no g5-a.pt in $D"; exit 1; }
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
  push_kernel "$NAME" 40 .venv/bin/python kaggle/job.py --name "$NAME" --gpu --internet \
    --source markthegamer108/nexarch-train-g5-a \
    --dataset markthegamer108/nexarch-graded-g3 \
    --dataset markthegamer108/nexarch-t80-2024-01-jan \
    --dataset markthegamer108/nexarch-t80-2024-02-feb \
    --dataset markthegamer108/nexarch-t80-2024-03-mar \
    --dataset markthegamer108/nexarch-lichess-evals \
    --dataset markthegamer108/nexarch-fishnet-2025-01 \
    --dataset markthegamer108/nexarch-selfplay-2026-11-22 \
    --dataset markthegamer108/nexarch-g5-starts \
    --cmd 'R=$(find /kaggle/input -name g5-a.pt -print -quit); test -n "$R" || exit 1; P=/kaggle/working/fishpack32-part0.bin; EXPECTED_SHA="7603dd47c059346c5516c339648e688adfcf0e1c390b915d91da0909152ca5b7"; for i in 1 2 3; do curl -sSfL -r 0- https://huggingface.co/datasets/mark43233/nexarch-binpacks/resolve/main/binpacks/fishpack32.bin | head -c 15000000000 > "$P"; ACTUAL=$(sha256sum "$P" | cut -d" " -f1); [ "$ACTUAL" = "$EXPECTED_SHA" ] && break; echo "SHA mismatch: got $ACTUAL, expected $EXPECTED_SHA"; rm -f "$P"; sleep 30; done; [ "$(stat -c %s "$P" 2>/dev/null || echo 0)" = 15000000000 ] && break; rm -f "$P"; sleep 30; done; test "$(stat -c %s "$P")" = 15000000000; G5_BUDGET='"$BUDGET"' G5_EPOCHS=8 G5_ONLY=g5-a G5_RESUME="$R" G5_A_LR=0.0003 G5_EXTRA_DATA="$P" bash kaggle/train-g5.sh {out} {cpus}' \
    --push || { say "could not launch $NAME"; exit 1; }
fi
bash kaggle/ensure-kernel.sh "$NAME"
say "$NAME finished: $(head -1 kaggle-out/$NAME.done 2>/dev/null)"
say "candidates: $(ls kaggle-out/$NAME/g5-[ab].nnue 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')"
