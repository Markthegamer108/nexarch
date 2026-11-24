#!/usr/bin/env python3
import argparse
import os
import sys

import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trainer"))
from train import NNUE, export


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pt", required=True, help=".pt state dict written by trainer/train.py")
    ap.add_argument("--nnue", required=True, help="output .nnue file")
    args = ap.parse_args()
    state = torch.load(args.pt, map_location="cpu")
    hidden = int(state["ft_bias"].shape[0])
    model = NNUE(hidden)
    model.load_state_dict(state)
    model.eval()
    export(model, args.nnue)


if __name__ == "__main__":
    main()
