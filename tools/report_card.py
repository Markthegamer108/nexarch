#!/usr/bin/env python3
import argparse
import glob

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


def pava(y, w):
    vals, wts, sizes = [], [], []
    for yi, wi in zip(y, w):
        vals.append(float(yi)); wts.append(float(wi)); sizes.append(1)
        while len(vals) > 1 and vals[-2] > vals[-1]:
            v2, w2, s2 = vals.pop(), wts.pop(), sizes.pop()
            v1, w1, s1 = vals.pop(), wts.pop(), sizes.pop()
            vals.append((v1 * w1 + v2 * w2) / (w1 + w2)); wts.append(w1 + w2); sizes.append(s1 + s2)
    return np.repeat(vals, sizes)


def calibrate(rs, role_names, role, bins=200):
    if role not in role_names or len(role_names) < 2:
        print(f"calibration: role {role} missing or alone, skipped")
        return
    c = role_names.index(role)
    w_c = rs[:, c, 0].astype(np.float64)
    w_o = rs[:, :, 0].sum(1, dtype=np.float64) - w_c
    s_o = rs[:, :, 1].sum(1, dtype=np.float64) - rs[:, c, 1]
    both = (w_c > 0) & (w_o > 0)
    if both.sum() < 10_000:
        print(f"calibration: only {int(both.sum()):,} positions graded by both {role} and the panel, skipped")
        return
    x = rs[both, c, 1] / w_c[both]
    y = s_o[both] / w_o[both]
    edges = np.quantile(x, np.linspace(0, 1, bins + 1))
    idx = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, bins - 1)
    cnt = np.bincount(idx, minlength=bins)
    keep = cnt > 0
    bx = np.bincount(idx, weights=x, minlength=bins)[keep] / cnt[keep]
    by = pava(np.bincount(idx, weights=y, minlength=bins)[keep] / cnt[keep], cnt[keep])
    before = float(np.abs(x - y).mean())
    after = float(np.abs(np.interp(x, bx, by) - y).mean())
    has = w_c > 0
    rs[has, c, 1] = (np.interp(rs[has, c, 1] / w_c[has], bx, by) * w_c[has]).astype(np.float32)
    pts = ", ".join(f"{a:.2f}->{b:.2f}" for a, b in zip(np.interp([.1, .25, .5, .75, .9], np.linspace(0, 1, len(bx)), bx),
                                                         np.interp(np.interp([.1, .25, .5, .75, .9], np.linspace(0, 1, len(bx)), bx), bx, by)))
    print(f"calibration of {role}: fitted on {int(both.sum()):,} positions graded by both; mean gap to the panel "
          f"{100 * before:.1f}% -> {100 * after:.1f}%; applied to {int(has.sum()):,} positions ({pts})", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("meta", nargs="+", help="glob(s) of *.meta.npz from tools/grade.py")
    ap.add_argument("--out", help="write merged, relabeled positions here")
    ap.add_argument("--calibrate", default="", help="role to map onto the rest of the panel's scale first (e.g. lc0)")
    args = ap.parse_args()
    files = sorted({f for p in args.meta for f in glob.glob(p, recursive=True)})
    if not files:
        raise SystemExit("no meta files")

    role_names, keys, info = [], [], []
    for f in files:
        m = np.load(f)
        names = [str(r) for r in m["roles"]]
        for r in names:
            if r not in role_names:
                role_names.append(r)
        k = m["key"]
        if len(k) != len(m["cats"]) or m["role_sum"].shape != (len(k), len(names), 2):
            raise SystemExit(f"{f}: inconsistent arrays (key {len(k)}, cats {len(m['cats'])}, "
                             f"role_sum {m['role_sum'].shape}, roles {len(names)})")
        keys.append(k)
        info.append((f, names, len(k)))
        print(f"{f}: {len(k):,} positions, roles {names}", flush=True)
    R = len(role_names)
    key = np.concatenate(keys)
    del keys
    total = len(key)
    uniq, inv = np.unique(key.view(np.dtype((np.void, RECORD.itemsize))), return_inverse=True)
    del key
    inv = inv.reshape(-1)
    n = len(uniq)

    rs = np.zeros((n, R, 2), np.float32)
    cats = np.zeros(n, np.uint16)
    off = 0
    for f, names, cnt in info:
        m = np.load(f)
        s, c = m["role_sum"], m["cats"]
        cols = np.array([role_names.index(r) for r in names])
        for a in range(0, cnt, 1_000_000):
            idx = inv[off + a:off + min(cnt, a + 1_000_000)]
            np.add.at(rs, (idx[:, None], cols[None, :]), s[a:a + len(idx)])
            np.bitwise_or.at(cats, idx, c[a:a + len(idx)])
        del s, c
        off += cnt
    del inv
    base = uniq.view(RECORD).reshape(-1)
    print(f"merged: {n:,} unique positions (from {total:,} graded entries)")
    if args.calibrate:
        calibrate(rs, role_names, args.calibrate)

    nex_stm = base["score"].astype(np.float64) * np.where(base["stm"] == 0, 1, -1)
    p_nex = 1 / (1 + np.exp(-nex_stm / SCALE))
    del nex_stm
    tot = rs[:, :, 0].sum(1, dtype=np.float64)
    p_all = rs[:, :, 1].sum(1, dtype=np.float64) / np.maximum(tot, 1e-9)

    print(f"\nReport card for the net that played these games (its self-play scores vs the graders)\n")
    print(f"{'role':18s} {'positions':>10s} {'wrong side':>11s} {'mean err':>9s}  grade")

    def row(name, has, p):
        if not has.any():
            return
        pr, pn = p[has], p_nex[has]
        decisive = np.abs(pr - 0.5) > 0.12
        wrong = float(((pr[decisive] > 0.5) != (pn[decisive] > 0.5)).mean()) if decisive.any() else 0.0
        err = float(np.abs(pr - pn).mean())
        print(f"{name:18s} {has.sum():10,d} {100 * wrong:10.1f}% {100 * err:8.1f}%  {grade_letter(wrong, err)}", flush=True)

    row("whole panel", tot > 0, p_all)
    for r, name in enumerate(role_names):
        has = rs[:, r, 0] > 0
        row(name, has, rs[:, r, 1].astype(np.float64) / np.maximum(rs[:, r, 0], 1e-9))

    if args.out:
        del rs
        keep = tot > 0
        p = np.clip(p_all[keep], 0.001, 0.999)
        cp = SCALE * np.log(p / (1 - p))
        out = base[keep]
        out["score"] = np.round(np.where(out["stm"] == 0, cp, -cp)).astype(np.int16)
        out.tofile(args.out)
        print(f"\nwrote {len(out):,} positions -> {args.out}")


if __name__ == "__main__":
    main()
