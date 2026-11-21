#!/bin/bash
# Grade Gen 2's self-play (dataset markthegamer108/nexarch-g2-full, 10.4M positions) for training Gen 3.
#
#   bash kaggle/launch-grade-g2.sh lc0-bench       # ~20 min GPU: build Lc0, measure real T4 speed on 100k positions
#   bash kaggle/launch-grade-g2.sh lc0 SAMPLE SECS # Lc0 network-only grading (2x T4), e.g. lc0 2000000 21600
#   bash kaggle/launch-grade-g2.sh cpu SECS        # 4 CPU shards, 33-engine panel, random order until SECS
#
# Every job stops at its time limit and keeps what it finished. Merge everything afterwards with
#   python tools/report_card.py 'kaggle-out/**/*.meta.npz' --out data/graded-g2.bin
set -e
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
    SAMPLE=${2:?sample size}; SECS=${3:?seconds}; ONLY=${4-imbalance,quiet}   # ONLY="" = every category
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
  *) sed -n 2,10p "$0"; exit 1 ;;
esac
