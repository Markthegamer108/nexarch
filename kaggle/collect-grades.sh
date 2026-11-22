#!/bin/bash
set -u
cd "$(dirname "$0")/.."
RUN=${1:-44898159439}
LOG=kaggle-out/collect-grades.log
mkdir -p kaggle-out
. kaggle/lib.sh
rm -f data/graded-g2-all.failed
say "collecting Actions run $RUN and Kaggle shards nexarch-grade-g2-0..3"
gh_collect "$RUN"
for s in 0 1 2 3; do
  bash kaggle/ensure-kernel.sh nexarch-grade-g2-$s
  say "nexarch-grade-g2-$s: $(head -1 kaggle-out/nexarch-grade-g2-$s.done)"
done
if .venv/bin/python tools/report_card.py \
     'kaggle-out/nexarch-grade-g2-lc0/*.meta.npz' \
     'kaggle-out/nexarch-grade-g2-[0-3]/*.meta.npz' \
     "kaggle-out/gh-$RUN/*/*.meta.npz" \
     --calibrate lc0 --out data/graded-g2-all.bin >> "$LOG" 2>&1; then
  touch data/graded-g2-all.done
  say "merged: $(( $(stat -c %s data/graded-g2-all.bin) / 32 )) positions -> data/graded-g2-all.bin"
else
  touch data/graded-g2-all.failed
  say "MERGE FAILED (see the report_card output above)"
  exit 1
fi
