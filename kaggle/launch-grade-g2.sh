#!/bin/bash
set -e
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy

set -euo pipefail
cd "$(dirname "$0")/.."
JOB=".venv/bin/python kaggle/job.py"
DATA="'/kaggle/input/**/${DATAFILE:-nexarch-g2-full.bin}'"
LC0="python3 tools/lc0_batch_grade.py --data $DATA --weights /tmp/nexarch/bt4.pb.gz --lc0-py /tmp/nexarch/lc0/build/release --backend cuda-fp16 --gpus 2 --batch 512"

case "$1" in
  lc0-bench)
    $JOB --name nexarch-lc0-bench --gpu --internet --dataset markthegamer108/nexarch-g2-full \
      --cmd "bash kaggle/lc0-setup.sh" \
      --cmd "$LC0 --out {out}/lc0-bench --sample 100000 --seconds 600" --push ;;
  lc0)
    SAMPLE=${2:?sample size}; SECS=${3:?seconds}; ONLY=${4-imbalance,quiet}
    NAME=${NAME:-nexarch-grade-g2-lc0}; DS=${DS:-markthegamer108/nexarch-g2-full}
    $JOB --name $NAME --gpu --internet --dataset $DS \
      --cmd "bash kaggle/lc0-setup.sh" \
      --cmd "$LC0 --out {out}/grade-g2-lc0 --sample $SAMPLE --seconds $SECS --only '$ONLY'" \
      --cmd "python3 tools/report_card.py {out}/grade-g2-lc0.meta.npz" --push ;;
  cpu)
    SECS=${2:-39600}
    for s in 0 1 2 3; do
      $JOB --name nexarch-grade-g2-$s --internet --dataset markthegamer108/nexarch-engines --dataset markthegamer108/nexarch-g2-full \
        --cmd "bash kaggle/setup-engines.sh" \
        --cmd "python3 tools/grade.py --config nets/graders.json --data $DATA --out {out}/grade-g2-$s.bin --workers {cpus} --shard $s --shards 4 --seconds $SECS" \
        --cmd "python3 tools/report_card.py {out}/grade-g2-$s.bin.meta.npz" --push
    done ;;
  cpu2)
    SECS=${2:-39600}; DS=${DS:-markthegamer108/nexarch-g2d}; DATAFILE=${DATAFILE:-nexarch-g2d.bin}
    PREFIX=${PREFIX:-nexarch-grade-g2d}; SHARDS=${SHARDS:-0 1 2 3}
    for s in $SHARDS; do
      $JOB --name $PREFIX-$s --internet --dataset markthegamer108/nexarch-engines --dataset $DS \
        --cmd "bash kaggle/setup-engines.sh" \
        --cmd "python3 tools/grade.py --config nets/graders.json --data '/kaggle/input/**/$DATAFILE' --out {out}/grade-g2d-$s.bin --workers {cpus} --shard $s --shards 4 --seconds $SECS" \
        --cmd "python3 tools/report_card.py {out}/grade-g2d-$s.bin.meta.npz" --push
      sleep 5
    done ;;
  *) sed -n 2,10p "$0"; exit 1 ;;
esac
