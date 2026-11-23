#!/bin/bash
set -u
cd "$(dirname "$0")/.."
mkdir -p data/aws kaggle-out
THREADS=${SELFPLAY_THREADS:-$(( $(nproc) - 2 ))}
NODES=${SELFPLAY_NODES:-5000}
CHUNK=${SELFPLAY_CHUNK:-1800}
NET=${SELFPLAY_NET:-nets/current.nnue}
echo "$(date -u '+%F %T') aws self-play: $(nproc) vCPU, $THREADS threads, $NODES nodes, ${CHUNK}s chunks, $NET"
while true; do
  N=$(date -u '+%Y%m%d-%H%M%S')
  ./engine/nexarch datagen threads="$THREADS" nodes="$NODES" seconds="$CHUNK" seed="$N$RANDOM" \
    out="data/aws/sp-$N.bin" net="$NET" >> kaggle-out/aws-selfplay.log 2>&1 < /dev/null
  tail -1 kaggle-out/aws-selfplay.log
done
