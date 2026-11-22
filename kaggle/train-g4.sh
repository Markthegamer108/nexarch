#!/bin/bash
set -u
OUT=${1:?output dir}
CPUS=${2:-4}
cd "$(dirname "$0")/.."
IN=${G4_INPUT:-/kaggle/input}
MOVETIME=${G4_MOVETIME:-200}
GAMES=${G4_GAMES:-150}
FINAL_GAMES=${G4_FINAL_GAMES:-0}
BUDGET=${G4_BUDGET:-240}
STREAM=${G4_STREAM:-16000000}
EPOCHS=${G4_EPOCHS:-8}
G3=$(find "$IN" -name nexarch-g3.pt -print -quit)
G3N=$(find "$IN" -name nexarch-g3.nnue -print -quit)
[ -n "$G3" ] && [ -n "$G3N" ] || { echo "Gen 3 (nexarch-g3.pt and .nnue) not found in $IN"; exit 1; }
H=$(python -c "import sys, torch; print(torch.load(sys.argv[1], map_location='cpu')['ft_bias'].shape[0])" "$G3") || exit 1
DATA=("$IN/**/graded-g3-full.bin" "$IN/**/t80-*.bin" "$IN/**/lichess-*.bin")
if [ "$H" -lt 2048 ]; then
  BIG=$(( H * 2 > 2048 ? 2048 : H * 2 ))
  python tools/widen.py --from "$G3" --hidden "$BIG" --out "$OUT/start-b.pt" || exit 1
  B=(g4-b "$BIG" "$OUT/start-b.pt" 0.001)
else
  B=(g4-b "$H" "$G3" 0.0005)
fi
echo "Gen 3 has $H neurons; candidates: g4-a $H (from Gen 3), ${B[0]} ${B[1]} (start ${B[2]##*/}, lr ${B[3]})"

train() {
  local name=$1
  if CUDA_VISIBLE_DEVICES=$2 python trainer/train.py --data "${DATA[@]}" --stream "$STREAM" --resume "$4" --hidden "$3" \
       --lr "$5" --epochs "$EPOCHS" --wdl 0.4 --time-budget "$BUDGET" --out "$OUT/$name.nnue" > "$OUT/train-$name.txt" 2>&1 \
     && printf 'setoption name EvalFile value %s\nnnuecheck 100\n' "$OUT/$name.nnue" | ./engine/nexarch | tail -1 \
        | tee -a "$OUT/train-$name.txt" | grep -q 'all match'; then
    echo "candidate $name trained: $(grep -E '^epoch' "$OUT/train-$name.txt" | tail -1)"
  else
    echo "candidate $name FAILED: $(tail -3 "$OUT/train-$name.txt" | tr '\n' ' ')"
    rm -f "$OUT/$name.nnue"
  fi
}
( train g4-a 0 "$H" "$G3" 0.0003 ) &
( train "${B[0]}" 1 "${B[1]}" "${B[2]}" "${B[3]}" ) &
wait

PICK=()
for name in g4-a g4-b; do
  [ -f "$OUT/$name.nnue" ] || continue
  echo "$name vs Gen 3, $GAMES games at $MOVETIME ms per move: $(./engine/nexarch match a="$OUT/$name.nnue" b="$G3N" \
    games="$GAMES" movetime="$MOVETIME" threads="$CPUS" seed=777 | tee "$OUT/gauntlet-$name.txt" | tail -1)"
  PICK+=("$name" "$OUT/gauntlet-$name.txt" "$OUT/$name.nnue")
done
[ ${#PICK[@]} -gt 0 ] || { echo "no candidate survived training"; exit 1; }
python trainer/pick_best.py "$OUT/nexarch-g4.nnue" "${PICK[@]}" | tee "$OUT/pick.txt" || exit 1
if [ "$FINAL_GAMES" -gt 0 ]; then
  ./engine/nexarch match a="$OUT/nexarch-g4.nnue" b="$G3N" games="$FINAL_GAMES" movetime="$MOVETIME" threads="$CPUS" \
    seed=20261124 | tee "$OUT/vs-g3.txt" | tail -1
  ./engine/nexarch match a="$OUT/nexarch-g4.nnue" b=nets/nexarch-g2.nnue games="$FINAL_GAMES" movetime="$MOVETIME" \
    threads="$CPUS" seed=20261125 | tee "$OUT/vs-g2.txt" | tail -1
else
  echo "confirmation matches left for a CPU run"
fi
