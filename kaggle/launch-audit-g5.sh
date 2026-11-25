#!/bin/bash
set -u
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy

set -euo pipefail
cd "$(dirname "$0")/.."
LOG=kaggle-out/launch-audit-g5.log
mkdir -p kaggle-out
. kaggle/lib.sh
say "Auditing the Gen 5 input set on Kaggle"
SETS=(
  --dataset markthegamer108/nexarch-graded-g3
  --dataset markthegamer108/nexarch-t80-2024-01-jan
  --dataset markthegamer108/nexarch-t80-2024-02-feb
  --dataset markthegamer108/nexarch-t80-2024-03-mar
  --dataset markthegamer108/nexarch-lichess-evals
  --dataset markthegamer108/nexarch-fishnet-2025-01
  --dataset markthegamer108/nexarch-selfplay-2026-11-22
  --dataset markthegamer108/nexarch-g5-starts
)
push_kernel nexarch-audit-g5 5 .venv/bin/python kaggle/job.py --name nexarch-audit-g5 --internet \
  "${SETS[@]}" --cmd "python kaggle/audit-g5.py" --push || { say "could not launch the audit"; exit 1; }
JOB=nexarch-audit-g5
for i in $(seq 1 240); do
  ST=$(kernel_state "$JOB")
  case "$ST" in COMPLETE|ERROR|CANCELED|FAILED) break ;; esac
  [ $((i % 10)) -eq 1 ] && say "$JOB: ${ST:-no answer}"
  sleep 30
done
say "$JOB finished: ${ST:-unknown}"
rm -rf "kaggle-out/$JOB"
.venv/bin/kaggle kernels output "markthegamer108/$JOB" -p "kaggle-out/$JOB" >> "$LOG" 2>&1
grep -h 'positions\|audit \|BAD ' "kaggle-out/$JOB/run.log" 2>/dev/null | tail -20 >> "$LOG"
tail -20 "$LOG"
