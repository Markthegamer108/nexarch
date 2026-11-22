#!/bin/bash
cd "$(dirname "$0")/.."
while kill -0 "$1" 2>/dev/null; do sleep 10; done
END=$(TZ=Europe/Berlin date -d "$2" +%s); S=$((END - $(date +%s) - 20))
if [ $S -gt 60 ]; then
  nice -n 15 ./engine/nexarch datagen threads=10 nodes=5000 seconds=$S seed=$RANDOM$RANDOM out=data/data-g2d-local.bin net=nets/nexarch-g2.nnue > data/data-g2d-local-2.log 2>&1 < /dev/null
fi
touch data/selfplay-g2d.done
