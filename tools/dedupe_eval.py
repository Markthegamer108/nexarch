#!/usr/bin/env python3
import argparse
import os

import numpy as np

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])
assert RECORD.itemsize == 32


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--want", type=int, default=250_000)
    args = ap.parse_args()
    rec = np.memmap(args.src, dtype=RECORD, mode="r")
    pcs = np.ascontiguousarray(rec["pcs"]).view(np.uint64).reshape(len(rec), 2)
    key = np.stack([rec["occ"].astype(np.uint64), pcs[:, 0], pcs[:, 1], rec["stm"].astype(np.uint64)], axis=1)
    _, first = np.unique(key, axis=0, return_index=True)
    keep = np.sort(first)
    if len(keep) > args.want:
        keep = keep[: args.want]
    out = rec[keep]
    out.tofile(args.out)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    print(f"{args.src}: {len(rec):,} positions, {len(keep):,} unique kept -> {args.out}")


if __name__ == "__main__":
    main()
