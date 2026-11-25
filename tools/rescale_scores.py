#!/usr/bin/env python3
import argparse
import json
import os
import time

import numpy as np

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--calibration", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "nets",
                                                          "t80-calibration.json"))
    args = ap.parse_args()
    cal = json.load(open(args.calibration))
    xp, fp = np.array(cal["x_cp_stm"], np.float64), np.array(cal["p_stm"], np.float64)
    for f in args.files:
        marker = f + ".rescaled"
        if os.path.exists(marker):
            print(f"{f}: already rescaled, skipped", flush=True)
            continue
        m = np.memmap(f, dtype=RECORD, mode="r+")
        t = time.time()
        for s in range(0, len(m), 10_000_000):
            r = m[s:s + 10_000_000]
            sign = np.where(r["stm"] == 0, 1.0, -1.0)
            p = np.clip(np.interp(r["score"].astype(np.float64) * sign, xp, fp), 0.001, 0.999)
            r["score"] = np.round(400 * np.log(p / (1 - p)) * sign).astype(np.int16)
        m.flush()
        del m
        with open(marker, "w") as out:
            out.write(cal.get("source", args.calibration) + "\n")
        print(f"{f}: {os.path.getsize(f) // 32:,} positions rescaled in {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
