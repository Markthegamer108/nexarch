#!/usr/bin/env python3
import argparse
import json
import os
import sys

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trainer"))
from train import RECORD, NNUE, decode, targets


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--net", required=True, help=".pt checkpoint or .nnue exported network")
    ap.add_argument("--eval", required=True, help="frozen eval .bin")
    ap.add_argument("--batch", type=int, default=65536)
    ap.add_argument("--wdl", type=float, default=0.4)
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    rec = np.memmap(args.eval, dtype=RECORD, mode="r")
    n = len(rec)
    us, them = decode(rec)
    y = targets(rec, args.wdl)
    if args.net.endswith(".nnue"):
        raise SystemExit("pass the .pt checkpoint; the quantized .nnue cannot be scored directly")
    state = torch.load(args.net, map_location="cpu")
    hidden = int(state["ft_bias"].shape[0])
    model = NNUE(hidden)
    model.load_state_dict(state)
    model.eval()
    total, count = 0.0, 0
    with torch.no_grad():
        for s in range(0, n, args.batch):
            e = min(n, s + args.batch)
            u = torch.from_numpy(us[s:e].astype(np.int64))
            t = torch.from_numpy(them[s:e].astype(np.int64))
            yy = torch.from_numpy(y[s:e])
            loss = ((torch.sigmoid(model(u, t)) - yy) ** 2).mean().item()
            total += loss * (e - s)
            count += e - s
    res = {"net": args.net, "eval": os.path.basename(args.eval), "positions": int(n),
           "hidden": hidden, "loss": round(total / count, 6)}
    print(json.dumps(res))
    if args.json:
        json.dump(res, open(args.json, "w"), indent=1)


if __name__ == "__main__":
    main()
