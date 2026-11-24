import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from panel_match import a_points, elo, opening_pairs, score_ci


class PanelTest(unittest.TestCase):
    def test_opening_pairs_dedupes_positions_and_rejects_a_short_book(self):
        with tempfile.TemporaryDirectory() as d:
            book = Path(d) / "book.epd"
            book.write_text(
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1\n"
                "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 4 9\n"
                "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1\n"
            )
            openings = opening_pairs(book, 2, 7)
            self.assertEqual(len(openings), 2)
            self.assertEqual(len(set(openings)), 2)
            with self.assertRaisesRegex(ValueError, "only 2 unique openings"):
                opening_pairs(book, 3, 7)

    def test_results_are_from_the_contenders_point_of_view(self):
        self.assertEqual(a_points({"result": "1-0"}, True), 1.0)
        self.assertEqual(a_points({"result": "1-0"}, False), 0.0)
        self.assertEqual(a_points({"result": "0-1"}, True), 0.0)
        self.assertEqual(a_points({"result": "1/2-1/2"}, False), 0.5)

    def test_intervals_and_elo_endpoints(self):
        mean, interval = score_ci([0.5] * 16)
        self.assertEqual(mean, 0.5)
        self.assertLess(interval[0], 0.5)
        self.assertGreater(interval[1], 0.5)
        self.assertEqual(elo(0.5), 0.0)
        self.assertIsNone(elo(0.0))
        self.assertIsNone(elo(1.0))
        mean, interval = score_ci([1.0, -0.5, 0.0], -1.0, 1.0)
        self.assertAlmostEqual(mean, 1.0 / 6.0)
        self.assertLessEqual(interval[0], mean)
        self.assertGreaterEqual(interval[1], mean)


if __name__ == "__main__":
    unittest.main()
