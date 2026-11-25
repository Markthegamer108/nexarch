#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p kaggle-out
NAME=nexarch-holdout-g5
LOG=kaggle-out/launch-$NAME.log
exec 9>"kaggle-out/.$NAME.launch.lock"
flock -n 9 || exit 0
. kaggle/lib.sh
DIR="kaggle/jobs/$NAME"
.venv/bin/python kaggle/job.py --name "$NAME" --dir "$DIR" \
  --dataset markthegamer108/nexarch-graded-g3 \
  --dataset markthegamer108/nexarch-t80-2024-01-jan \
  --dataset markthegamer108/nexarch-t80-2024-02-feb \
  --dataset markthegamer108/nexarch-t80-2024-03-mar \
  --dataset markthegamer108/nexarch-lichess-evals \
  --dataset markthegamer108/nexarch-fishnet-2025-01 \
  --dataset markthegamer108/nexarch-selfplay-2026-11-22 \
  --dataset markthegamer108/nexarch-evalset-2024-05 \
  --cmd 'set -e; f=$(find /kaggle/input -type f -name eval-2024-05.bin -print -quit); test -n "$f"; OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python tools/audit_holdout.py --input /kaggle/input --eval "$f" --out {out} --positions 2042685943 --files 26 --eval-sha256 80e4da83447e207e0b014b6e245b07dcf51b6b00fa82e68938425d9a73b12a3c' >> "$LOG" 2>&1
.venv/bin/python -m py_compile "$DIR/$NAME.py"
if [[ ${G5_HOLDOUT_DRY_RUN:-0} = 1 ]]; then
  exit 0
fi
R=$(timeout 45 "$KAGGLE" kernels status "markthegamer108/$NAME" 2>&1) || {
  case "$R" in
    *'404 Client Error: Not Found'*) ;;
    *"Cannot access kernel 'markthegamer108/$NAME'"*)
      L=$(timeout 35 "$KAGGLE" kernels list --mine --search "$NAME" --format json 2>&1) || {
        [[ "$L" = 'Not found' ]] || { say "$L"; exit 1; }
      }
      case "$L" in 'Not found'|'[]') ;; *) say "$NAME: existing or ambiguous notebook; refusing duplicate"; exit 1 ;; esac ;;
    *) say "$NAME: cannot confirm launch state: $R"; exit 1 ;;
  esac
}
if [[ "$R" = *KernelWorkerStatus.* ]]; then
  say "$NAME: $R; not submitting a duplicate"
  exit 0
fi
[[ ! -e "kaggle-out/.$NAME.submission" ]] || { say "previous submission exists, not resubmitting"; exit 1; }
date -u +%FT%TZ > "kaggle-out/.$NAME.submission"
R=$(timeout 90 "$KAGGLE" kernels push -p "$DIR" -t 14400 2>&1) || { say "$R"; exit 1; }
say "$R"
[[ "$R" = *'successfully pushed'* ]]
