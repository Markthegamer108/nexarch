#!/usr/bin/env python3
import argparse
import os
import time
import numpy as np

RECORD = np.dtype([("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
                   ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1")])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("bin")
    ap.add_argument("--top", type=int, default=8)
    args = ap.parse_args()
    m = np.memmap(args.bin, dtype=RECORD, mode="r")
    n = len(m)
    idx = np.linspace(0, n - 1, num=min(n, 400_000), dtype=np.int64)
    s = m[idx]
    pcs = np.ascontiguousarray(s["pcs"]).view(np.uint64).reshape(len(s), 2)
    key = np.stack([s["occ"].astype(np.uint64), pcs[:, 0], pcs[:, 1], s["stm"].astype(np.uint64)], axis=1)
    order = np.lexsort(key.T[::-1])
    key, s = key[order], s[order]
    eq = np.all(key[1:] == key[:-1], axis=1)
    starts = np.flatnonzero(np.r_[True, ~eq])
    ends = np.r_[starts[1:], len(key)]
    groups = [(starts[i], ends[i]) for i in range(len(starts)) if ends[i] - starts[i] > 1]
    print(f"sample {len(key):,} positions, {len(groups):,} duplicate groups")
    rows = []
    for a, b in groups:
        sc = s["score"][a:b].astype(np.int32)
        spread = int(sc.max() - sc.min())
        rows.append((spread, b - a, a, b, sc))
    rows.sort(reverse=True, key=lambda r: r[0])
    print("worst score disagreements (all in the same position):")
    for spread, copies, a, b, sc in rows[: args.top]:
        u = np.unique(sc)
        stm = int(s["stm"][a])
        hm = int(s["halfmove"][a])
        fm = int(s["fullmove"][a])
        print(f"  spread {spread:5d} cp over {copies:4d} copies  stm={'w' if stm == 0 else 'b'}  "
              f"halfmove {hm} fullmove {fm}  scores {u[:6].tolist()}{'...' if len(u) > 6 else ''}")
    mate = int((np.abs(s["score"]).astype(np.int32) >= 10000).sum())
    print(f"mate-range records in sample: {mate} ({100 * mate / len(s):.2f}%)")
    big = int((np.abs(s["score"].astype(np.int32)) >= 3000).sum())
    print(f"|score| >= 3000: {big} ({100 * big / len(s):.2f}%)")
    if len(rows):
        spreads = np.array([r[0] for r in rows])
        print(f"score spread across duplicate groups: median {np.median(spreads):.0f}, p90 {np.percentile(spreads, 90):.0f}, max {spreads.max()}")


if __name__ == "__main__":
    main()
