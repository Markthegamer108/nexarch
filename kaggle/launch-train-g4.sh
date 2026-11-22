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
[ -s kaggle-out/nexarch-train-g3/nexarch-g3.nnue ] || { say "no Gen 3 network in kaggle-out/nexarch-train-g3"; exit 1; }
S1=$(sed -n 's/.*match result:.*score \([0-9.]*\)%.*/\1/p' kaggle-out/nexarch-train-g3/vs-g2.txt 2>/dev/null | tail -1)
S2=$(sed -n 's/.*match result:.*score \([0-9.]*\)%.*/\1/p' kaggle-out/nexarch-train-g3/vs-g2-nodes.txt 2>/dev/null | tail -1)
.venv/bin/python -c "import sys; sys.exit(0 if max(float('${S1:-0}'), float('${S2:-0}')) >= 50 else 1)" \
  || { say "Gen 3 did not beat Gen 2 (timed ${S1:-?}%, nodes ${S2:-?}%): not launching Gen 4"; exit 1; }
REM=$( .venv/bin/kaggle quota 2>/dev/null | awk '$1 == "GPU" {print $3}' | tr -d 'h' )
[ -n "$REM" ] || { say "could not read the GPU quota: not launching Gen 4"; exit 1; }
BUDGET=$( .venv/bin/python -c "
r = float('$REM')
wall = min(6.0, (r - 1.5) / 2.0) - 0.3
print(max(60, min(300, int((wall - 0.2) * 60))))
" )
say "GPU quota left ${REM}h: training ${BUDGET} min per candidate, matches on CPU afterwards"
say "Gen 3: timed ${S1:-?}% / nodes ${S2:-?}% vs Gen 2"
ST=$(kernel_state nexarch-train-g4)
if [ -n "$ST" ]; then
  say "nexarch-train-g4 already exists ($ST): watching it instead of pushing again"
else
  push_kernel nexarch-train-g4 40 .venv/bin/python kaggle/job.py --name nexarch-train-g4 --gpu --internet \
    --dataset markthegamer108/nexarch-graded-g3 --dataset markthegamer108/nexarch-t80-2024-01-jan \
    --dataset markthegamer108/nexarch-lichess-evals --source markthegamer108/nexarch-train-g3 \
    --cmd "G4_BUDGET=$BUDGET G4_GAMES=0 G4_FINAL_GAMES=0 bash kaggle/train-g4.sh {out} {cpus}" \
    --push || { say "could not launch Gen 4"; exit 1; }
fi
bash kaggle/ensure-kernel.sh nexarch-train-g4
say "Gen 4 finished: $(head -1 kaggle-out/nexarch-train-g4.done)"
say "candidates: $(ls kaggle-out/nexarch-train-g4/g4-[ab].nnue 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')"
