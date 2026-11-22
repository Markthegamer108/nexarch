#!/bin/bash
set -u
OUT=${1:?output dir}
CPUS=${2:-4}
cd "$(dirname "$0")/.."
IN=${G3_INPUT:-/kaggle/input}
DATA=${G3_DATA:-$IN/**/graded-g3-full.bin}
MOVETIME=${G3_MOVETIME:-200}
GAMES=${G3_GAMES:-300}
FINAL_GAMES=${G3_FINAL_GAMES:-400}
NODES_GAMES=${G3_NODES_GAMES:-400}
G2=$(find "$IN" -name nexarch-g2.pt -print -quit)
[ -n "$G2" ] || { echo "nexarch-g2.pt not found in $IN"; exit 1; }
for h in 512 1024 2048; do
  python tools/widen.py --from "$G2" --hidden $h --out "$OUT/start-h$h.pt" || exit 1
done

train() {
  local name=$1
  if CUDA_VISIBLE_DEVICES=$2 python trainer/train.py --data "$DATA" --resume "$4" --hidden "$3" --lr "$5" --epochs "$6" \
       --wdl "$7" --time-budget "$8" --out "$OUT/$name.nnue" > "$OUT/train-$name.txt" 2>&1 \
     && printf 'setoption name EvalFile value %s\nnnuecheck 100\n' "$OUT/$name.nnue" | ./engine/nexarch | tail -1 \
        | tee -a "$OUT/train-$name.txt" | grep -q 'all match'; then
    echo "candidate $name trained: $(grep -E '^epoch' "$OUT/train-$name.txt" | tail -1)"
  else
    echo "candidate $name FAILED: $(tail -3 "$OUT/train-$name.txt" | tr '\n' ' ')"
    rm -f "$OUT/$name.nnue"
  fi
}

( train g3-h2048 0 2048 "$OUT/start-h2048.pt" 0.001 16 0.4 "${G3_BUDGET_2048:-150}" ) &
( train g3-h128 1 128 "$G2" 0.0003 12 0.5 "${G3_BUDGET_128:-20}"
  train g3-h512 1 512 "$OUT/start-h512.pt" 0.001 16 0.4 "${G3_BUDGET_512:-50}"
  train g3-h1024 1 1024 "$OUT/start-h1024.pt" 0.001 16 0.4 "${G3_BUDGET_1024:-80}" ) &
wait

PICK=()
for name in g3-h128 g3-h512 g3-h1024 g3-h2048; do
  [ -f "$OUT/$name.nnue" ] || continue
  echo "$name vs Gen 2, $GAMES games at $MOVETIME ms per move: $(./engine/nexarch match a="$OUT/$name.nnue" \
    b=nets/nexarch-g2.nnue games="$GAMES" movetime="$MOVETIME" threads="$CPUS" seed=777 | tee "$OUT/gauntlet-$name.txt" | tail -1)"
  PICK+=("$name" "$OUT/gauntlet-$name.txt" "$OUT/$name.nnue")
done
[ ${#PICK[@]} -gt 0 ] || { echo "no candidate survived training"; exit 1; }
python trainer/pick_best.py "$OUT/nexarch-g3.nnue" "${PICK[@]}" | tee "$OUT/pick.txt" || exit 1

./engine/nexarch match a="$OUT/nexarch-g3.nnue" b=nets/nexarch-g2.nnue games="$FINAL_GAMES" movetime="$MOVETIME" \
  threads="$CPUS" seed=20261122 | tee "$OUT/vs-g2.txt" | tail -1
./engine/nexarch match a="$OUT/nexarch-g3.nnue" b=nets/nexarch-g2.nnue games="$NODES_GAMES" nodes=5000 \
  threads="$CPUS" seed=20261123 | tee "$OUT/vs-g2-nodes.txt" | tail -1
