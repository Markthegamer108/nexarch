#!/bin/bash
set -u
cd "$(dirname "$0")/.."
mkdir -p data/aws kaggle-out
THREADS=${SELFPLAY_THREADS:-$(nproc)}
NODES=${SELFPLAY_NODES:-5000}
CHUNK=${SELFPLAY_CHUNK:-1800}
NET=${SELFPLAY_NET:-nets/current.nnue}
echo "$(date -u '+%F %T') aws self-play: $(nproc) vCPU, $THREADS threads, $NODES nodes, ${CHUNK}s chunks, $NET"
while true; do
  N=$(date -u '+%Y%m%d-%H%M%S')
  OUT="data/aws/sp-$N.bin"
  rm -f "$OUT.open"
  ./engine/nexarch datagen threads="$THREADS" nodes="$NODES" seconds="$CHUNK" seed="$N$RANDOM" \
    out="$OUT.open" net="$NET" >> kaggle-out/aws-selfplay.log 2>&1 < /dev/null
  if [ -s "$OUT.open" ]; then
    mv -f "$OUT.open" "$OUT"
    tail -1 kaggle-out/aws-selfplay.log
  fi
done
