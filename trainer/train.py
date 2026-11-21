#!/usr/bin/env python3
"""Train a Nexarch NNUE on self-play data.

Network: (768 -> H) x 2 perspectives -> 1 with SCReLU, exactly the layout the engine runs on the CPU.
Training runs on a GPU when one is available; the result is quantised to integers for fast CPU inference.
Data: 32-byte records written by `nexarch datagen` (see engine/src/datagen.cpp).
"""
import argparse
import glob
import math
import struct
import time

import numpy as np
import torch
import torch.nn as nn

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])
assert RECORD.itemsize == 32
QA, QB, SCALE = 255, 64, 400
PAD = 768  # padding slot, contributes nothing
CHECK_FENS = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
    "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 8",
    "2r3k1/pp3ppp/4p3/3pP3/3P4/P1R2N2/1q3PPP/3Q2K1 b - - 0 1",
    "8/8/8/4k3/8/8/3QK3/8 w - - 0 1",
]


def load_records(patterns, max_positions=0):
    files = sorted({f for p in patterns for f in glob.glob(p, recursive=True)})
    if not files:
        raise SystemExit(f"no data files match {patterns}")
    data = np.concatenate([np.fromfile(f, dtype=RECORD) for f in files])
    print(f"loaded {len(data):,} positions from {len(files)} file(s)", flush=True)
    if max_positions and len(data) > max_positions:
        data = data[np.random.default_rng(0).permutation(len(data))[:max_positions]]
    return data


def decode(rec, chunk=500_000):
    """Feature lists for both perspectives, padded to 32 pieces: (side to move, opponent) int16 [N, 32]."""
    n = len(rec)
    us = np.full((n, 32), PAD, np.int16)
    them = np.full((n, 32), PAD, np.int16)
    for start in range(0, n, chunk):
        r = rec[start:start + chunk]
        m = len(r)
        occ = np.ascontiguousarray(r["occ"]).view(np.uint8).reshape(m, 8)
        bits = np.unpackbits(occ, axis=1, bitorder="little").astype(bool)  # bit i = square i
        nibbles = np.empty((m, 32), np.uint8)
        nibbles[:, 0::2] = r["pcs"] & 15
        nibbles[:, 1::2] = r["pcs"] >> 4
        slot = np.cumsum(bits, axis=1, dtype=np.int16) - 1
        rows, squares = np.nonzero(bits)
        slots = slot[rows, squares]
        codes = nibbles[rows, slots].astype(np.int16)
        color, ptype = codes // 6, codes % 6
        stm = r["stm"][rows].astype(np.int16)
        squares = squares.astype(np.int16)

        def feature(persp):
            relative = (color != persp).astype(np.int16) * 384
            return relative + ptype * 64 + np.where(persp == 0, squares, squares ^ 56)

        us[start + rows, slots] = feature(stm)
        them[start + rows, slots] = feature(1 - stm)
    return us, them


def targets(rec, wdl):
    """Blend of game result and search score, both from the side to move's point of view."""
    stm = rec["stm"].astype(np.float32)
    score = rec["score"].astype(np.float32) * (1 - 2 * stm)
    result = rec["result"].astype(np.float32) / 2
    result = np.where(stm == 0, result, 1 - result)
    return (wdl * result + (1 - wdl) / (1 + np.exp(-score / SCALE))).astype(np.float32)


class NNUE(nn.Module):
    def __init__(self, hidden):
        super().__init__()
        self.hidden = hidden
        self.ft = nn.EmbeddingBag(PAD + 1, hidden, mode="sum", padding_idx=PAD)
        self.ft_bias = nn.Parameter(torch.zeros(hidden))
        self.out = nn.Linear(2 * hidden, 1)
        with torch.no_grad():
            self.ft.weight.normal_(0.0, 0.05)
            self.ft.weight[PAD].zero_()

    def forward(self, us, them):
        a = (self.ft(us) + self.ft_bias).clamp(0, 1).square()
        b = (self.ft(them) + self.ft_bias).clamp(0, 1).square()
        return self.out(torch.cat([a, b], dim=1)).squeeze(1)

    def clip(self):  # keep weights inside the integer range the engine uses
        with torch.no_grad():
            self.ft.weight.clamp_(-1.98, 1.98)
            self.out.weight.clamp_(-1.98, 1.98)


def quantize(model):
    ft_w = model.ft.weight.detach().cpu().double()[:768]
    q = lambda t, s: torch.round(t * s).clamp(-32767, 32767).to(torch.int16).numpy()
    return (q(ft_w, QA), q(model.ft_bias.detach().cpu().double(), QA),
            q(model.out.weight.detach().cpu().double()[0], QB),
            int(round(float(model.out.bias.detach().cpu()[0]) * QA * QB)))


def export(model, path):
    ft_w, ft_b, out_w, out_b = quantize(model)
    with open(path, "wb") as f:
        f.write(b"NXNN")
        f.write(struct.pack("<III", 1, model.hidden, 0))
        for arr in (ft_w, ft_b, out_w):
            f.write(arr.astype("<i2").tobytes())
        f.write(struct.pack("<i", out_b))
    print(f"wrote {path} (hidden {model.hidden})", flush=True)


def trunc_div(a, b):  # C++ integer division rounds toward zero
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def fen_features(fen):
    placement, side = fen.split()[:2]
    stm = 0 if side == "w" else 1
    us, them, rank, file = [], [], 7, 0
    for ch in placement:
        if ch == "/":
            rank, file = rank - 1, 0
        elif ch.isdigit():
            file += int(ch)
        else:
            code = "PNBRQKpnbrqk".index(ch)
            color, ptype, sq = code // 6, code % 6, rank * 8 + file
            feat = lambda p: (0 if color == p else 384) + ptype * 64 + (sq if p == 0 else sq ^ 56)
            us.append(feat(stm))
            them.append(feat(1 - stm))
            file += 1
    return us, them


def quantized_eval(q, fen):
    """Bit-exact copy of the engine's integer evaluation (side to move's view, centipawns)."""
    ft_w, ft_b, out_w, out_b = (a.astype(np.int64) if isinstance(a, np.ndarray) else a for a in q)
    h = len(ft_b)
    us, them = fen_features(fen)
    x = np.clip(ft_b + ft_w[us].sum(0), 0, QA)
    y = np.clip(ft_b + ft_w[them].sum(0), 0, QA)
    total = int((x * x * out_w[:h]).sum() + (y * y * out_w[h:]).sum())
    return trunc_div((trunc_div(total, QA) + out_b) * SCALE, QA * QB)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", nargs="+", required=True, help="glob(s) of datagen .bin files")
    p.add_argument("--out", default="nexarch.nnue")
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--batch", type=int, default=16384)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--wdl", type=float, default=0.5, help="weight of the game result vs the search score")
    p.add_argument("--max-positions", type=int, default=0)
    p.add_argument("--resume", help="continue from a .pt checkpoint")
    p.add_argument("--device", default="auto")
    args = p.parse_args()

    torch.manual_seed(0)
    dev = torch.device("cuda" if args.device == "auto" and torch.cuda.is_available() else
                       args.device if args.device != "auto" else "cpu")
    print(f"device: {dev}" + (f" ({torch.cuda.get_device_name(dev)})" if dev.type == "cuda" else ""), flush=True)

    rec = load_records(args.data, args.max_positions)
    t0 = time.time()
    us, them = decode(rec)
    tgt = targets(rec, args.wdl)
    print(f"decoded in {time.time() - t0:.1f}s; mean target {tgt.mean():.3f}", flush=True)

    n = len(rec)
    order = np.random.default_rng(1).permutation(n)
    n_val = min(max(n // 50, 1), 200_000)
    val_idx, train_idx = order[:n_val], order[n_val:]
    to = lambda a: torch.from_numpy(np.ascontiguousarray(a)).to(dev)
    tr = [to(us[train_idx]), to(them[train_idx]), to(tgt[train_idx])]
    va = [to(us[val_idx]), to(them[val_idx]), to(tgt[val_idx])]
    del us, them

    model = NNUE(args.hidden).to(dev)
    if args.resume:
        model.load_state_dict(torch.load(args.resume, map_location=dev))
        print(f"resumed from {args.resume}", flush=True)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.0)
    steps_per_epoch = max(1, math.ceil(len(train_idx) / args.batch))
    total_steps = steps_per_epoch * args.epochs
    warmup = min(200, total_steps // 10 + 1)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warmup) * (0.02 + 0.98 * 0.5 * (1 + math.cos(math.pi * min(s, total_steps) / total_steps))))

    def loss_on(u, t, y):
        return (torch.sigmoid(model(u.long(), t.long())) - y).square().mean()

    print(f"training {len(train_idx):,} positions, {args.epochs} epochs x {steps_per_epoch} steps, hidden {args.hidden}", flush=True)
    start = time.time()
    for epoch in range(1, args.epochs + 1):
        model.train()
        perm = torch.randperm(len(train_idx), device=dev)
        running = 0.0
        for i in range(steps_per_epoch):
            idx = perm[i * args.batch:(i + 1) * args.batch]
            loss = loss_on(tr[0][idx], tr[1][idx], tr[2][idx])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            model.clip()
            sched.step()
            running += loss.item()
        model.eval()
        with torch.no_grad():
            val = sum(loss_on(va[0][j:j + 65536], va[1][j:j + 65536], va[2][j:j + 65536]).item() * len(va[2][j:j + 65536])
                      for j in range(0, n_val, 65536)) / n_val
        print(f"epoch {epoch:3d}  train {running / steps_per_epoch:.5f}  val {val:.5f}  lr {sched.get_last_lr()[0]:.2e}  "
              f"{time.time() - start:.0f}s", flush=True)

    export(model, args.out)
    torch.save(model.state_dict(), args.out.rsplit(".", 1)[0] + ".pt")
    q = quantize(model)
    with torch.no_grad():
        for fen in CHECK_FENS:
            u, t = fen_features(fen)
            pad = lambda f: torch.tensor([f + [PAD] * (32 - len(f))], device=dev)
            raw = float(model(pad(u), pad(t))[0]) * SCALE
            print(f"check: quantized {quantized_eval(q, fen):6d}  float {raw:8.1f}  {fen}", flush=True)


if __name__ == "__main__":
    main()
