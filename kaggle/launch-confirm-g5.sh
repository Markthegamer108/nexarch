#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/launch-confirm-g5.log
mkdir -p kaggle-out
. kaggle/lib.sh
say "waiting for the h2048 candidate"
while :; do
  D=kaggle-out/nexarch-train-g5-a
  if [ -f "$D/collected/remote-status" ]; then
    S=$(cat "$D/collected/remote-status")
    [ "$S" = COMPLETE ] && break
    say "h2048 job ended as $S: not confirming"
    exit 1
  fi
  if [ -f kaggle-out/nexarch-train-g5-a.done ]; then
    grep -q 'status: .*COMPLETE' kaggle-out/nexarch-train-g5-a.done && break
    say "h2048 job did not complete: not confirming"
    exit 1
  fi
  sleep 120
done
D=kaggle-out/nexarch-train-g5-a
NET=$(find "$D" -name 'g5-a.nnue' -o -name 'g5-b.nnue' -o -name 'nexarch-g5.nnue' 2>/dev/null | head -1)
[ -n "$NET" ] || { say "no Gen 5 network in $D: not confirming"; exit 1; }
say "candidate found: $NET"
ST=$(kernel_state nexarch-confirm-g5)
if [ -n "$ST" ]; then
  say "nexarch-confirm-g5 already exists ($ST): watching it instead of pushing again"
else
  push_kernel nexarch-confirm-g5 40 .venv/bin/python kaggle/job.py --name nexarch-confirm-g5 --internet \
    --source markthegamer108/nexarch-train-g5-a \
    --source markthegamer108/nexarch-confirm-g4 \
    --dataset markthegamer108/nexarch-evalset-g5-unseen \
    --dataset markthegamer108/nexarch-engines \
    --cmd 'bash kaggle/confirm-g5.sh {out} {cpus}' --push || { say "could not launch the confirmation"; exit 1; }
fi
bash kaggle/ensure-kernel.sh nexarch-confirm-g5
say "Gen 5 confirmed: $(head -1 kaggle-out/nexarch-confirm-g5.done 2>/dev/null)"
for f in unseen vs-g4 vs-g4-nodes vs-g3 panel; do
  [ -f "kaggle-out/nexarch-confirm-g5/$f.txt" ] && say "$f: $(tail -1 "kaggle-out/nexarch-confirm-g5/$f.txt")"
done
