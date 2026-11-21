#!/usr/bin/env python3
"""Re-score self-play positions with a teacher engine (Stockfish 19 at full strength).

Reads datagen .bin files, asks the teacher for a fixed-node search of every position, and writes the same
records with the teacher's score (White's view). Game results are kept, so training can still blend in outcomes.

  python tools/relabel.py --engine ./sf --data 'in/**/*.bin' --out relabeled.bin --nodes 20000 --workers 4
"""
import argparse
import glob
import multiprocessing as mp
import subprocess
import sys
import time

import numpy as np

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])
PIECES = "PNBRQKpnbrqk"
MATE_SCORE = 20000

_engine = None
_nodes = 0


def to_fen(rec):
    """Rebuild a FEN from a packed record (castling rights inferred from king/rook placement)."""
    board = ["."] * 64
    occ, k = int(rec["occ"]), 0
    for sq in range(64):
        if occ >> sq & 1:
            byte = int(rec["pcs"][k // 2])
            board[sq] = PIECES[(byte >> (4 * (k & 1))) & 15]
            k += 1
    rows = []
    for rank in range(7, -1, -1):
        row, empty = "", 0
        for file in range(8):
            p = board[rank * 8 + file]
            if p == ".":
                empty += 1
            else:
                row += (str(empty) if empty else "") + p
                empty = 0
        rows.append(row + (str(empty) if empty else ""))
    rights = ""
    if board[4] == "K":
        rights += ("K" if board[7] == "R" else "") + ("Q" if board[0] == "R" else "")
    if board[60] == "k":
        rights += ("k" if board[63] == "r" else "") + ("q" if board[56] == "r" else "")
    stm = "b" if rec["stm"] else "w"
    return f"{'/'.join(rows)} {stm} {rights or '-'} - {int(rec['halfmove'])} {max(1, int(rec['fullmove']))}"


def start_engine(path, nodes):
    global _engine, _nodes
    _nodes = nodes
    _engine = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    send("uci")
    wait_for("uciok")
    send("setoption name Threads value 1")
    send("setoption name Hash value 16")
    send("isready")
    wait_for("readyok")


def send(line):
    _engine.stdin.write(line + "\n")
    _engine.stdin.flush()


def wait_for(token):
    while True:
        line = _engine.stdout.readline()
        if not line:
            raise RuntimeError("teacher engine exited")
        if line.startswith(token):
            return line


def score_fen(fen):
    """Teacher's score in centipawns from the side to move's view."""
    send(f"position fen {fen}")
    send(f"go nodes {_nodes}")
    score = None
    while True:
        line = _engine.stdout.readline()
        if not line:
            raise RuntimeError("teacher engine exited")
        if line.startswith("bestmove"):
            return score
        if line.startswith("info") and " score " in line and "bound" not in line:
            parts = line.split()
            i = parts.index("score")
            if parts[i + 1] == "cp":
                score = int(parts[i + 2])
            elif parts[i + 1] == "mate":
                m = int(parts[i + 2])
                score = MATE_SCORE if m > 0 else -MATE_SCORE


def relabel_chunk(chunk):
    out = chunk.copy()
    keep = np.ones(len(chunk), bool)
    for i, rec in enumerate(chunk):
        s = score_fen(to_fen(rec))
        if s is None:
            keep[i] = False
            continue
        out["score"][i] = np.clip(s if rec["stm"] == 0 else -s, -32000, 32000)
    return out[keep]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nodes", type=int, default=20000)
    ap.add_argument("--workers", type=int, default=mp.cpu_count())
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--seconds", type=int, default=0, help="stop (keeping finished work) after this long")
    ap.add_argument("--limit", type=int, default=0, help="only relabel this many positions")
    args = ap.parse_args()

    files = sorted({f for p in args.data for f in glob.glob(p, recursive=True)})
    data = np.concatenate([np.fromfile(f, dtype=RECORD) for f in files])
    data = data[np.random.default_rng(42).permutation(len(data))]  # mix games so partial runs stay diverse
    data = data[args.shard::args.shards]
    if args.limit:
        data = data[:args.limit]
    print(f"relabeling {len(data):,} positions from {len(files)} file(s) with {args.workers} teacher processes, "
          f"{args.nodes} nodes each", flush=True)

    chunks = [data[i:i + 1000] for i in range(0, len(data), 1000)]
    start, done = time.time(), 0
    with open(args.out, "wb") as f, mp.Pool(args.workers, initializer=start_engine,
                                            initargs=(args.engine, args.nodes)) as pool:
        for out in pool.imap(relabel_chunk, chunks):
            out.tofile(f)
            done += len(out)
            elapsed = time.time() - start
            if done % 20000 < 1000:
                print(f"relabeled {done:,} / {len(data):,}  ({done / elapsed:.0f} pos/s, {elapsed / 60:.0f} min)", flush=True)
            if args.seconds and elapsed > args.seconds:
                print("time limit reached; keeping finished work", flush=True)
                pool.terminate()
                break
    print(f"done: {done:,} positions -> {args.out}", flush=True)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
