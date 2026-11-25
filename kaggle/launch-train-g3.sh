#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Launch Gen 3 training after combined dataset is ready.

set -euo pipefail
cd "$(dirname "$0")/.."

LOG=kaggle-out/launch-train-g3.log
mkdir -p kaggle-out
. kaggle/lib.sh

say "waiting for data/graded-g3-full.done"
while [ ! -f data/graded-g3-full.done ]; do
  [ -f data/graded-g3-full.failed ] && { say "building the combined set failed: not training (kaggle-out/finish-g3.log)"; exit 1; }
  sleep 60
done
[ -s data/graded-g3-full.bin ] || { say "data/graded-g3-full.bin missing"; exit 1; }
say "combined: $(( $(stat -c %s data/graded-g3-full.bin) / 32 )) positions"

ST=$(kernel_state nexarch-train-g3)
if [ -n "$ST" ]; then
  say "nexarch-train-g3 already exists ($ST): watching it instead of pushing again"
else
  D=/home/mark/.cache/nexarch-kds/nexarch-graded-g3
  mkdir -p "$D"
  ln -f data/graded-g3-full.bin "$D/graded-g3-full.bin" 2>/dev/null || cp data/graded-g3-full.bin "$D/graded-g3-full.bin"
  cp -f nets/nexarch-g2.pt "$D/nexarch-g2.pt"
  printf '{"title":"nexarch-graded-g3","id":"markthegamer108/nexarch-graded-g3","licenses":[{"name":"MIT"}]}\n' > "$D/dataset-metadata.json"
  mit_license "$D"
  upload_dataset nexarch-graded-g3 "$D" "graded g2 + g2d, plus the Gen 2 checkpoint" || { say "UPLOAD FAILED: not training"; exit 1; }

  push_kernel nexarch-train-g3 40 .venv/bin/python kaggle/job.py --name nexarch-train-g3 --gpu --internet \
    --dataset markthegamer108/nexarch-graded-g3 --cmd 'bash kaggle/train-g3.sh {out} {cpus}' \
    --push || { say "could not launch the training job"; exit 1; }
fi
bash kaggle/ensure-kernel.sh nexarch-train-g3
say "training job finished: $(head -1 kaggle-out/nexarch-train-g3.done)"
say "vs Gen 2: $(grep 'match result' kaggle-out/nexarch-train-g3/vs-g2.txt 2>/dev/null)"
