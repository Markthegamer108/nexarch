#!/usr/bin/env python3
import re
import shutil
import sys
from pathlib import Path

final, rest = sys.argv[1], sys.argv[2:]
if not rest or len(rest) % 3:
    sys.exit("usage: pick_best.py FINAL.nnue NAME LOG NET [NAME LOG NET ...]")
rows = []
for i in range(0, len(rest), 3):
    name, log, net = rest[i:i + 3]
    text = Path(log).read_text() if Path(log).exists() else ""
    found = re.search(r"match result: A \+(\d+) =(\d+) -(\d+)\s+score [\d.]+%\s+Elo ([+-]?\d+) \(95%: ([+-]?\d+) \.\. ([+-]?\d+)\)", text)
    if not found or not Path(net).exists():
        print(f"{name:12s} no match result, skipped", flush=True)
        continue
    w, d, l = map(int, found.groups()[:3])
    rows.append(((w + 0.5 * d) / (w + d + l), -i, name, net, f"+{w} ={d} -{l}", found.group(4), found.group(5), found.group(6)))
if not rows:
    sys.exit("no candidate has a match result")
for score, _, name, _, wdl, elo, lo, hi in sorted(rows, reverse=True):
    print(f"{name:12s} {wdl:16s} score {100 * score:5.1f}%  Elo {elo:>5s} (95%: {lo} .. {hi})", flush=True)
best = max(rows)
shutil.copy(best[3], final)
pt = Path(best[3]).with_suffix(".pt")
if pt.exists():
    shutil.copy(pt, Path(final).with_suffix(".pt"))
print(f"keeping {best[2]} as {Path(final).name}", flush=True)
