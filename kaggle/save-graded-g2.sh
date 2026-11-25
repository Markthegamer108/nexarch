#!/bin/bash
set -u
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy

set -euo pipefail
cd "$(dirname "$0")/.."
LOG=kaggle-out/save-graded-g2.log
mkdir -p kaggle-out
. kaggle/lib.sh
say "waiting for data/graded-g2-all.done"
while [ ! -f data/graded-g2-all.done ]; do
  [ -f data/graded-g2-all.failed ] && { say "the merge failed: nothing to upload"; exit 1; }
  sleep 60
done
[ -s data/graded-g2-all.bin ] || { say "data/graded-g2-all.bin missing"; exit 1; }
D=/home/mark/.cache/nexarch-kds/nexarch-graded-g2
mkdir -p "$D"
ln -f data/graded-g2-all.bin "$D/graded-g2-all.bin" 2>/dev/null || cp data/graded-g2-all.bin "$D/graded-g2-all.bin"
printf '{"title":"nexarch-graded-g2","id":"markthegamer108/nexarch-graded-g2","licenses":[{"name":"MIT"}]}\n' > "$D/dataset-metadata.json"
mit_license "$D"
if upload_dataset nexarch-graded-g2 "$D" "graded g2: lc0 + cpu panel + actions panel"; then
  say "saved as markthegamer108/nexarch-graded-g2"
else
  say "UPLOAD FAILED: the merged set is only on this laptop (data/graded-g2-all.bin)"
  exit 1
fi
