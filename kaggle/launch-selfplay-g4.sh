#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/launch-selfplay-g4.log
mkdir -p kaggle-out
. kaggle/lib.sh
SECS=${1:-12300}
touch kaggle-out/sp-g4a-kernels.txt
for i in 0 1 2 3 4; do
  name=nexarch-sp-g4a-$i
  if push_kernel "$name" 240 .venv/bin/python kaggle/job.py --name "$name" --source markthegamer108/nexarch-train-g4 \
       --cmd "net=\$(find /kaggle/input -name g4-b.nnue -print -quit); ./engine/nexarch datagen threads={cpus} nodes=5000 seconds=$SECS seed=$((RANDOM * 32768 + RANDOM)) out={out}/data-g4a-k$i.bin net=\$net" \
       --push; then
    grep -qx "$name" kaggle-out/sp-g4a-kernels.txt || echo "$name" >> kaggle-out/sp-g4a-kernels.txt
    bash kaggle/ensure-kernel.sh "$name" &
  fi
done
say "Kaggle self-play launched: $(tr '\n' ' ' < kaggle-out/sp-g4a-kernels.txt)"
wait
