#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import time
import urllib.request

MATE_CP = 10000
BASE = "https://huggingface.co/datasets/Lichess/fishnet-evals/resolve/main/"


def token():
    for p in (os.path.expanduser("~/.cache/huggingface/token"),):
        if os.path.exists(p):
            return open(p).read().strip()
    return os.environ.get("HF_TOKEN", "")


def pull(name, dest, start, end):
    url = BASE + name
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token()} if token() else {})
    req.add_header("Range", f"bytes={start}-{end}")
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def convert(parquet, out, engine, batch, every, limit):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(parquet)
    proc = subprocess.Popen([engine, "packfens", f"out={out}"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    rows = emitted = 0
    t = time.time()
    stop = False
    for b in pf.iter_batches(batch_size=batch, columns=["fen", "cp", "mate", "move"]):
        fen = b.column("fen").to_pylist()
        cp = b.column("cp").to_pylist()
        mate = b.column("mate").to_pylist()
        move = b.column("move").to_pylist()
        lines = []
        for i in range(len(fen)):
            rows += 1
            if every > 1 and rows % every:
                continue
            m = move[i]
            if not m or len(m) < 4:
                continue
            c, mt = cp[i], mate[i]
            if c is not None:
                score = int(c)
            elif mt is not None and int(mt) != 0:
                score = MATE_CP if int(mt) > 0 else -MATE_CP
            else:
                continue
            lines.append(f"{fen[i]}\t{m}\t{score}")
            emitted += 1
            if limit and emitted >= limit:
                stop = True
                break
        if lines:
            proc.stdin.write(("\n".join(lines) + "\n").encode())
        if rows % (batch * 20) < batch:
            print(f"{parquet}: {rows:,} rows, {emitted:,} written, {rows / max(time.time() - t, 1e-9):,.0f} rows/s", flush=True)
        if stop:
            break
    proc.stdin.close()
    report = proc.stdout.read().decode().strip()
    if proc.wait() != 0:
        raise SystemExit(f"{parquet}: nexarch packfens failed")
    return rows, emitted, report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("parquet", nargs="+")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--engine", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine", "nexarch"))
    ap.add_argument("--batch", type=int, default=500_000)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    for path in args.parquet:
        name = os.path.splitext(os.path.basename(path))[0]
        out = os.path.join(args.out_dir, f"fishnet-{name}.bin")
        if os.path.exists(out + ".done"):
            print(f"{path}: already converted", flush=True)
            continue
        if os.path.exists(out):
            os.remove(out)
        t = time.time()
        rows, emitted, report = convert(path, out, args.engine, args.batch, args.every, args.limit)
        open(out + ".done", "w").write(report + "\n")
        print(f"{path}: {rows:,} rows, {emitted:,} positions -> {report} ({time.time() - t:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
