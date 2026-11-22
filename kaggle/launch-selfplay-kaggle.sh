#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/launch-selfplay-kaggle.log
mkdir -p kaggle-out
. kaggle/lib.sh
touch kaggle-out/sp-g2e-kernels.txt
for i in 0 1 2 3 4; do
  name=nexarch-sp-g2e-$i
  if push_kernel "$name" 240 .venv/bin/python kaggle/job.py --name "$name" \
       --cmd "./engine/nexarch datagen threads={cpus} nodes=5000 seconds=39000 seed=$((RANDOM * 32768 + RANDOM)) out={out}/data-g2e-k$i.bin net=nets/nexarch-g2.nnue" \
       --push; then
    grep -qx "$name" kaggle-out/sp-g2e-kernels.txt || echo "$name" >> kaggle-out/sp-g2e-kernels.txt
    bash kaggle/ensure-kernel.sh "$name" &
  fi
done
say "Kaggle self-play launched: $(tr '\n' ' ' < kaggle-out/sp-g2e-kernels.txt)"
wait
