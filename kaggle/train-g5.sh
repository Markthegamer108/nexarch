#!/bin/bash
set -u
OUT=${1:?output dir}
CPUS=${2:-4}
cd "$(dirname "$0")/.."
IN=${G5_INPUT:-/kaggle/input}
BUDGET=${G5_BUDGET:-600}
EPOCHS=${G5_EPOCHS:-8}
ONLY=${G5_ONLY:-g5-a}
PY=${PYTHON:-python}
DATA=("$IN/**/graded-g3-full.bin" "$IN/**/t80-*.bin" "$IN/**/lichess-*.bin" "$IN/**/fishnet-*.bin" "$IN/**/selfplay-*.bin")
[ -n "${G5_EXTRA_DATA:-}" ] && DATA+=("$G5_EXTRA_DATA")
S2048=${G5_RESUME:-$(find "$IN" -name nexarch-g5-h2048-start.pt -print -quit)}
S4096=$(find "$IN" -name nexarch-g5-h4096-start.pt -print -quit)
[ -n "$S2048" ] && [ -n "$S4096" ] || { echo "start checkpoints nexarch-g5-h2048-start.pt / nexarch-g5-h4096-start.pt not found in $IN"; exit 1; }
mkdir -p "$OUT"
echo "Gen 5: budget ${BUDGET} min, $EPOCHS epochs, data under $IN"

train() {
  local name=$1 gpu=$2 hidden=$3 start=$4 lr=$5 batch=$6
  if CUDA_VISIBLE_DEVICES=$gpu "$PY" trainer/train.py --data "${DATA[@]}" --resume "$start" --hidden "$hidden" \
       --batch "$batch" --lr "$lr" --epochs "$EPOCHS" --wdl 0.4 --time-budget "$BUDGET" \
       --stream "${G5_STREAM:-16000000}" --out "$OUT/$name.nnue" \
       > "$OUT/train-$name.txt" 2>&1 \
     && printf 'setoption name EvalFile value %s\nnnuecheck 100\n' "$OUT/$name.nnue" | ./engine/nexarch | tail -1 \
        | tee -a "$OUT/train-$name.txt" | grep -q 'all match'; then
    echo "candidate $name trained: $(grep -E '^epoch' "$OUT/train-$name.txt" | tail -1)"
  else
    echo "candidate $name FAILED: $(tail -3 "$OUT/train-$name.txt" | tr '\n' ' ')"
    rm -f "$OUT/$name.nnue"
  fi
}

if [ "${G5_SEQ:-0}" = 1 ]; then
  [ "$ONLY" = g5-b ] || train g5-a 0 2048 "$S2048" "${G5_A_LR:-0.0006}" 8192
  [ "$ONLY" = g5-a ] || train g5-b 0 4096 "$S4096" "${G5_B_LR:-0.0004}" 4096
elif [ "$ONLY" = g5-b ]; then
  train g5-b 0 4096 "$S4096" "${G5_B_LR:-0.0004}" 4096
elif [ "$ONLY" = g5-a ]; then
  train g5-a 0 2048 "$S2048" "${G5_A_LR:-0.0006}" 8192
else
  ( train g5-a 0 2048 "$S2048" "${G5_A_LR:-0.0006}" 8192 ) &
  ( train g5-b 1 4096 "$S4096" "${G5_B_LR:-0.0004}" 4096 ) &
  wait
fi
[ -f "$OUT/g5-a.nnue" ] || [ -f "$OUT/g5-b.nnue" ] || { echo "no candidate survived training"; exit 1; }
echo "candidates: $(ls "$OUT"/g5-[ab].nnue 2>/dev/null | xargs -r -n1 basename | tr '\n' ' ')"
