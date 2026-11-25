#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Launch 33-engine panel benchmark on Kaggle CPU.
# Compares Gen 5 candidate vs Gen 4 baseline across 32 engines (Maia 1900 skipped).

set -euo pipefail
cd "$(dirname "$0")/.."

NAME=${PANEL_NAME:-nexarch-panel-g5}
LOG=kaggle-out/launch-$NAME.log
mkdir -p kaggle-out
. kaggle/lib.sh
[ -s kaggle-out/nexarch-confirm-g5/nexarch-g5.nnue ] || {
  say "$NAME: missing Gen 5 network"
  exit 1
}
[ -s kaggle-out/nexarch-confirm-g4/nexarch-g4.nnue ] || {
  say "$NAME: missing Gen 4 network"
  exit 1
}
ST=$(kernel_state "$NAME")
if [ -n "$ST" ]; then
  say "$NAME already exists ($ST): watching it instead of pushing again"
else
  push_kernel "$NAME" 20 .venv/bin/python kaggle/job.py --name "$NAME" --internet \
    --source markthegamer108/nexarch-confirm-g5 \
    --source markthegamer108/nexarch-confirm-g4 \
    --dataset markthegamer108/nexarch-engines \
    --cmd 'bash kaggle/setup-engines.sh; G5=$(find /kaggle/input -name nexarch-g5.nnue -print -quit); G4=$(find /kaggle/input -name nexarch-g4.nnue -print -quit); test -n "$G5" -a -n "$G4" || exit 1; python tools/panel_match.py --candidate "$G5" --incumbent "$G4" --panel nets/graders.json --book openings/uho-8mvs.epd --out {out}/panel --pairs 8 --movetime 100 --concurrency 3 --allow-missing | tee {out}/panel.txt' \
    --push || { say "could not launch $NAME"; exit 1; }
fi
bash kaggle/ensure-kernel.sh "$NAME"
say "$NAME finished"
[ -f "kaggle-out/$NAME/panel.txt" ] && say "panel: $(tail -3 "kaggle-out/$NAME/panel.txt" | tr '\n' ' ')"
