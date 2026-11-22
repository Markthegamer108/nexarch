#!/usr/bin/env python3
import argparse
import math
import os
import random
import shlex
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import chess
import chess.engine

OPENINGS = [
    "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6", "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4 f3d4 g8f6 b1c3 a7a6",
    "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6", "d2d4 g8f6 c2c4 g7g6 b1c3 f8g7 e2e4 d7d6",
    "e2e4 e7e6 d2d4 d7d5 b1c3 g8f6", "e2e4 c7c6 d2d4 d7d5 b1c3 d5e4 c3e4 c8f5",
    "c2c4 e7e5 b1c3 g8f6 g1f3 b8c6", "g1f3 d7d5 g2g3 g8f6 f1g2 e7e6",
    "d2d4 g8f6 c2c4 e7e6 b1c3 f8b4", "e2e4 e7e5 g1f3 b8c6 f1c4 f8c5",
    "e2e4 d7d6 d2d4 g8f6 b1c3 g7g6", "d2d4 d7d5 c2c4 c7c6 g1f3 g8f6 b1c3 d5c4",
    "e2e4 c7c5 b1c3 b8c6 g2g3 g7g6", "d2d4 g8f6 c2c4 c7c5 d4d5 e7e6",
    "e2e4 e7e5 f2f4 e5f4 g1f3 g7g5", "d2d4 f7f5 g2g3 g8f6 f1g2 e7e6",
    "e2e4 g8f6 e4e5 f6d5 d2d4 d7d6", "e2e4 e7e5 g1f3 g8f6 f3e5 d7d6",
    "c2c4 c7c5 b1c3 b8c6 g2g3 g7g6", "d2d4 g8f6 g1f3 e7e6 c1g5 c7c5",
    "e2e4 c7c5 g1f3 b8c6 d2d4 c5d4 f3d4 g7g6", "e2e4 c7c5 g1f3 e7e6 d2d4 c5d4 f3d4 a7a6",
    "d2d4 d7d5 g1f3 g8f6 c1f4 e7e6 e2e3 c7c5", "d2d4 g8f6 c2c4 e7e6 g1f3 b7b6",
    "e2e4 e7e5 g1f3 b8c6 d2d4 e5d4 f3d4 g8f6", "e2e4 d7d5 e4d5 d8d5 b1c3 d5a5",
    "c2c4 g8f6 b1c3 e7e6 e2e4 d7d5", "d2d4 g8f6 c2c4 g7g6 g2g3 f8g7 f1g2 d7d5",
    "e2e4 c7c6 d2d4 d7d5 e4e5 c8f5", "e2e4 e7e6 d2d4 d7d5 e4e5 c7c5",
    "d2d4 d7d5 c2c4 d5c4 g1f3 g8f6 e2e3 e7e6", "g1f3 g8f6 c2c4 g7g6 b1c3 f8g7",
]


def load_book(path):
    lines = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if raw and not raw.startswith("#"):
                lines.append(raw)
    return lines


def start_board(entry):
    if "/" in entry:
        return chess.Board(" ".join(entry.split()[:4]) + " 0 1")
    board = chess.Board()
    for mv in entry.split():
        board.push_uci(mv)
    return board


def elo(score):
    score = min(max(score, 1e-6), 1 - 1e-6)
    return -400 * math.log10(1 / score - 1)


def llr(w, d, l, elo0, elo1):
    n = w + d + l
    if n == 0 or w == 0 or l == 0:
        return 0.0
    s = (w + d / 2) / n
    var = (w * (1 - s) ** 2 + d * (0.5 - s) ** 2 + l * s ** 2) / n
    if var <= 0:
        return 0.0
    s0, s1 = 1 / (1 + 10 ** (-elo0 / 400)), 1 / (1 + 10 ** (-elo1 / 400))
    return n * (s1 - s0) * (2 * s - s0 - s1) / (2 * var)


class Player:
    def __init__(self, command, options, name):
        parts = shlex.split(command, posix=False)
        parts[0] = shutil.which(parts[0]) or parts[0]
        self.engine = chess.engine.SimpleEngine.popen_uci(parts, timeout=60)
        if options:
            self.engine.configure(options)
        self.name = name

    def close(self):
        try:
            self.engine.quit()
        except Exception:
            self.engine.close()


def parse_options(pairs):
    options = {}
    for pair in pairs or []:
        key, _, value = pair.partition("=")
        options[key] = value
    return options


class EngineFailure(Exception):
    def __init__(self, side):
        super().__init__(f"engine playing {'white' if side == chess.WHITE else 'black'} failed")
        self.side = side


def play_game(white, black, opening, args, game_id):
    board = start_board(opening)
    base, inc = args.base, args.inc
    clocks = {chess.WHITE: base, chess.BLACK: base}
    good, draw_run = {chess.WHITE: 0, chess.BLACK: 0}, 0
    while not board.is_game_over(claim_draw=True) and board.ply() < 500:
        mover = white if board.turn == chess.WHITE else black
        if args.nodes:
            limit = chess.engine.Limit(nodes=args.nodes)
        else:
            limit = chess.engine.Limit(white_clock=clocks[chess.WHITE], black_clock=clocks[chess.BLACK],
                                       white_inc=inc, black_inc=inc)
        t0 = time.perf_counter()
        try:
            result = mover.engine.play(board, limit, info=chess.engine.INFO_SCORE, game=game_id)
        except (chess.engine.EngineError, chess.engine.EngineTerminatedError, TimeoutError) as exc:
            raise EngineFailure(board.turn) from exc
        spent = time.perf_counter() - t0
        if not args.nodes:
            clocks[board.turn] -= spent
            if clocks[board.turn] < 0:
                return ("0-1" if board.turn == chess.WHITE else "1-0"), board.ply()
            clocks[board.turn] += inc
        if result.move is None:
            break
        score = result.info.get("score")
        if score is not None:
            cp = score.pov(board.turn).score(mate_score=100000)
            good[board.turn] = good[board.turn] + 1 if cp >= args.resign else 0
            good[not board.turn] = good[not board.turn] + 1 if cp <= -args.resign else 0
            draw_run = draw_run + 1 if abs(cp) <= 10 and board.ply() >= 80 else 0
        board.push(result.move)
        for side in (chess.WHITE, chess.BLACK):
            if good[side] >= 8:
                return ("1-0" if side == chess.WHITE else "0-1"), board.ply()
        if draw_run >= 12:
            return "1/2-1/2", board.ply()
    outcome = board.outcome(claim_draw=True)
    return (outcome.result() if outcome else "1/2-1/2"), board.ply()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--a", required=True, help="engine A command (the one being measured)")
    ap.add_argument("--b", required=True, help="engine B command (the opponent)")
    ap.add_argument("--a-opt", action="append", help="UCI option for A, e.g. EvalFile=nets/x.nnue")
    ap.add_argument("--b-opt", action="append", help="UCI option for B, e.g. UCI_Elo=1500")
    ap.add_argument("--games", type=int, default=40)
    ap.add_argument("--tc", default="10+0.1", help="seconds+increment per game")
    ap.add_argument("--nodes", type=int, default=0, help="fixed nodes per move instead of a clock")
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--book", help="file of openings (UCI move lines or EPD); default: built-in list")
    ap.add_argument("--resign", type=int, default=800)
    ap.add_argument("--sprt", nargs=2, type=float, metavar=("ELO0", "ELO1"))
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    args.base, _, inc = args.tc.partition("+")
    args.base, args.inc = float(args.base), float(inc or 0)

    openings = load_book(args.book) if args.book else OPENINGS
    random.Random(args.seed).shuffle(openings)
    a_opts, b_opts = parse_options(args.a_opt), parse_options(args.b_opt)
    lock = threading.Lock()
    stats = {"w": 0, "d": 0, "l": 0, "done": 0, "crash_a": 0, "crash_b": 0}
    stop = threading.Event()
    local = threading.local()
    lower, upper = math.log(0.05 / 0.95), math.log(0.95 / 0.05)
    start = time.time()

    def players():
        if not hasattr(local, "a"):
            local.a = Player(args.a, a_opts, "A")
            local.b = Player(args.b, b_opts, "B")
            with lock:
                created.append(local.a)
                created.append(local.b)
        return local.a, local.b

    def replace(which):
        old = getattr(local, which)
        old.close()
        setattr(local, which, Player(args.a if which == "a" else args.b, a_opts if which == "a" else b_opts, which.upper()))
        with lock:
            created.append(getattr(local, which))

    created = []

    def run(i):
        if stop.is_set():
            return
        a, b = players()
        opening = openings[(i // 2) % len(openings)]
        a_white = i % 2 == 0
        try:
            res, plies = play_game(a if a_white else b, b if a_white else a, opening, args, game_id=i)
        except EngineFailure as failure:
            a_failed = (failure.side == chess.WHITE) == a_white
            res = ("0-1" if failure.side == chess.WHITE else "1-0")
            with lock:
                stats["crash_a" if a_failed else "crash_b"] += 1
                print(f"game {i}: engine {'A' if a_failed else 'B'} failed ({failure.__cause__!r}); restarting it", flush=True)
            replace("a" if a_failed else "b")
        a_score = {"1-0": 1.0, "0-1": 0.0}.get(res, 0.5)
        if not a_white:
            a_score = 1 - a_score
        with lock:
            stats["w" if a_score == 1 else "l" if a_score == 0 else "d"] += 1
            stats["done"] += 1
            w, d, l, n = stats["w"], stats["d"], stats["l"], stats["done"]
            s = (w + d / 2) / n
            line = f"game {n:5d}: A +{w} ={d} -{l}  score {100 * s:5.1f}%  Elo {elo(s):+6.0f}  ({time.time() - start:.0f}s)"
            if args.sprt:
                ratio = llr(w, d, l, *args.sprt)
                line += f"  LLR {ratio:+.2f} [{lower:.2f}, {upper:.2f}]"
                if ratio >= upper or ratio <= lower:
                    stop.set()
            if n % max(1, args.concurrency) == 0 or n == args.games or stop.is_set():
                print(line, flush=True)

    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            list(pool.map(run, range(args.games)))
    finally:
        for p in created:
            p.close()

    w, d, l = stats["w"], stats["d"], stats["l"]
    n = max(1, w + d + l)
    s = (w + d / 2) / n
    var = (w * (1 - s) ** 2 + d * (0.5 - s) ** 2 + l * s ** 2) / n
    margin = 1.96 * math.sqrt(var / n)
    if w == n or l == n:
        estimate = "Elo n/a (one side won every game; use a stronger or weaker opponent)"
    else:
        estimate = f"Elo {elo(s):+.0f} (95%: {elo(s - margin):+.0f} .. {elo(s + margin):+.0f})"
    print(f"RESULT: A +{w} ={d} -{l}  score {100 * s:.1f}%  {estimate}  "
          f"engine failures A {stats['crash_a']} B {stats['crash_b']}", flush=True)
    if args.sprt:
        ratio = llr(w, d, l, *args.sprt)
        verdict = "PASSED (keep the change)" if ratio >= upper else "FAILED (reject)" if ratio <= lower else "inconclusive"
        print(f"SPRT [{args.sprt[0]:g}, {args.sprt[1]:g}]: LLR {ratio:+.2f} -> {verdict}", flush=True)


if __name__ == "__main__":
    main()
    sys.stdout.flush()
    os._exit(0)
