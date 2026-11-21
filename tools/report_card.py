#!/usr/bin/env python3
"""Merge grading runs (tools/grade.py outputs, e.g. 4 CPU shards + the Lc0 GPU run) and print a
per-role report card for the Nexarch net that played the self-play games.

Positions graded by several runs (same original record) have their role sums added, so Lc0's
verdict is blended into the CPU panel's. --out writes the merged training file.

Report card, per role: how often Nexarch's own self-play score picked the wrong side
(role says one side is better by >1 pawn, Nexarch disagrees), and its mean win-probability error.
"""
import argparse
import glob
import math

import numpy as np

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])
SCALE = 400.0


def grade_letter(wrong_side, err):
    s = 100 - 250 * wrong_side - 120 * err
    for cut, letter in ((90, "A"), (80, "B"), (70, "C"), (60, "D")):
        if s >= cut:
            return letter
    return "F"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("meta", nargs="+", help="glob(s) of *.meta.npz from tools/grade.py")
    ap.add_argument("--out", help="write merged, relabeled positions here")
    args = ap.parse_args()
    files = sorted({f for p in args.meta for f in glob.glob(p, recursive=True)})
    if not files:
        raise SystemExit("no meta files")

    role_names = []
    keys, sums, cats_all = [], [], []
    for f in files:
        m = np.load(f)
        names = [str(r) for r in m["roles"]]
        for r in names:
            if r not in role_names:
                role_names.append(r)
        keys.append(m["key"])
        cats_all.append(m["cats"])
        sums.append((names, m["role_sum"]))
        print(f"{f}: {len(m['key']):,} positions, roles {names}")
    R = len(role_names)
    key = np.concatenate(keys)
    kb = key.view(np.dtype((np.void, RECORD.itemsize)))
    uniq, inv = np.unique(kb, return_inverse=True)
    n = len(uniq)
    rs = np.zeros((n, R, 2), np.float64)
    cats = np.zeros(n, np.uint16)
    off = 0
    for (names, s), c in zip(sums, cats_all):
        idx = inv[off:off + len(s)]
        cols = [role_names.index(r) for r in names]
        np.add.at(rs, (idx[:, None], np.array(cols)[None, :]), s)
        np.bitwise_or.at(cats, idx, c)
        off += len(s)
    base = uniq.view(RECORD).reshape(-1).copy()
    print(f"merged: {n:,} unique positions (from {len(key):,} graded entries)")

    nex_stm = base["score"].astype(np.float64) * np.where(base["stm"] == 0, 1, -1)
    p_nex = 1 / (1 + np.exp(-nex_stm / SCALE))
    tot = rs[:, :, 0].sum(1)
    p_all = rs[:, :, 1].sum(1) / np.maximum(tot, 1e-9)

    print(f"\nReport card for the net that played these games (its self-play scores vs the graders)\n")
    print(f"{'role':18s} {'positions':>10s} {'wrong side':>11s} {'mean err':>9s}  grade")
    rows = [("whole panel", tot > 0, p_all)]
    for r, name in enumerate(role_names):
        has = rs[:, r, 0] > 0
        rows.append((name, has, rs[:, r, 1] / np.maximum(rs[:, r, 0], 1e-9)))
    for name, has, p in rows:
        if not has.any():
            continue
        pr, pn = p[has], p_nex[has]
        decisive = np.abs(pr - 0.5) > 0.12  # role says one side is clearly better (~1 pawn)
        wrong = float(((pr[decisive] > 0.5) != (pn[decisive] > 0.5)).mean()) if decisive.any() else 0.0
        err = float(np.abs(pr - pn).mean())
        print(f"{name:18s} {has.sum():10,d} {100 * wrong:10.1f}% {100 * err:8.1f}%  {grade_letter(wrong, err)}")

    if args.out:
        p = np.clip(p_all, 0.001, 0.999)
        cp = SCALE * np.log(p / (1 - p))
        base["score"] = np.round(np.where(base["stm"] == 0, cp, -cp)).astype(np.int16)
        base[tot > 0].tofile(args.out)
        print(f"\nwrote {int((tot > 0).sum()):,} positions -> {args.out}")


if __name__ == "__main__":
    main()
