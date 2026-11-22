#!/bin/bash
set -u
OUT=${1:?output dir}
CPUS=${2:-4}
cd "$(dirname "$0")/.."
IN=${G4_INPUT:-/kaggle/input}
G3N=$(find "$IN" -name nexarch-g3.nnue -print -quit)
[ -n "$G3N" ] || { echo "Gen 3 network not found in $IN"; exit 1; }
GAMES=${G4_CONFIRM_GAMES:-400}
GAUNTLET=${G4_CONFIRM_GAUNTLET:-150}
MOVETIME=${G4_CONFIRM_MOVETIME:-200}
G4N=$(find "$IN" -name nexarch-g4.nnue -print -quit)
if [ -z "$G4N" ]; then
  PICK=()
  for name in g4-a g4-b; do
    N=$(find "$IN" -name "$name.nnue" -print -quit)
    [ -n "$N" ] || continue
    echo "$name vs Gen 3, $GAUNTLET games at $MOVETIME ms per move: $(./engine/nexarch match a="$N" b="$G3N" \
      games="$GAUNTLET" movetime="$MOVETIME" threads="$CPUS" seed=777 | tee "$OUT/gauntlet-$name.txt" | tail -1)"
    PICK+=("$name" "$OUT/gauntlet-$name.txt" "$N")
  done
  [ ${#PICK[@]} -gt 0 ] || { echo "no Gen 4 candidate found in $IN"; exit 1; }
  python trainer/pick_best.py "$OUT/nexarch-g4.nnue" "${PICK[@]}" | tee "$OUT/pick.txt" || exit 1
  G4N="$OUT/nexarch-g4.nnue"
fi
./engine/nexarch match a="$G4N" b="$G3N" games="$GAMES" movetime="$MOVETIME" threads="$CPUS" \
  seed=20261124 | tee "$OUT/vs-g3.txt" | tail -1
./engine/nexarch match a="$G4N" b=nets/nexarch-g2.nnue games="$GAMES" movetime="$MOVETIME" threads="$CPUS" \
  seed=20261125 | tee "$OUT/vs-g2.txt" | tail -1
./engine/nexarch match a="$G4N" b="$G3N" games="$GAMES" nodes=5000 threads="$CPUS" \
  seed=20261126 | tee "$OUT/vs-g3-nodes.txt" | tail -1
