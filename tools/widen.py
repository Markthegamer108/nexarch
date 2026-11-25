#!/usr/bin/env python3
import argparse
import os
import sys

import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trainer"))
from train import NNUE, PAD, export


def widen(state, hidden, seed=0, std=0.05):
    old = state["ft_bias"].shape[0]
    if hidden < old or hidden % 16:
        raise SystemExit(f"--hidden must be a multiple of 16 and at least the current {old}")
    g = torch.Generator().manual_seed(seed)
    ft = torch.zeros(PAD + 1, hidden)
    ft[:, :old] = state["ft.weight"]
    ft[:PAD, old:] = torch.randn(PAD, hidden - old, generator=g) * std
    bias = torch.zeros(hidden)
    bias[:old] = state["ft_bias"]
    out = torch.zeros(1, 2 * hidden)
    out[0, :old] = state["out.weight"][0, :old]
    out[0, hidden:hidden + old] = state["out.weight"][0, old:]
    return {"ft.weight": ft, "ft_bias": bias, "out.weight": out, "out.bias": state["out.bias"].clone()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="src", required=True, help="trained .pt checkpoint (e.g. nets/nexarch-g2.pt)")
    ap.add_argument("--hidden", type=int, required=True)
    ap.add_argument("--out", required=True, help="widened .pt checkpoint, for train.py --resume")
    ap.add_argument("--nnue", help="also export the widened network for the engine")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    state = torch.load(args.src, map_location="cpu")
    new = widen(state, args.hidden, args.seed)
    model = NNUE(args.hidden)
    model.load_state_dict(new)
    torch.save(model.state_dict(), args.out)
    print(f"widened {args.src}: {state['ft_bias'].shape[0]} -> {args.hidden} neurons -> {args.out}", flush=True)
    if args.nnue:
        export(model, args.nnue)


if __name__ == "__main__":
    main()
