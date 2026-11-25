#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time

import numpy as np

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])
assert RECORD.itemsize == 32


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--positions", type=int, default=250_000)
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--month", default="")
    args = ap.parse_args()
    src = np.memmap(args.bin, dtype=RECORD, mode="r")
    rng = np.random.default_rng(args.seed)
    idx = np.sort(rng.choice(len(src), size=min(args.positions, len(src)), replace=False))
    out = src[idx]
    out.tofile(args.out)
    h = hashlib.blake2b(out.tobytes(), digest_size=16).hexdigest()
    man = {"file": os.path.basename(args.out), "source": os.path.basename(args.bin), "month": args.month,
           "positions": int(len(out)), "bytes": int(out.nbytes), "seed": args.seed, "sha": h,
           "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with open(args.out + ".json", "w") as f:
        json.dump(man, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps(man))


if __name__ == "__main__":
    main()
