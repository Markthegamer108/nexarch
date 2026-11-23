#!/usr/bin/env python3
import glob
import os
import sys

import torch

ROOT = os.environ.get("G5_INPUT", "/kaggle/input")
PATTERNS = ["graded-g3-full.bin", "t80-*.bin", "lichess-*.bin", "fishnet-*.bin", "selfplay-*.bin"]
STARTS = ["nexarch-g5-h2048-start.pt", "nexarch-g5-h4096-start.pt"]

seen = {}
bad = []
for pat in PATTERNS:
    files = sorted(glob.glob(os.path.join(ROOT, "**", pat), recursive=True))
    n = 0
    for f in files:
        if f in seen:
            continue
        size = os.path.getsize(f)
        if size % 32 or size == 0:
            bad.append(f"{f}: {size} bytes is not a whole number of 32-byte positions")
            continue
        seen[f] = size // 32
        n += size // 32
    print(f"{pat:20s} {len(files):2d} file(s) {n:>13,} positions")

total = sum(seen.values())
print(f"{'total':20s} {len(seen):2d} file(s) {total:>13,} positions ({total * 32 / 1e9:.1f} GB)")
for f in sorted(seen):
    print(f"  {seen[f]:>13,}  {f}")

ok = True
if bad:
    ok = False
    for b in bad:
        print(f"BAD {b}")
if total < 1_000_000_000:
    ok = False
    print(f"BAD only {total:,} positions mounted")
for name in STARTS:
    hit = glob.glob(os.path.join(ROOT, "**", name), recursive=True)
    if not hit:
        ok = False
        print(f"BAD missing {name}")
        continue
    state = torch.load(hit[0], map_location="cpu")
    hidden = int(state["ft_bias"].shape[0])
    print(f"ok {name}: hidden {hidden}, out {tuple(state['out.weight'].shape)}")
    if hidden not in (2048, 4096):
        ok = False
        print(f"BAD {name} has hidden {hidden}")
print("audit", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
