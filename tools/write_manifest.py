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


def digest(path, limit):
    h = hashlib.blake2b(digest_size=16)
    n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h.update(b)
            n += len(b)
            if limit and n >= limit:
                break
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", required=True)
    ap.add_argument("--month", required=True)
    ap.add_argument("--every", default="1")
    ap.add_argument("--source", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--digest-bytes", type=int, default=64 << 20)
    args = ap.parse_args()
    size = os.path.getsize(args.bin)
    if size == 0 or size % 32:
        raise SystemExit(f"{args.bin}: {size} bytes is not a whole number of 32-byte records")
    records = np.memmap(args.bin, dtype=RECORD, mode="r")
    n = len(records)
    idx = np.linspace(0, n - 1, num=min(n, 200_000), dtype=np.int64)
    sample = records[idx]
    scores = sample["score"].astype(np.int32)
    pcs = np.ascontiguousarray(sample["pcs"]).view(np.uint64).reshape(len(sample), 2)
    keys = np.stack([sample["occ"].astype(np.uint64), pcs[:, 0], pcs[:, 1], sample["stm"].astype(np.uint64)], axis=1)
    uniq = len(np.unique(keys, axis=0))
    man = {
        "file": os.path.basename(args.bin),
        "month": args.month,
        "source": args.source,
        "positions": int(n),
        "bytes": size,
        "sampled": int(len(sample)),
        "sample_sha": digest(args.bin, args.digest_bytes),
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "score": {
            "min": int(scores.min()),
            "max": int(scores.max()),
            "mean": round(float(scores.mean()), 2),
            "mate_like": int((np.abs(scores) >= 10000).sum()),
            "zero": int((scores == 0).sum()),
            "stm_white": int((sample["stm"] == 0).sum()),
            "stm_black": int((sample["stm"] == 1).sum()),
        },
        "result": {str(int(k)): int(v) for k, v in zip(*np.unique(sample["result"], return_counts=True))},
        "spare": {str(int(k)): int(v) for k, v in zip(*np.unique(sample["spare"], return_counts=True))},
        "duplicate_rate": round(1 - uniq / len(sample), 4),
        "halfmove_max": int(sample["halfmove"].max()),
        "fullmove_max": int(sample["fullmove"].max()),
    }
    with open(args.out, "w") as f:
        json.dump(man, f, indent=1, sort_keys=True)
        f.write("\n")
    print(json.dumps({k: man[k] for k in ("file", "positions", "bytes", "duplicate_rate")}))
    if man["score"]["mate_like"] > len(sample) // 2 or man["duplicate_rate"] > 0.5:
        raise SystemExit("manifest check failed")


if __name__ == "__main__":
    main()
