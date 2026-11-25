#!/usr/bin/env python3
import argparse
import glob
import hashlib
import json
import os
import platform
import tempfile
import time
from pathlib import Path

import numpy as np

RECORD = np.dtype([
    ("occ", "<u8"), ("pcs", "u1", (16,)), ("score", "<i2"), ("result", "u1"),
    ("stm", "u1"), ("fullmove", "<u2"), ("halfmove", "u1"), ("spare", "u1"),
])
PATTERNS = ("graded-g3-full.bin", "t80-*.bin", "lichess-*.bin", "fishnet-*.bin", "selfplay-*.bin")
UINT64 = np.uint64
KEY_BYTES = 25


def fingerprint(words, stm):
    h = words[:, 0] ^ (words[:, 1] * UINT64(0x9E3779B97F4A7C15))
    h ^= words[:, 2] * UINT64(0xD6E8FEB86659FD93)
    h ^= stm.astype(np.uint64) * UINT64(0xC2B2AE3D27D4EB4F)
    h ^= h >> UINT64(31)
    h *= UINT64(0xBF58476D1CE4E5B9)
    return h ^ (h >> UINT64(27))


def read_records(data):
    if len(data) == 0 or len(data) % RECORD.itemsize:
        raise ValueError(f"invalid record byte count: {len(data):,}")
    return np.frombuffer(data, dtype=RECORD), np.frombuffer(data, dtype="<u8").reshape(-1, 4)


def packed_keys(words, stm):
    keys = np.empty((len(words), KEY_BYTES), dtype=np.uint8)
    keys[:, :24] = np.ascontiguousarray(words[:, :3]).view(np.uint8).reshape(-1, 24)
    keys[:, 24] = stm
    return keys


def reflected(words):
    out = np.zeros_like(words)
    for start in range(0, len(words), 8192):
        src = np.ascontiguousarray(words[start:start + 8192])
        dst = out[start:start + len(src)]
        occ = src[:, 0].astype("<u8", copy=True).view(np.uint8).reshape(-1, 8)
        dst[:, 0] = np.ascontiguousarray(occ[:, ::-1]).view("<u8").reshape(-1)
        bits = np.unpackbits(occ, axis=1, bitorder="little")
        rows, squares = np.nonzero(bits)
        slots = np.cumsum(bits, axis=1, dtype=np.uint8)[rows, squares] - 1
        rev_slot = np.cumsum(np.unpackbits(occ[:, ::-1], axis=1, bitorder="little"), axis=1, dtype=np.uint8)
        dst_slots = rev_slot[rows, squares ^ 56] - 1
        src_pcs = src[:, 1:3].copy().view(np.uint8)
        codes = (src_pcs[rows, slots // 2] >> (4 * (slots % 2))) & 15
        codes = (codes + 6) % 12
        packed = np.zeros_like(src_pcs)
        np.bitwise_or.at(packed, (rows, dst_slots // 2), codes << (4 * (dst_slots % 2)))
        dst[:, 1:3] = packed.view("<u8")
    return out


def malformed(records, words):
    if hasattr(np, "bitwise_count"):
        count = np.bitwise_count(words[:, 0])
    else:
        occ = np.ascontiguousarray(words[:, 0]).view(np.uint8).reshape(-1, 8)
        count = np.unpackbits(occ, axis=1).sum(axis=1)
    pcs = words[:, 1:3]
    mask = UINT64(0x1111111111111111)
    high = (pcs >> UINT64(3)) & mask
    middle = (pcs >> UINT64(2)) & mask
    bad_piece = (high & middle).any(axis=1)
    two = (pcs >> UINT64(1)) & mask
    one = pcs & mask
    white = (~high & middle & ~two & one) & mask
    black = (high & ~middle & two & one) & mask
    last = records["score"].astype(np.int32)
    one_king = lambda m: ((m[:, 0] == 0) != (m[:, 1] == 0)) & (((m & (m - UINT64(1))) == 0).all(axis=1))
    return ((count < 2) | (count > 32) | bad_piece | ~one_king(white) | ~one_king(black) |
            (records["stm"] > 1) | (records["result"] > 2) | (records["fullmove"] == 0) |
            (np.abs(last) > 32000))


class Holdout:
    def __init__(self, data):
        records, words = read_records(data)
        if malformed(records, words).any():
            raise ValueError("frozen evaluation set contains malformed records")
        all_keys = packed_keys(words, records["stm"])
        hashes = fingerprint(words, records["stm"])
        if len(np.unique(hashes)) != len(hashes):
            raise ValueError("evaluation keys are not unique or their fingerprints collide")
        mirror = reflected(words)
        flip = 1 - records["stm"]
        all_keys = np.concatenate((all_keys, packed_keys(mirror, flip)))
        hashes = np.concatenate((hashes, fingerprint(mirror, flip)))
        order = np.argsort(hashes, kind="stable")
        sorted_hashes, sorted_keys = hashes[order], all_keys[order]
        same = sorted_hashes[1:] == sorted_hashes[:-1]
        if not np.array_equal(sorted_keys[1:][same], sorted_keys[:-1][same]):
            raise ValueError("evaluation fingerprints collide")
        idx = np.flatnonzero(np.r_[True, ~same])
        self.ends = np.r_[idx[1:], len(order)]
        self.starts = idx
        self.order = order % len(records)
        self.hashes = sorted_hashes[idx]
        self.keys = sorted_keys[idx]
        self.mask = (1 << 23) - 1
        self.present = np.zeros(self.mask + 1, dtype=bool)
        self.present[self.hashes & UINT64(self.mask)] = True
        self.seen = np.zeros(len(records), dtype=bool)

    def compare(self, records, words):
        h = fingerprint(words, records["stm"])
        i = np.flatnonzero(self.present[h & UINT64(self.mask)])
        dst = np.searchsorted(self.hashes, h[i])
        bounded = dst < len(self.hashes)
        i, dst = i[bounded], dst[bounded]
        equal = self.hashes[dst] == h[i]
        i, dst = i[equal], dst[equal]
        equal = (self.keys[dst] == packed_keys(words[i], records["stm"][i])).all(axis=1)
        starts, ends = self.starts[dst[equal]], self.ends[dst[equal]]
        return self.order[np.r_[starts, (starts + 1)[ends - starts == 2]]], len(starts)


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)


def scan(path, holdout, chunk):
    seen = np.zeros_like(holdout.seen)
    rows = invalid = matches = 0
    digest = hashlib.sha256()
    before = path.stat()
    with path.open("rb") as f:
        while data := f.read(RECORD.itemsize * chunk):
            records, words = read_records(data)
            digest.update(data)
            rows += len(records)
            invalid += int(malformed(records, words).sum())
            hit, n_matches = holdout.compare(records, words)
            matches += n_matches
            seen[hit] = True
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino) or rows == 0 or rows * RECORD.itemsize != before.st_size:
        raise ValueError(f"empty or changed during audit: {path}")
    holdout.seen |= seen
    return {"positions": rows, "bytes": before.st_size, "sha256": digest.hexdigest(), "malformed": invalid,
            "overlapping_training_rows": matches, "overlapping_holdout_positions": int(seen.sum())}


def audit(root, eval_file, out, expected_positions, expected_files, chunk, expected_sha256=None):
    paths = sorted({Path(p) for pattern in PATTERNS for p in glob.glob(str(root / "**" / pattern), recursive=True)})
    if len(paths) != expected_files or sum(p.stat().st_size for p in paths) != expected_positions * RECORD.itemsize:
        raise ValueError(f"mounted data does not match expected {expected_files} files / {expected_positions:,} positions")
    if any(p.samefile(eval_file) for p in paths):
        raise ValueError("frozen evaluation file is also in the training inputs")
    data = eval_file.read_bytes()
    frozen_sha256 = hashlib.sha256(data).hexdigest()
    if expected_sha256 and frozen_sha256 != expected_sha256:
        raise ValueError(f"frozen SHA-256 mismatch: {frozen_sha256}")
    frozen, _ = read_records(data)
    holdout = Holdout(data)
    sources = []
    for path in paths:
        start = time.monotonic()
        entry = {"path": str(path.relative_to(root)), **scan(path, holdout, chunk)}
        sources.append(entry)
        print(f"{entry['path']}: {entry['positions']:,} positions, {entry['malformed']:,} malformed, "
              f"{entry['overlapping_holdout_positions']:,} holdout hits in {time.monotonic() - start:.1f}s", flush=True)
    clean = frozen[~holdout.seen].tobytes()
    report = {
        "key": "piece placement and side to move, also checked after color swap and rank reflection; ignores labels, counters, castling and en passant",
        "host": platform.platform(), "numpy": np.__version__, "files": sources,
        "training_positions": sum(r["positions"] for r in sources),
        "malformed_training_rows": sum(r["malformed"] for r in sources),
        "frozen_sha256": frozen_sha256, "frozen_positions": len(frozen),
        "overlap_positions": int(holdout.seen.sum()), "clean_positions": len(clean) // RECORD.itemsize,
        "clean_sha256": hashlib.sha256(clean).hexdigest(),
    }
    atomic_write(out / "holdout-audit.json", (json.dumps(report, indent=2) + "\n").encode())
    if not clean or report["malformed_training_rows"]:
        raise ValueError("no usable holdout or malformed training data; see holdout-audit.json")
    atomic_write(out / "eval-g5-unseen.bin", clean)
    print(f"Frozen positions: {len(frozen):,}; overlap: {report['overlap_positions']:,}; unseen: {report['clean_positions']:,}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--eval", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--positions", type=int, required=True)
    p.add_argument("--files", type=int, required=True)
    p.add_argument("--chunk", type=int, default=262_144)
    p.add_argument("--eval-sha256")
    args = p.parse_args()
    if min(args.positions, args.files, args.chunk) <= 0:
        p.error("positions, files and chunk must be positive")
    audit(args.input, args.eval, args.out, args.positions, args.files, args.chunk, args.eval_sha256)


if __name__ == "__main__":
    main()
