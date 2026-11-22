#!/bin/bash
set -e
SRC=$(cd "$(dirname "$0")" && pwd)
OUT=${BUILD_DIR:-$HOME/.cache/nexarch-binpack/build}
SHA=aa7f4818b42fdc0230f0f85e54046fb34085f348
mkdir -p "$OUT/lib"
for f in arithmetic.h binpack.h chess.h nodchip.h training_data_entry.h; do
  [ -s "$OUT/lib/$f" ] || curl -sSfL -o "$OUT/lib/$f" "https://raw.githubusercontent.com/official-stockfish/nnue-pytorch/$SHA/data_loader/cpp/lib/$f"
done
${CXX:-g++} -O2 -std=c++20 ${ARCH_FLAGS:--march=native} -I"$OUT/lib" -o "$OUT/binpack2nexarch" "$SRC/binpack2nexarch.cpp"
echo "built $OUT/binpack2nexarch"
