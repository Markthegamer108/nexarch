#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import time

import numpy as np
import pyarrow.parquet as pq

MATE_CP = 10000


def best_rows(fen, depth, knodes):
    n = len(fen)
    starts = np.flatnonzero(np.r_[True, fen[1:] != fen[:-1]])
    gid = np.repeat(np.arange(len(starts)), np.diff(np.r_[starts, n]))
    key = (depth.astype(np.int64) << 32) | knodes.astype(np.int64)
    gmax = np.maximum.reduceat(key, starts)
    hit = np.flatnonzero(key == gmax[gid])
    _, first = np.unique(gid[hit], return_index=True)
    return hit[first]


def lines_for(cols, rows):
    out = []
    for i in rows:
        cp, mate = cols["cp"][i], cols["mate"][i]
        if cp is not None:
            score = int(cp)
        elif mate is not None and int(mate) != 0:
            score = MATE_CP if int(mate) > 0 else -MATE_CP
        else:
            continue
        line = cols["line"][i]
        if not line:
            continue
        out.append(f"{cols['fen'][i]}\t{line.split(' ', 1)[0]}\t{score}")
    return ("\n".join(out) + "\n").encode() if out else b""


def convert(path, out, engine, batch):
    pf = pq.ParquetFile(path)
    proc = subprocess.Popen([engine, "packfens", f"out={out}"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    names = ["fen", "line", "depth", "knodes", "cp", "mate"]
    carry = None
    rows = positions = 0
    for b in pf.iter_batches(batch_size=batch, columns=names):
        cols = {k: b.column(k).to_pylist() if k in ("fen", "line", "cp", "mate") else
                b.column(k).fill_null(0).to_numpy(zero_copy_only=False) for k in names}
        if carry is not None:
            cols = {k: (carry[k] + cols[k]) if isinstance(cols[k], list) else np.concatenate([carry[k], cols[k]])
                    for k in names}
        fen = np.array(cols["fen"], dtype=object)
        last = int(np.flatnonzero(np.r_[True, fen[1:] != fen[:-1]])[-1])
        carry = {k: cols[k][last:] for k in names}
        block = {k: cols[k][:last] for k in names}
        if last:
            chosen = best_rows(fen[:last], block["depth"], block["knodes"])
            proc.stdin.write(lines_for(block, chosen))
            positions += len(chosen)
        rows += b.num_rows
    if carry is not None and len(carry["fen"]):
        fen = np.array(carry["fen"], dtype=object)
        chosen = best_rows(fen, carry["depth"], carry["knodes"])
        proc.stdin.write(lines_for(carry, chosen))
        positions += len(chosen)
    proc.stdin.close()
    report = proc.stdout.read().decode().strip()
    if proc.wait() != 0:
        raise SystemExit(f"{path}: nexarch packfens failed")
    return rows, positions, report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parquet", nargs="+")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--engine", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine", "nexarch"))
    ap.add_argument("--batch", type=int, default=2_000_000)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    for path in args.parquet:
        name = os.path.splitext(os.path.basename(path))[0]
        out = os.path.join(args.out_dir, f"lichess-{name}.bin")
        if os.path.exists(out + ".done"):
            print(f"{path}: already converted", flush=True)
            continue
        if os.path.exists(out):
            os.remove(out)
        t = time.time()
        rows, positions, report = convert(path, out, args.engine, args.batch)
        open(out + ".done", "w").write(report + "\n")
        print(f"{path}: {rows:,} rows, {positions:,} positions -> {report} ({time.time() - t:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
