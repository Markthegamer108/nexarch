#!/usr/bin/env python3
"""Dual-teacher relabeling: Stockfish + LC0 both score each position, scores are averaged."""
import argparse
import glob
import numpy as np
import subprocess
import sys
import time

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])
assert RECORD.itemsize == 32

PIECES = "PNBRQKpnbrqk"
MATE_SCORE = 20000

def to_fen(rec):
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


class Engine:
    def __init__(self, path, name):
        self.path = path
        self.name = name
        self.proc = subprocess.Popen(
            [path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            text=True, bufsize=1
        )
        self._send("uci")
        self._wait_for("uciok")
        self._send("isready")
        self._wait_for("readyok")

    def _send(self, line):
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()

    def _wait_for(self, token):
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"{self.name} engine died")
            if line.startswith(token):
                return

    def score(self, fen, nodes):
        self._send(f"position fen {fen}")
        self._send(f"go nodes {nodes}")
        score = None
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"{self.name} engine died")
            if line.startswith("bestmove"):
                return score
            if line.startswith("info") and " score " in line:
                parts = line.split()
                i = parts.index("score")
                if parts[i + 1] == "cp":
                    score = int(parts[i + 2])
                elif parts[i + 1] == "mate":
                    m = int(parts[i + 2])
                    score = 20000 if m > 0 else -20000

    def quit(self):
        self._send("quit")
        self.proc.wait()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine-sf", required=True)
    ap.add_argument("--engine-lc0", required=True)
    ap.add_argument("--net-lc0", required=True)
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sf-nodes", type=int, default=20000)
    ap.add_argument("--lc0-nodes", type=int, default=500)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--seconds", type=int, default=28800)
    args = ap.parse_args()

    files = sorted({f for p in args.data for f in glob.glob(p, recursive=True)})
    data = np.concatenate([np.fromfile(f, dtype=RECORD) for f in files])
    data = data[np.random.default_rng(42).permutation(len(data))]
    data = data[args.shard::args.shards]
    print(f"dual-relabeling {len(data):,} positions (shard {args.shard}/{args.shards})", flush=True)

    # Start both engines
    sf = Engine(args.engine_sf, "Stockfish")
    sf._send("setoption name Threads value 1")
    sf._send("setoption name Hash value 16")
    sf._send("isready")
    sf._wait_for("readyok")

    lc0 = Engine(args.engine_lc0, "LC0")
    lc0._send(f"setoption name WeightsFile value {args.net_lc0}")
    lc0._send("setoption name Threads value 1")
    lc0._send("setoption name MaxPrefetch value 32")
    lc0._send("isready")
    lc0._wait_for("readyok")

    out = []
    start = time.time()
    deadline = start + args.seconds

    for i, rec in enumerate(data):
        if time.time() > deadline:
            print("time limit reached; keeping finished work", flush=True)
            break
        fen = to_fen(rec)
        sf_score = sf.score(fen, args.sf_nodes)
        lc0_score = lc0.score(fen, args.lc0_nodes)

        if sf_score is None or lc0_score is None:
            continue

        # Average the two evaluations (both in centipawns, white's perspective)
        avg = int((sf_score + lc0_score) / 2)

        # Convert to white's perspective for storage
        stored = avg if rec["stm"] == 0 else -avg
        stored = np.clip(stored, -32000, 32000)

        new_rec = rec.copy()
        new_rec["score"] = np.int16(stored)
        out.append(new_rec)

        if i % 5000 == 0 and i > 0:
            elapsed = time.time() - start
            print(f"  {i:,} positions ({i/elapsed:.0f} pos/s)", flush=True)

    out = np.array(out, dtype=RECORD)
    out.tofile(args.out)
    print(f"done: {len(out):,} positions -> {args.out}", flush=True)

    sf.quit()
    lc0.quit()


if __name__ == "__main__":
    main()