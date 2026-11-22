#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/finish-g3.log
mkdir -p kaggle-out
. kaggle/lib.sh
fail() { say "FAILED: $*"; touch data/graded-g3-full.failed; exit 1; }
rm -f data/graded-g3-full.failed

say "waiting for the old 10.4M merged set"
while [ ! -f data/graded-g2-all.done ]; do
  [ -f data/graded-g2-all.failed ] && fail "the old set's merge failed (kaggle-out/collect-grades.log)"
  sleep 60
done
say "old set: $(( $(stat -c %s data/graded-g2-all.bin) / 32 )) positions"

say "waiting for the g2d launches"
while [ ! -f kaggle-out/g2d-launch.done ] && pgrep -f 'kaggle/after-selfplay\.sh' >/dev/null; do sleep 60; done

RUN=$(cat kaggle-out/g2d-actions-run.txt 2>/dev/null)
if [[ "$RUN" =~ ^[0-9]+$ ]]; then gh_collect "$RUN"; else say "no g2d Actions run recorded: skipping it"; RUN=none; fi

say "waiting for local grading"
while [ ! -f data/grade-local-g2d.done ] && pgrep -f 'grade-local-cpu\.bin' >/dev/null; do sleep 60; done
if [ ! -f data/grade-local-cpu.bin.meta.npz ] && ls data/grade-local-cpu.bin.part*.rec >/dev/null 2>&1; then
  say "local grading output missing: rebuilding it from the part files"
  .venv/bin/python tools/grade.py --config nets/graders.json --data data/data-g2d-local.bin --out data/grade-local-cpu.bin \
    --finalize-only >> "$LOG" 2>&1 || say "local rebuild failed: continuing without it"
fi

for name in $(cat kaggle-out/g2d-kernels.txt 2>/dev/null); do
  say "collecting $name"
  bash kaggle/ensure-kernel.sh "$name"
  say "$name: $(head -1 "kaggle-out/$name.done")"
done

FILES=()
for p in 'kaggle-out/nexarch-grade-g2d-lc0/*.meta.npz' 'kaggle-out/nexarch-grade-g2d-[0-3]/*.meta.npz' "kaggle-out/gh-$RUN/*/*.meta.npz" \
         'data/grade-local-cpu.bin.meta.npz'; do
  for f in $p; do [ -f "$f" ] && FILES+=("$f"); done
done
[ ${#FILES[@]} -gt 0 ] || fail "no g2d grading output at all"
say "merging ${#FILES[@]} g2d grading files"
.venv/bin/python tools/report_card.py "${FILES[@]}" --calibrate lc0 --out data/graded-g2d-all.bin >> "$LOG" 2>&1 || fail "g2d merge (report_card)"
touch data/graded-g2d-all.done
say "g2d set: $(( $(stat -c %s data/graded-g2d-all.bin) / 32 )) positions"

.venv/bin/python - >> "$LOG" 2>&1 <<'PY' || fail "combining old + new"
import sys
import numpy as np
sys.path.insert(0, "tools")
from report_card import RECORD

old = np.fromfile("data/graded-g2-all.bin", dtype=RECORD)
new = np.fromfile("data/graded-g2d-all.bin", dtype=RECORD)
print(f"old {len(old):,} + new {len(new):,} positions", flush=True)
allr = np.concatenate([old, new])
del old, new
_, first = np.unique(allr.view(np.dtype((np.void, RECORD.itemsize))), return_index=True)
out = allr[np.sort(first)]
out.tofile("data/graded-g3-full.bin")
print(f"combined: {len(allr):,} -> {len(out):,} unique -> data/graded-g3-full.bin", flush=True)
PY
touch data/graded-g3-full.done
say "combined set ready: $(( $(stat -c %s data/graded-g3-full.bin) / 32 )) positions"
