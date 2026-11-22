#!/usr/bin/env python3
import re
import shutil
import sys
from pathlib import Path

log, cand_a, cand_b, final = sys.argv[1:5]
found = re.search(r"match result: A \+(\d+) =(\d+) -(\d+)", Path(log).read_text())
if not found:
    sys.exit(f"no match result in {log}")
wins, draws, losses = map(int, found.groups())
winner = cand_a if wins >= losses else cand_b
shutil.copy(winner, final)
checkpoint = Path(winner).with_suffix(".pt")
if checkpoint.exists():
    shutil.copy(checkpoint, Path(final).with_suffix(".pt"))
print(f"head-to-head A +{wins} ={draws} -{losses}: keeping {Path(winner).name} as {Path(final).name}", flush=True)
