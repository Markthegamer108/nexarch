#!/bin/bash
set -u
OUT=${1:?output dir}
CPUS=${2:-4}
cd "$(dirname "$0")/.."
IN=${G5_INPUT:-/kaggle/input}
PY=${PYTHON:-python}
GAMES=${G5_CONFIRM_GAMES:-400}
GAUNTLET=${G5_CONFIRM_GAUNTLET:-150}
MOVETIME=${G5_CONFIRM_MOVETIME:-200}
NODES=${G5_CONFIRM_NODES:-5000}
mkdir -p "$OUT"
G4N=$(find "$IN" -name nexarch-g4.nnue -print -quit)
G3N=$(find "$IN" -name nexarch-g3.nnue -print -quit)
[ -n "$G4N" ] || { echo "Gen 4 network not found in $IN"; exit 1; }
FINAL=$(find "$IN" -name nexarch-g5.nnue -print -quit)
if [ -z "$FINAL" ]; then
  PICK=()
  for name in g5-a g5-b; do
    N=$(find "$IN" -name "$name.nnue" -print -quit)
    [ -n "$N" ] || continue
    echo "$name vs Gen 4, $GAUNTLET games at $MOVETIME ms per move: $(./engine/nexarch match a="$N" b="$G4N" \
      games="$GAUNTLET" movetime="$MOVETIME" threads="$CPUS" seed=777 | tee "$OUT/gauntlet-$name.txt" | tail -1)"
    PICK+=("$name" "$OUT/gauntlet-$name.txt" "$N")
  done
  [ ${#PICK[@]} -gt 0 ] || { echo "no Gen 5 candidate found in $IN"; exit 1; }
  "$PY" trainer/pick_best.py "$OUT/nexarch-g5.nnue" "${PICK[@]}" | tee "$OUT/pick.txt" || exit 1
  FINAL="$OUT/nexarch-g5.nnue"
else
  cp "$FINAL" "$OUT/nexarch-g5.nnue"
  FINAL="$OUT/nexarch-g5.nnue"
  PT=$(find "$IN" -name nexarch-g5.pt -print -quit)
  [ -n "$PT" ] && cp "$PT" "$OUT/nexarch-g5.pt"
fi
[ -s "$FINAL" ] || { echo "no Gen 5 network to confirm"; exit 1; }

EVAL=$(find "$IN" -name eval-g5-unseen.bin -print -quit)
if [ -n "$EVAL" ] && [ -s "${FINAL%.nnue}.pt" ]; then
  OMP_NUM_THREADS=2 "$PY" tools/eval_net.py --net "${FINAL%.nnue}.pt" --eval "$EVAL" \
    --json "$OUT/unseen.json" | tee "$OUT/unseen.txt"
fi

echo "Gen 5 vs Gen 4, $GAMES games at $MOVETIME ms per move"
./engine/nexarch match a="$FINAL" b="$G4N" games="$GAMES" movetime="$MOVETIME" threads="$CPUS" \
  seed=20261124 | tee "$OUT/vs-g4.txt" | tail -1
echo "Gen 5 vs Gen 4, $GAMES games at $NODES nodes per move"
./engine/nexarch match a="$FINAL" b="$G4N" games="$GAMES" nodes="$NODES" threads="$CPUS" \
  seed=20261125 | tee "$OUT/vs-g4-nodes.txt" | tail -1
if [ -n "$G3N" ] && [ "${G5_CONFIRM_G3:-1}" = 1 ]; then
  echo "Gen 5 vs Gen 3, $GAMES games at $MOVETIME ms per move"
  ./engine/nexarch match a="$FINAL" b="$G3N" games="$GAMES" movetime="$MOVETIME" threads="$CPUS" \
    seed=20261126 | tee "$OUT/vs-g3.txt" | tail -1
fi

if [ "${G5_CONFIRM_PANEL:-1}" = 1 ]; then
  if [ ! -x engines/bin/stockfish ] || ! "$PY" -c 'import chess' 2>/dev/null; then
    bash kaggle/setup-engines.sh || true
  fi
  if [ -x engines/bin/stockfish ] && [ -s openings/uho-8mvs.epd ] && "$PY" -c 'import chess' 2>/dev/null; then
    "$PY" tools/panel_match.py --candidate "$FINAL" --incumbent "$G4N" --panel nets/graders.json \
      --book openings/uho-8mvs.epd --out "$OUT/panel" --pairs "${G5_PANEL_PAIRS:-8}" \
      --movetime "${G5_PANEL_MOVETIME:-100}" --concurrency "${G5_PANEL_WORKERS:-3}" \
      | tee "$OUT/panel.txt"
  else
    echo "panel skipped: engines or opening book missing"
  fi
fi
