#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# This file loads Lc0's GPL-3.0 Python module (lczero backends) into the same process, so unlike the
# rest of Nexarch (MIT) it is licensed GPL-3.0-or-later.
"""Grade self-play positions with Lc0's network directly (no search), in big GPU batches.

Why no search: Lc0 search on a T4 runs ~1,000 nodes/s with BT4, i.e. ~6.5 positions/s even at 128 nodes.
One batched network evaluation per position is orders of magnitude faster, and the raw BT4 value head
is still a strong positional judge (that is the role it plays in our panel: imbalance + quiet positions).

Pipeline:
  1. random sample of positions in --only categories (default imbalance,quiet), up to --sample
  2. one process per GPU (CUDA_VISIBLE_DEVICES), each evaluates its share in --batch sized batches
  3. results are appended to part files after every batch, so a time limit or a killed session keeps
     everything finished so far; --finalize-only rebuilds the output from the parts
  4. OUT.meta.npz in tools/grade.py's format (key, cats, role_sum, raw, roles, engines, categories),
     so `tools/report_card.py` merges it with the CPU panel's grading

Needs Lc0 built with -Dpython_bindings=true (module `backends`, path given by --lc0-py).
"""
import argparse
import glob
import math
import multiprocessing as mp
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grade import CAT, CATEGORIES, categorize  # noqa: E402
from relabel_ensemble import RECORD, to_fen  # noqa: E402

SCALE = 400.0


def _cats_chunk(recs):
    out = np.zeros(len(recs), np.uint16)
    for i, r in enumerate(recs):
        try:
            out[i] = categorize(to_fen(r), int(r["fullmove"]))
        except Exception:
            out[i] = 0
    return out


def sample_positions(data, mask, want, cpus, seed):
    order = np.random.default_rng(seed).permutation(len(data))
    picked, cats = [], []
    pos, chunk = 0, 20000
    t = time.time()
    with mp.get_context("fork").Pool(cpus) as pool:
        while sum(len(p) for p in picked) < want and pos < len(order):
            block = order[pos:pos + chunk * cpus]
            pos += len(block)
            parts = pool.map(_cats_chunk, [data[block[i:i + chunk]] for i in range(0, len(block), chunk)])
            c = np.concatenate(parts)
            keep = (c & mask) != 0 if mask else np.ones(len(c), bool)
            picked.append(block[keep])
            cats.append(c[keep])
    idx = np.concatenate(picked)[:want]
    cats = np.concatenate(cats)[:want]
    print(f"sampled {len(idx):,} positions from {pos:,} examined in {time.time() - t:.0f}s", flush=True)
    return idx, cats


def gpu_worker(g, args, tmp, deadline):
    if args.backend.startswith("cuda"):
        os.environ["CUDA_VISIBLE_DEVICES"] = str(g)
    sys.path.insert(0, args.lc0_py)
    import backends as lc

    recs = np.load(tmp + ".recs.npy", mmap_mode="r")[g::args.gpus]
    cats = np.load(tmp + ".cats.npy", mmap_mode="r")[g::args.gpus]
    done_before = 0
    kf = f"{args.out}.gpu{g}.key"
    if os.path.exists(kf):  # resume after a restart: skip what is already graded
        done_before = os.path.getsize(kf) // RECORD.itemsize
    weights = lc.Weights(args.weights)
    backend = lc.Backend(weights=weights, backend=args.backend, options=args.backend_opts or None)
    files = {k: open(f"{args.out}.gpu{g}.{k}", "ab") for k in ("key", "cats", "p")}
    start, last, n = time.time(), time.time(), 0
    for s in range(done_before, len(recs), args.batch):
        if time.time() > deadline:
            print(f"gpu{g}: time limit reached", flush=True)
            break
        r = np.array(recs[s:s + args.batch])
        inputs = [lc.GameState(fen=to_fen(x)).as_input(backend) for x in r]
        outs = backend.evaluate(*inputs)
        p = np.array([(1.0 + o.q()) / 2.0 for o in outs], np.float32)  # side to move's expected score
        files["key"].write(r.tobytes())
        files["cats"].write(np.asarray(cats[s:s + len(r)], np.uint16).tobytes())
        files["p"].write(p.tobytes())
        for f in files.values():
            f.flush()
        n += len(r)
        if time.time() - last >= 60 or s == done_before:
            last = time.time()
            el = time.time() - start
            print(f"gpu{g}: {done_before + n:,}/{len(recs):,}  {n / max(el, 1e-9):.0f} pos/s  {el / 3600:.2f} h", flush=True)
    for f in files.values():
        f.close()
    print(f"gpu{g}: finished {done_before + n:,} positions ({n:,} this run)", flush=True)


def finalize(args):
    keys, cats, ps = [], [], []
    for g in range(args.gpus):
        b = f"{args.out}.gpu{g}"
        if not os.path.exists(b + ".key"):
            continue
        k = np.fromfile(b + ".key", dtype=RECORD)
        c = np.fromfile(b + ".cats", dtype=np.uint16)
        p = np.fromfile(b + ".p", dtype=np.float32)
        n = min(len(k), len(c), len(p))  # a kill mid-write can leave one file a batch ahead
        keys.append(k[:n]); cats.append(c[:n]); ps.append(p[:n])
    if not keys:
        sys.exit("no graded parts found")
    key, cat, p = np.concatenate(keys), np.concatenate(cats), np.concatenate(ps).astype(np.float64)
    pc = np.clip(p, 0.001, 0.999)
    raw = np.round(SCALE * np.log(pc / (1 - pc))).astype(np.int16)[:, None]
    role_sum = np.stack([np.full(len(p), args.weight), args.weight * p], axis=1)[:, None, :].astype(np.float32)
    np.savez_compressed(args.out + ".meta.npz", key=key, cats=cat, role_sum=role_sum, raw=raw,
                        roles=np.array(["lc0"]), engines=np.array([f"lc0:{args.name}"]), categories=np.array(CATEGORIES))
    print(f"wrote {args.out}.meta.npz: {len(key):,} positions, mean expected score {p.mean():.3f}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--lc0-py", required=True, help="directory containing the built `backends` module")
    ap.add_argument("--backend", default="cuda-fp16")
    ap.add_argument("--backend-opts", default="")
    ap.add_argument("--name", default="Lc0 0.32.1 BT4 (network only)")
    ap.add_argument("--gpus", type=int, default=1)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--sample", type=int, default=1_000_000)
    ap.add_argument("--only", default="imbalance,quiet")
    ap.add_argument("--weight", type=float, default=2.0)
    ap.add_argument("--seconds", type=int, default=10800)
    ap.add_argument("--cpus", type=int, default=os.cpu_count())
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--finalize-only", action="store_true")
    args = ap.parse_args()
    deadline = time.time() + args.seconds
    tmp = args.out + ".tmp"

    if not args.finalize_only:
        if not (os.path.exists(tmp + ".recs.npy") and os.path.exists(tmp + ".cats.npy")):
            files = sorted({f for p in args.data for f in glob.glob(p, recursive=True)})
            if not files:
                sys.exit(f"no data files match {args.data}")
            data = np.concatenate([np.fromfile(f, dtype=RECORD) for f in files])
            print(f"loaded {len(data):,} positions from {files}", flush=True)
            mask = sum(CAT[c] for c in args.only.split(",")) if args.only else 0
            if mask:
                idx, cats = sample_positions(data, mask, args.sample, args.cpus, args.seed)
            else:  # no filter: skip the slow python-chess pass (20 min per 10M positions on Kaggle's 4 CPUs);
                # report_card.py ORs in the CPU panel's categories when merging
                idx = np.random.default_rng(args.seed).permutation(len(data))[:args.sample]
                cats = np.full(len(idx), CAT["all"], np.uint16)
                print(f"no category filter: grading {len(idx):,} positions in random order", flush=True)
            np.save(tmp + ".recs.npy", data[idx])
            np.save(tmp + ".cats.npy", cats)
            del data
        ctx = mp.get_context("spawn")  # fresh process per GPU, so CUDA_VISIBLE_DEVICES applies before CUDA init
        procs = [ctx.Process(target=gpu_worker, args=(g, args, tmp, deadline)) for g in range(args.gpus)]
        for p in procs:
            p.start()
        for p in procs:
            p.join()
        bad = [p.exitcode for p in procs if p.exitcode]
        if bad:
            print(f"warning: {len(bad)} GPU worker(s) failed: {bad}", flush=True)
    finalize(args)


if __name__ == "__main__":
    main()
