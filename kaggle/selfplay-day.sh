#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/selfplay-day.log
mkdir -p kaggle-out
. kaggle/lib.sh
START=$(TZ=Europe/Berlin date -d "${1:?start}" +%s) || exit 1
END=$(TZ=Europe/Berlin date -d "${2:?end}" +%s) || exit 1
THREADS=${SELFPLAY_THREADS:-10}

gen3_ok() {
  local s
  [ -s kaggle-out/nexarch-train-g3/nexarch-g3.nnue ] || return 1
  s=$(grep -o 'match result: A [^%]*%' kaggle-out/nexarch-train-g3/vs-g2.txt 2>/dev/null | grep -oE '[0-9.]+%$' | tr -d '%')
  [ -n "$s" ] && awk -v s="$s" 'BEGIN { exit !(s > 50) }'
}

gen4_ok() {
  [ -s nets/nexarch-g4.nnue ] || return 1
  grep -q 'keeping g4' kaggle-out/nexarch-confirm-g4/pick.txt 2>/dev/null
}

say "self-play day: $(TZ=Europe/Berlin date -d "@$START" '+%F %H:%M') to $(TZ=Europe/Berlin date -d "@$END" '+%H:%M'), $THREADS threads"
while [ "$(date +%s)" -lt "$START" ]; do sleep 30; done
while true; do
  LEFT=$((END - $(date +%s) - 20))
  [ $LEFT -gt 120 ] || break
  S=$((LEFT < 3600 ? LEFT : 3600))
  if gen4_ok; then NET=nets/nexarch-g4.nnue; TAG=g4a; elif gen3_ok; then NET=kaggle-out/nexarch-train-g3/nexarch-g3.nnue; TAG=g3a; else NET=nets/nexarch-g2.nnue; TAG=g2e; fi
  say "chunk: ${S}s with $NET -> data/data-$TAG-day-local.bin"
  nice -n 15 ./engine/nexarch datagen threads=$THREADS nodes=5000 seconds=$S seed=$RANDOM$RANDOM \
    out=data/data-$TAG-day-local.bin net=$NET >> data/data-$TAG-day-local.log 2>&1 < /dev/null
  say "chunk done: $(tail -1 data/data-$TAG-day-local.log | cut -c1-120)"
done
for t in g2e g3a g4a; do
  [ -f data/data-$t-day-local.bin ] && say "total $t: $(( $(stat -c %s data/data-$t-day-local.bin) / 32 )) positions"
done
touch data/selfplay-day.done
say "self-play day finished"
