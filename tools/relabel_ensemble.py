#!/usr/bin/env python3
import argparse
import glob
import json
import math
import multiprocessing as mp
import os
import select
import subprocess
import sys
import time

import numpy as np

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])
assert RECORD.itemsize == 32
PIECES = "PNBRQKpnbrqk"
SCALE = 400.0
MATE_RAW = 30000
MISSING = -32768
P_MAX = 0.999


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
    TIMEOUT = 120

    def __init__(self, cfg, worker, gpus):
        self.cfg = cfg
        self.name = cfg["name"]
        self.nodes = cfg.get("nodes")
        self.path = os.path.abspath(cfg["path"])
        d = os.path.dirname(self.path)
        self.init = [c.replace("{worker}", str(worker)).replace("{gpu}", str(worker % max(1, gpus))).replace("{dir}", d)
                     for c in cfg.get("init", [])]
        self.proc = None
        self.start()

    def start(self):
        self.proc = subprocess.Popen([self.path], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=0)
        self.buf = b""
        self.send("uci")
        self.wait_for("uciok")
        for cmd in self.init:
            self.send(cmd)
        self.send("isready")
        self.wait_for("readyok")

    def send(self, line):
        try:
            self.proc.stdin.write((line + "\n").encode())
        except (BrokenPipeError, OSError):
            raise RuntimeError(f"{self.name} exited")

    def readline(self):
        fd = self.proc.stdout.fileno()
        while b"\n" not in self.buf:
            if not select.select([fd], [], [], self.TIMEOUT)[0]:
                raise RuntimeError(f"{self.name} hung (no output for {self.TIMEOUT}s)")
            chunk = os.read(fd, 65536)
            if not chunk:
                raise RuntimeError(f"{self.name} exited")
            self.buf += chunk
        line, self.buf = self.buf.split(b"\n", 1)
        return line.decode(errors="replace").strip() + "\n"

    def wait_for(self, token):
        while True:
            if self.readline().startswith(token):
                return

    def score(self, fen, nodes):
        self.send(f"position fen {fen}")
        self.send(f"go nodes {self.nodes or nodes}")
        score = None
        while True:
            line = self.readline()
            if line.startswith("bestmove"):
                return score
            if line.startswith("info") and " score " in line and " lowerbound" not in line and " upperbound" not in line:
                parts = line.split()
                i = parts.index("score")
                if parts[i + 1] == "cp":
                    score = max(-MATE_RAW + 1, min(MATE_RAW - 1, int(parts[i + 2])))
                elif parts[i + 1] == "mate":
                    score = MATE_RAW if int(parts[i + 2]) > 0 else -MATE_RAW

    def close(self):
        try:
            self.send("quit")
            self.proc.wait(timeout=5)
        except Exception:
            self.proc.kill()


def win_prob(raw):
    if raw >= MATE_RAW:
        return P_MAX
    if raw <= -MATE_RAW:
        return 1 - P_MAX
    return 1.0 / (1.0 + math.exp(-raw / SCALE))


def worker_main(w, args, configs, data_path, idx_path, out_prefix, deadline, counter):
    data = np.load(data_path, mmap_mode="r")
    idx = np.load(idx_path, mmap_mode="r")[w::args.workers]
    engines = []
    for cfg in configs:
        engines.append(Engine(cfg, w, args.gpus))
    rec_f = open(f"{out_prefix}.part{w}", "ab")
    sc_f = open(f"{out_prefix}.part{w}.scores", "ab")
    buf, sbuf = [], []
    restarts = 0
    for j in idx:
        if time.time() > deadline:
            break
        arr = np.array(data[j:j + 1])
        rec = arr[0]
        fen = to_fen(rec)
        raws = []
        for e in engines:
            try:
                s = e.score(fen, args.nodes)
            except RuntimeError:
                restarts += 1
                if restarts > 50:
                    raise
                e.proc.kill()
                e.start()
                s = None
            raws.append(MISSING if s is None else s)
        probs = [win_prob(r) for r in raws if r != MISSING]
        if len(probs) * 2 < len(engines):
            continue
        p = min(P_MAX, max(1 - P_MAX, sum(probs) / len(probs)))
        cp = SCALE * math.log(p / (1 - p))
        arr["score"][0] = round(cp if rec["stm"] == 0 else -cp)
        buf.append(arr.tobytes())
        sbuf.append(np.array(raws, dtype=np.int16).tobytes())
        if len(buf) >= args.flush_every:
            rec_f.write(b"".join(buf)); sc_f.write(b"".join(sbuf)); rec_f.flush(); sc_f.flush()
            with counter.get_lock():
                counter.value += len(buf)
            buf, sbuf = [], []
    rec_f.write(b"".join(buf)); sc_f.write(b"".join(sbuf)); rec_f.close(); sc_f.close()
    with counter.get_lock():
        counter.value += len(buf)
    for e in engines:
        e.close()


def check_engines(configs, args):
    fen = "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 8"
    good = []
    for cfg in configs:
        t = time.time()
        e = None
        try:
            e = Engine(cfg, 0, args.gpus)
            s = e.score(fen, cfg.get("nodes") or args.nodes)
            e.close()
            if s is None:
                raise RuntimeError("no score")
            print(f"  ok    {cfg['name']:26s} score {s:6d}  {1000 * (time.time() - t):6.0f} ms", flush=True)
            good.append(cfg)
        except Exception as ex:
            if e is not None and e.proc is not None:
                e.proc.kill()
            print(f"  DROP  {cfg['name']:26s} {ex}", flush=True)
    return good


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--engines", required=True, help="engine JSON file")
    ap.add_argument("--data", nargs="+", required=True, help="glob(s) of datagen .bin files")
    ap.add_argument("--out", required=True)
    ap.add_argument("--nodes", type=int, default=5000, help="default node limit per engine per position")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--gpus", type=int, default=1)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="grade at most this many positions of the shard")
    ap.add_argument("--seconds", type=int, default=40000)
    ap.add_argument("--flush-every", type=int, default=200)
    ap.add_argument("--min-engines", type=int, default=1)
    args = ap.parse_args()
    start = time.time()
    deadline = start + args.seconds

    with open(args.engines) as f:
        cfg = json.load(f)
    configs = cfg["engines"] if isinstance(cfg, dict) else cfg
    print(f"checking {len(configs)} engines:", flush=True)
    configs = check_engines(configs, args)
    if len(configs) < args.min_engines:
        sys.exit(f"only {len(configs)} engines work, need {args.min_engines}")
    with open(args.out + ".engines.json", "w") as f:
        json.dump([c["name"] for c in configs], f)

    files = sorted({f for p in args.data for f in glob.glob(p, recursive=True)})
    if not files:
        sys.exit(f"no data files match {args.data}")
    data = np.concatenate([np.fromfile(f, dtype=RECORD) for f in files])
    print(f"loaded {len(data):,} positions from {len(files)} file(s): {files}", flush=True)
    order = np.random.default_rng(42).permutation(len(data))[args.shard::args.shards]
    if args.limit:
        order = order[:args.limit]
    tmp = args.out + ".tmp"
    np.save(tmp + ".data.npy", data)
    np.save(tmp + ".idx.npy", order)
    del data
    print(f"grading {len(order):,} positions (shard {args.shard}/{args.shards}) with {len(configs)} engines, "
          f"{args.workers} workers, {args.nodes} nodes", flush=True)

    counter = mp.Value("q", 0)
    procs = [mp.Process(target=worker_main, args=(w, args, configs, tmp + ".data.npy", tmp + ".idx.npy",
                                                  args.out, deadline, counter)) for w in range(args.workers)]
    for p in procs:
        p.start()
    last = 0
    while any(p.is_alive() for p in procs):
        for p in procs:
            p.join(timeout=60 / len(procs))
        if time.time() - last >= 300:
            last = time.time()
            n = counter.value
            el = time.time() - start
            print(f"  {n:,}/{len(order):,} graded  {n / max(el, 1):.1f} pos/s  {el / 3600:.2f} h", flush=True)
    bad = [p.exitcode for p in procs if p.exitcode]
    if bad:
        print(f"warning: {len(bad)} worker(s) failed: {bad}", flush=True)

    with open(args.out, "wb") as out, open(args.out + ".scores.raw", "wb") as sout:
        for w in range(args.workers):
            for src, dst in ((f"{args.out}.part{w}", out), (f"{args.out}.part{w}.scores", sout)):
                if os.path.exists(src):
                    with open(src, "rb") as f:
                        dst.write(f.read())
                    os.remove(src)
    raw = np.fromfile(args.out + ".scores.raw", dtype=np.int16).reshape(-1, len(configs))
    np.save(args.out + ".scores.npy", raw)
    os.remove(args.out + ".scores.raw")
    for suffix in (".data.npy", ".idx.npy"):
        os.remove(tmp + suffix)
    n = len(raw)
    print(f"done: {n:,} positions -> {args.out} in {(time.time() - start) / 3600:.2f} h", flush=True)
    if n:
        ok = raw != MISSING
        print("per-engine coverage: " + ", ".join(f"{c['name']} {ok[:, i].mean():.1%}" for i, c in enumerate(configs)), flush=True)


if __name__ == "__main__":
    main()
