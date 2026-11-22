#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/launch-train-g4.log
mkdir -p kaggle-out
. kaggle/lib.sh
say "waiting for Gen 3 and both datasets"
for m in kaggle-out/nexarch-train-g3.done data/lc0/t80-2024-01-jan.done data/lichess/lichess.done; do
  while [ ! -f "$m" ]; do sleep 60; done
done
grep -q 'COMPLETE' kaggle-out/nexarch-train-g3.done || { say "Gen 3 did not complete: not launching Gen 4"; exit 1; }
[ -s kaggle-out/nexarch-train-g3/nexarch-g3.pt ] || { say "no Gen 3 checkpoint in kaggle-out/nexarch-train-g3"; exit 1; }
ST=$(kernel_state nexarch-train-g4)
if [ -n "$ST" ]; then
  say "nexarch-train-g4 already exists ($ST): watching it instead of pushing again"
else
  push_kernel nexarch-train-g4 40 .venv/bin/python kaggle/job.py --name nexarch-train-g4 --gpu --internet \
    --dataset markthegamer108/nexarch-graded-g3 --dataset markthegamer108/nexarch-t80-2024-01-jan \
    --dataset markthegamer108/nexarch-lichess-evals --source markthegamer108/nexarch-train-g3 \
    --cmd 'bash kaggle/train-g4.sh {out} {cpus}' --push || { say "could not launch Gen 4"; exit 1; }
fi
bash kaggle/ensure-kernel.sh nexarch-train-g4
say "Gen 4 finished: $(head -1 kaggle-out/nexarch-train-g4.done)"
say "vs Gen 3: $(grep 'match result' kaggle-out/nexarch-train-g4/vs-g3.txt 2>/dev/null)"
