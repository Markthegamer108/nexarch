#!/usr/bin/env python3
import argparse
import glob
import json
import os
import sys

import numpy as np

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])
assert RECORD.itemsize == 32


def positions(path):
    size = os.path.getsize(path)
    if size % 32:
        return None
    return size // 32


def sample_keys(path, n=150_000):
    m = np.memmap(path, dtype=RECORD, mode="r")
    if len(m) == 0:
        return np.empty((0, 4), dtype=np.uint64), m
    idx = np.linspace(0, len(m) - 1, num=min(len(m), n), dtype=np.int64)
    s = m[idx]
    pcs = np.ascontiguousarray(s["pcs"]).view(np.uint64).reshape(len(s), 2)
    return np.stack([s["occ"].astype(np.uint64), pcs[:, 0], pcs[:, 1], s["stm"].astype(np.uint64)], axis=1), m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--glob", default="**/*.bin")
    ap.add_argument("--skip", default="none")
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    skip = {s for s in args.skip.split(",") if s and s != "none"}
    files = sorted(glob.glob(os.path.join(args.root, args.glob), recursive=True))
    rows = []
    bad = []
    total = 0
    for f in files:
        if any(s in f for s in skip):
            continue
        n = positions(f)
        if n is None:
            bad.append(f"{f}: size not a multiple of 32")
            continue
        total += n
        keys, m = sample_keys(f)
        s = m[np.linspace(0, len(m) - 1, num=min(len(m), 150_000), dtype=np.int64)]
        scores = s["score"].astype(np.int32)
        dups = 0.0 if len(keys) == 0 else 1 - len(np.unique(keys, axis=0)) / len(keys)
        rows.append({"file": os.path.relpath(f, args.root), "positions": int(n),
                     "bytes": os.path.getsize(f), "dup_rate": round(float(dups), 4),
                     "score_mean": round(float(scores.mean()), 1),
                     "mate_like": int((np.abs(scores) >= 10000).sum()),
                     "spare": int(s["spare"].sum()), "stm_black": int(s["stm"].sum())})
        del m
    rows.sort(key=lambda r: -r["positions"])
    for r in rows:
        print(f"{r['positions']:>12,}  dup {r['dup_rate']:5.1%}  score {r['score_mean']:>7}  mate {r['mate_like']:>6}  {r['file']}")
    for b in bad:
        print("BAD " + b)
    print(f"total {total:,} positions in {len(rows)} files")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump({"total": total, "files": rows, "bad": bad}, fh, indent=1)
    if bad:
        sys.exit(1)


if __name__ == "__main__":
    main()
