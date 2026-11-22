#!/bin/bash
set -e
T=$(find /kaggle/input -type f -name 'nexarch-engines.tar.gz' -print -quit)
if [ -n "$T" ]; then
  tar -xzf "$T"
else
  S=$(find /kaggle/input -path '*engines/bin/stockfish' -print -quit)
  if [ -n "$S" ]; then
    SRC_DIR=$(dirname "$(dirname "$S")")
    if [ "$SRC_DIR" != "$(pwd)/engines" ]; then
      cp -r "$SRC_DIR" engines
    else
      echo "engines already in place"
    fi
  fi
fi
if [ -d engines ]; then
  chmod -R u+x engines/bin engines/real engines/lib 2>/dev/null || true
  echo "engines: $(ls engines/bin 2>/dev/null | wc -l) files in engines/bin"
fi
pip install -q chess 2>&1 | grep -v -i 'notice\|warning' || true
