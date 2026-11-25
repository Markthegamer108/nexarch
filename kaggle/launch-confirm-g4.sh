#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Wait for Gen 4 training to complete, then launch confirmation.

set -euo pipefail
cd "$(dirname "$0")/.."

LOG=kaggle-out/launch-confirm-g4.log
mkdir -p kaggle-out
. kaggle/lib.sh

say "waiting for Gen 4 to finish"
while [ ! -f kaggle-out/nexarch-train-g4.done ]; do sleep 60; done
grep -q 'COMPLETE' kaggle-out/nexarch-train-g4.done || { say "Gen 4 did not complete: not confirming"; exit 1; }
{ [ -s kaggle-out/nexarch-train-g4/nexarch-g4.nnue ] || [ -s kaggle-out/nexarch-train-g4/g4-a.nnue ] \
  || [ -s kaggle-out/nexarch-train-g4/g4-b.nnue ]; } || { say "no Gen 4 network in kaggle-out/nexarch-train-g4"; exit 1; }
ST=$(kernel_state nexarch-confirm-g4)
if [ -n "$ST" ]; then
  say "nexarch-confirm-g4 already exists ($ST): watching it instead of pushing again"
else
  push_kernel nexarch-confirm-g4 40 .venv/bin/python kaggle/job.py --name nexarch-confirm-g4 --internet \
    --source markthegamer108/nexarch-train-g4 --source markthegamer108/nexarch-train-g3 \
    --cmd 'bash kaggle/confirm-g4.sh {out} {cpus}' --push || { say "could not launch the confirmation"; exit 1; }
fi
bash kaggle/ensure-kernel.sh nexarch-confirm-g4
say "Gen 4 confirmed: $(head -1 kaggle-out/nexarch-confirm-g4.done)"
for f in vs-g3 vs-g2 vs-g3-nodes; do
  say "$f: $(grep 'match result' kaggle-out/nexarch-confirm-g4/$f.txt 2>/dev/null)"
done
