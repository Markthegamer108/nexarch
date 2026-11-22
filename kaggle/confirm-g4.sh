#!/bin/bash
set -u
OUT=${1:?output dir}
CPUS=${2:-4}
cd "$(dirname "$0")/.."
IN=${G4_INPUT:-/kaggle/input}
G4N=$(find "$IN" -name nexarch-g4.nnue -print -quit)
G3N=$(find "$IN" -name nexarch-g3.nnue -print -quit)
[ -n "$G4N" ] && [ -n "$G3N" ] || { echo "Gen 4 or Gen 3 network not found in $IN"; exit 1; }
GAMES=${G4_CONFIRM_GAMES:-400}
MOVETIME=${G4_CONFIRM_MOVETIME:-200}
./engine/nexarch match a="$G4N" b="$G3N" games="$GAMES" movetime="$MOVETIME" threads="$CPUS" \
  seed=20261124 | tee "$OUT/vs-g3.txt" | tail -1
./engine/nexarch match a="$G4N" b=nets/nexarch-g2.nnue games="$GAMES" movetime="$MOVETIME" threads="$CPUS" \
  seed=20261125 | tee "$OUT/vs-g2.txt" | tail -1
./engine/nexarch match a="$G4N" b="$G3N" games="$GAMES" nodes=5000 threads="$CPUS" \
  seed=20261126 | tee "$OUT/vs-g3-nodes.txt" | tail -1
