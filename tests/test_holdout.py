import hashlib
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from audit_holdout import Holdout, audit, malformed, read_records, reflected


def position(pawn, score=0, stm=0, clock=0):
    return struct.pack("<Q16shBBHBB", (1 << 4) | (1 << 60) | (1 << pawn), b"\x05\x0b" + b"\x00" * 14,
                       score, 1, stm, 3, clock, 1)


class HoldoutTest(unittest.TestCase):
    def test_exact_features_ignore_labels_and_clocks_but_not_turn(self):
        db = Holdout(position(8) + position(10, stm=1))
        r, w = read_records(position(8, score=900, clock=12) + position(10) + position(10, stm=1))
        hits, count = db.compare(r, w)
        self.assertEqual(hits.tolist(), [0, 1])
        self.assertEqual(count, 2)

    def test_color_reflection_is_equivalent(self):
        fixed = struct.pack("<Q16shBBHBB", (1 << 4) | (1 << 60) | (1 << 51), b"\x65\x0b" + b"\x00" * 14,
                            -10, 1, 1, 3, 0, 1)
        data = position(11)
        r, w = read_records(data)
        comparison, v = read_records(fixed)
        self.assertEqual(reflected(w)[0, :3].tolist(), v[0, :3].tolist())
        db = Holdout(data + fixed)
        hits, count = db.compare(comparison, v)
        self.assertEqual(sorted(hits.tolist()), [0, 1])
        self.assertEqual(count, 1)

    def test_validation_rejects_invalid_score_turn_and_pieces(self):
        bad = bytearray(position(8))
        bad[8] = 0xF5
        r, w = read_records(position(8) + position(8, score=-32768) + position(8, stm=2) + bad)
        self.assertEqual(malformed(r, w).tolist(), [False, True, True, True])
        with self.assertRaisesRegex(ValueError, "record byte count"):
            read_records(b"a")
        with self.assertRaisesRegex(ValueError, "not unique"):
            Holdout(position(8) + position(8, score=4))

    def test_audit_preserves_frozen_and_executes_count_hash_and_overlap_checks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            train = root / "fishnet-synthetic.bin"
            eval_path = root / "frozen.bin"
            out = root / "out"
            frozen = position(8) + position(9) + position(10)
            train.write_bytes(position(8, score=-3) + position(8, score=5) + position(11))
            eval_path.write_bytes(frozen)
            with self.assertRaisesRegex(ValueError, "mounted data"):
                audit(root, eval_path, out, 4, 1, 2)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                audit(root, eval_path, out, 3, 1, 2, "unknown")
            audit(root, eval_path, out, 3, 1, 2)
            report = json.loads((out / "holdout-audit.json").read_text())
            self.assertEqual(report["clean_positions"], 2)
            self.assertEqual(report["files"][0]["overlapping_training_rows"], 2)
            self.assertEqual(report["files"][0]["sha256"], hashlib.sha256(train.read_bytes()).hexdigest())
            self.assertEqual(eval_path.read_bytes(), frozen)
            self.assertEqual((out / "eval-g5-unseen.bin").read_bytes(), position(9) + position(10))


if __name__ == "__main__":
    unittest.main()
