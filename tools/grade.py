#!/usr/bin/env python3
import argparse
import glob
import json
import math
import multiprocessing as mp
import os
import re
import signal
import sys
import time

import chess
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from relabel_ensemble import RECORD, MISSING, SCALE, Engine, to_fen, win_prob

CATEGORIES = ["all", "tactical", "in_check", "imbalance", "king_attack", "endgame", "opening", "quiet", "worse"]
CAT = {c: 1 << i for i, c in enumerate(CATEGORIES)}
PARTS = ("rec", "key", "cats", "rs", "raw")
VALUE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}


def material(board, color):
    return sum(VALUE[p.piece_type] for p in board.piece_map().values() if p.color == color)


def hanging(board, color):
    n = 0
    for sq, p in board.piece_map().items():
        if p.color != color or p.piece_type == chess.KING:
            continue
        attackers = board.attackers(not color, sq)
        if not attackers:
            continue
        if not board.attackers(color, sq):
            n += 1
        elif min(VALUE[board.piece_type_at(a)] or 100 for a in attackers) < VALUE[p.piece_type]:
            n += 1
    return n


def king_pressure(board, color):
    k = board.king(color)
    if k is None:
        return 0
    zone = chess.SquareSet(chess.BB_KING_ATTACKS[k]) | chess.SquareSet.from_square(k)
    attacks = sum(len(board.attackers(not color, s)) for s in zone)
    shield_rank = 1 if color == chess.WHITE else -1
    shield = 0
    for df in (-1, 0, 1):
        f, r = chess.square_file(k) + df, chess.square_rank(k) + shield_rank
        if 0 <= f < 8 and 0 <= r < 8 and board.piece_at(chess.square(f, r)) == chess.Piece(chess.PAWN, color):
            shield += 1
    return attacks + 2 * (3 - shield)


def categorize(fen, fullmove):
    b = chess.Board(fen)
    stm = b.turn
    cats = CAT["all"]
    if b.is_check():
        cats |= CAT["in_check"] | CAT["tactical"]
    if hanging(b, stm) or hanging(b, not stm):
        cats |= CAT["tactical"]
    diff = material(b, chess.WHITE) - material(b, chess.BLACK)
    minor_major = {c: (len(b.pieces(chess.KNIGHT, c)) + len(b.pieces(chess.BISHOP, c)),
                       len(b.pieces(chess.ROOK, c)), len(b.pieces(chess.QUEEN, c))) for c in chess.COLORS}
    if 2 <= abs(diff) <= 8 or (abs(diff) <= 1 and minor_major[chess.WHITE] != minor_major[chess.BLACK]
                               and sum(minor_major[chess.WHITE]) != sum(minor_major[chess.BLACK])):
        cats |= CAT["imbalance"]
    queens = len(b.pieces(chess.QUEEN, chess.WHITE)) + len(b.pieces(chess.QUEEN, chess.BLACK))
    if queens and max(king_pressure(b, chess.WHITE), king_pressure(b, chess.BLACK)) >= 9:
        cats |= CAT["king_attack"]
    non_pawn = sum(VALUE[p.piece_type] for p in b.piece_map().values() if p.piece_type not in (chess.PAWN, chess.KING))
    if non_pawn <= 14:
        cats |= CAT["endgame"]
    elif fullmove <= 12:
        cats |= CAT["opening"]
    if not cats & (CAT["tactical"] | CAT["endgame"] | CAT["opening"] | CAT["imbalance"] | CAT["king_attack"]):
        cats |= CAT["quiet"]
    return cats


def load_config(path):
    with open(path) as f:
        cfg = json.load(f)
    by_name = {e["name"]: e for e in cfg["engines"]}
    roles = []
    for r in cfg["roles"]:
        engines = [by_name[n] for n in r["engines"] if n in by_name]
        roles.append({**r, "engines": engines, "mask": sum(CAT[c] for c in r["categories"])})
    return roles


def worker_main(w, args, roles, tmp, out, deadline, counter, stop):
    data = np.load(tmp + ".data.npy", mmap_mode="r")
    idx = np.load(tmp + ".idx.npy", mmap_mode="r")[w::args.workers]
    flat = [(ri, e) for ri, r in enumerate(roles) for e in r["engines"]]
    engines = [Engine(cfg, w, args.gpus) for _, cfg in flat]
    referee = next((i for i, (ri, _) in enumerate(flat) if roles[ri].get("referee")), None)
    R, E = len(roles), len(flat)
    only_mask = sum(CAT[c] for c in args.only.split(",")) if args.only else 0
    files = {k: open(f"{out}.part{w}.{k}", "ab") for k in PARTS}
    bufs = {k: [] for k in files}
    restarts = 0
    done = 0

    def run(i, fen):
        nonlocal restarts
        role = roles[flat[i][0]]
        try:
            s = engines[i].score(fen, role.get("nodes", args.nodes))
        except RuntimeError:
            restarts += 1
            if restarts > 100:
                raise
            engines[i].proc.kill()
            engines[i].start()
            s = None
        return MISSING if s is None else s

    for j in idx:
        if stop.value or time.time() > deadline:
            break
        arr = np.array(data[j:j + 1])
        rec = arr[0]
        fen = to_fen(rec)
        try:
            cats = categorize(fen, int(rec["fullmove"]))
        except Exception:
            continue
        if only_mask and not cats & only_mask:
            continue
        raw = np.full(E, MISSING, np.int16)
        if referee is not None:
            raw[referee] = run(referee, fen)
            if raw[referee] != MISSING and raw[referee] <= -150:
                cats |= CAT["worse"]
        for i, (ri, _) in enumerate(flat):
            if i != referee and cats & roles[ri]["mask"]:
                raw[i] = run(i, fen)
        rs = np.zeros((R, 2), np.float32)
        for i, (ri, ecfg) in enumerate(flat):
            if raw[i] != MISSING:
                wgt = ecfg.get("weight", roles[ri].get("weight", 1.0))
                rs[ri, 0] += wgt
                rs[ri, 1] += wgt * win_prob(int(raw[i]))
        if rs[:, 0].sum() <= 0:
            continue
        p = float(rs[:, 1].sum() / rs[:, 0].sum())
        p = min(0.999, max(0.001, p))
        cp = SCALE * math.log(p / (1 - p))
        bufs["key"].append(arr.tobytes())
        arr["score"][0] = round(cp if rec["stm"] == 0 else -cp)
        bufs["rec"].append(arr.tobytes())
        bufs["cats"].append(np.uint16(cats).tobytes())
        bufs["rs"].append(rs.tobytes())
        bufs["raw"].append(raw.tobytes())
        done += 1
        if done % args.flush_every == 0:
            for k, f in files.items():
                f.write(b"".join(bufs[k])); f.flush(); bufs[k] = []
            with counter.get_lock():
                counter.value += args.flush_every
    for k, f in files.items():
        f.write(b"".join(bufs[k])); f.close()
    with counter.get_lock():
        counter.value += done % args.flush_every
    for e in engines:
        e.close()


def finalize(out, info, start):
    R, E = len(info["roles"]), len(info["engines"])
    size = {"rec": RECORD.itemsize, "key": RECORD.itemsize, "cats": 2, "rs": R * 2 * 4, "raw": E * 2}
    workers = sorted(int(m.group(1)) for f in glob.glob(glob.escape(out) + ".part*.rec")
                     if (m := re.search(r"\.part(\d+)\.rec$", f)))
    chunks = {k: [] for k in PARTS}
    for w in workers:
        blobs = {}
        for k in PARTS:
            fn = f"{out}.part{w}.{k}"
            blobs[k] = open(fn, "rb").read() if os.path.exists(fn) else b""
        n = min(len(blobs[k]) // size[k] for k in PARTS)
        for k in PARTS:
            chunks[k].append(blobs[k][:n * size[k]])
    rec = np.frombuffer(b"".join(chunks["rec"]), dtype=RECORD)
    rec.tofile(out)
    np.savez_compressed(
        out + ".meta.npz",
        key=np.frombuffer(b"".join(chunks["key"]), dtype=RECORD),
        cats=np.frombuffer(b"".join(chunks["cats"]), dtype=np.uint16),
        role_sum=np.frombuffer(b"".join(chunks["rs"]), dtype=np.float32).reshape(-1, R, 2),
        raw=np.frombuffer(b"".join(chunks["raw"]), dtype=np.int16).reshape(-1, E),
        roles=np.array(info["roles"]),
        engines=np.array(info["engines"]),
        categories=np.array(CATEGORIES))
    for w in workers:
        for k in PARTS:
            if os.path.exists(f"{out}.part{w}.{k}"):
                os.remove(f"{out}.part{w}.{k}")
    for suffix in (".tmp.data.npy", ".tmp.idx.npy"):
        if os.path.exists(out + suffix):
            os.remove(out + suffix)
    print(f"done: {len(rec):,} positions -> {out} in {(time.time() - start) / 3600:.2f} h", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", required=True, help="graders JSON (engines + roles)")
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--nodes", type=int, default=5000)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    ap.add_argument("--gpus", type=int, default=1)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--reverse", action="store_true", help="walk the shard from the end")
    ap.add_argument("--part", type=int, default=0, help="split the shard further: take every PARTS-th position from PART")
    ap.add_argument("--parts", type=int, default=1)
    ap.add_argument("--skip", type=int, default=0, help="skip the first SKIP positions of this runner's order")
    ap.add_argument("--seconds", type=int, default=40000)
    ap.add_argument("--flush-every", type=int, default=100)
    ap.add_argument("--only", default="", help="comma list of categories: only grade positions in them (e.g. for the Lc0 GPU run)")
    ap.add_argument("--finalize-only", action="store_true", help="rebuild OUT and OUT.meta.npz from part files left by a killed run")
    args = ap.parse_args()
    start = time.time()
    deadline = start + args.seconds
    info_path = args.out + ".roles.json"
    if args.finalize_only:
        if not os.path.exists(info_path):
            sys.exit(f"{info_path} missing: cannot finalize")
        with open(info_path) as f:
            finalize(args.out, json.load(f), start)
        return

    roles = load_config(args.config)
    print("checking graders:", flush=True)
    fen = "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 8"
    for r in roles:
        keep = []
        for cfg in r["engines"]:
            t = time.time()
            e = None
            try:
                e = Engine(cfg, 0, args.gpus)
                s = e.score(fen, r.get("nodes", args.nodes))
                e.close()
                if s is None:
                    raise RuntimeError("no score")
                keep.append(cfg)
                print(f"  ok    {r['name']:16s} {cfg['name']:30s} {s:6d} cp {1000 * (time.time() - t):6.0f} ms", flush=True)
            except Exception as ex:
                if e is not None and e.proc is not None:
                    e.proc.kill()
                print(f"  DROP  {r['name']:16s} {cfg['name']:30s} {ex}", flush=True)
        r["engines"] = keep
    roles = [r for r in roles if r["engines"]]
    if not roles:
        sys.exit("no working graders")
    info = {"roles": [r["name"] for r in roles],
            "engines": [f"{r['name']}:{e['name']}" for r in roles for e in r["engines"]]}
    with open(info_path, "w") as f:
        json.dump(info, f)

    files = sorted({f for p in args.data for f in glob.glob(p, recursive=True)})
    if not files:
        sys.exit(f"no data files match {args.data}")
    data = np.concatenate([np.fromfile(f, dtype=RECORD) for f in files])
    print(f"loaded {len(data):,} positions from {files}", flush=True)
    order = np.random.default_rng(42).permutation(len(data))[args.shard::args.shards]
    if args.reverse:
        order = order[::-1]
    order = order[args.part::args.parts]
    if args.skip:
        order = order[args.skip:]
    if args.limit:
        order = order[:args.limit]
    tmp = args.out + ".tmp"
    np.save(tmp + ".data.npy", data)
    np.save(tmp + ".idx.npy", order)
    del data
    print(f"grading {len(order):,} positions (shard {args.shard}/{args.shards}), {args.workers} workers, roles: "
          + ", ".join(f"{r['name']}[{len(r['engines'])}]" for r in roles), flush=True)

    counter = mp.Value("q", 0)
    stop = mp.Value("b", 0)

    def request_stop(signum, frame):
        stop.value = 1
        print(f"signal {signum}: stopping after the current positions", flush=True)

    signal.signal(signal.SIGTERM, request_stop)
    procs = [mp.Process(target=worker_main, args=(w, args, roles, tmp, args.out, deadline, counter, stop))
             for w in range(args.workers)]
    for p in procs:
        p.start()
    last = time.time()
    while any(p.is_alive() for p in procs):
        for p in procs:
            p.join(timeout=10)
        if time.time() - last >= 300:
            last = time.time()
            el = time.time() - start
            print(f"  {counter.value:,}/{len(order):,} graded  {counter.value / el:.1f} pos/s  {el / 3600:.2f} h", flush=True)
    bad = [p.exitcode for p in procs if p.exitcode]
    if bad:
        print(f"warning: {len(bad)} worker(s) failed: {bad}", flush=True)

    finalize(args.out, info, start)


if __name__ == "__main__":
    main()
