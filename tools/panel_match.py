#!/usr/bin/env python3
import argparse
import hashlib
import json
import math
import os
import platform
import random
import re
import sqlite3
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, closing
from pathlib import Path

import chess
import chess.engine


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def opening_pairs(path, count, seed):
    books = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        board = chess.Board(line)
        if not board.is_valid() or board.is_game_over(claim_draw=True):
            raise ValueError(f"invalid starting position: {line}")
        books.setdefault(" ".join(board.fen().split()[:4]), board.fen())
    if len(books) < count:
        raise ValueError(f"only {len(books)} unique openings for {count} pairs")
    return random.Random(seed).sample(list(books.values()), count)


def opponents(path):
    entries = json.loads(path.read_text(encoding="utf-8"))["engines"]
    seen = set()
    result = []
    for entry in entries:
        name, executable = entry["name"], Path(entry["path"]).resolve(strict=True)
        if name in seen or not os.access(executable, os.X_OK):
            raise ValueError(f"invalid panel entry: {name}")
        seen.add(name)
        options = {}
        for line in entry["init"]:
            m = re.fullmatch(r"setoption name (.+?) value (.+)", line)
            if not m:
                raise ValueError(f"invalid UCI option for {name}: {line}")
            key, value = m.groups()
            options[key] = value.replace("{dir}", str(executable.parent))
        if name == "Maia 1900":
            options.update(Backend="eigen", MinibatchSize=1)
        result.append((name, executable, options))
    return result


def nx_player(name, executable, network):
    return name, executable, {"Threads": 1, "Hash": 16, "UCI_LimitStrength": False, "EvalFile": str(network)}


def start_engine(stack, spec, cpu, timeout):
    name, executable, options = spec
    cmd = [str(executable)] if cpu is None else ["taskset", "-c", str(cpu), str(executable)]
    engine = stack.enter_context(chess.engine.SimpleEngine.popen_uci(cmd, cwd=executable.parent, timeout=timeout))
    engine.configure(options)
    engine.ping()
    print(f"{name}: {engine.id.get('name', 'unidentified UCI engine')}", flush=True)
    return engine


def play(white, black, fen, seconds, nodes, max_plies):
    board = chess.Board(fen)
    limit = chess.engine.Limit(nodes=nodes) if nodes else chess.engine.Limit(time=seconds)
    moves = []
    elapsed = {chess.WHITE: 0.0, chess.BLACK: 0.0}
    game = object()
    outcome = board.outcome(claim_draw=True)
    while outcome is None and len(moves) < max_plies:
        mover = white if board.turn == chess.WHITE else black
        start = time.monotonic()
        result = mover.play(board, limit, game=game)
        elapsed[board.turn] += time.monotonic() - start
        if result.move not in board.legal_moves:
            raise RuntimeError(f"illegal or missing move from {mover.id} on {board.fen()}: {result.move}")
        moves.append(result.move.uci())
        board.push(result.move)
        outcome = board.outcome(claim_draw=True)
    return {"result": outcome.result() if outcome else "1/2-1/2",
            "reason": outcome.termination.name if outcome else "PLY_LIMIT",
            "moves": moves, "white_seconds": elapsed[chess.WHITE], "black_seconds": elapsed[chess.BLACK]}


def a_points(game, a_white):
    points = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}[game["result"]]
    return points if a_white else 1.0 - points


def configure_db(path, design):
    data = json.dumps(design, sort_keys=True)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS design (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS pairs (opponent TEXT, opening INTEGER, value TEXT NOT NULL, PRIMARY KEY(opponent, opening))")
        previous = db.execute("SELECT value FROM design WHERE id=1").fetchone()
        if previous is None:
            db.execute("INSERT INTO design VALUES (1, ?)", (data,))
        elif previous[0] != data:
            raise ValueError("saved benchmark design differs; use a fresh output directory")


def matchup(path, foe, own, openings, args, cpu):
    with closing(sqlite3.connect(path, timeout=20)) as db:
        done = {i for i, in db.execute("SELECT opening FROM pairs WHERE opponent=?", (foe[0],))}
        if len(done) == len(openings):
            return
        with ExitStack() as stack:
            rivals = {spec[0]: start_engine(stack, spec, cpu, args.timeout) for spec in (foe, *own)}
            opponent = rivals[foe[0]]
            for i, fen in enumerate(openings):
                if i in done:
                    continue
                arms = own if i % 2 == 0 else own[::-1]
                result = {}
                for name, _, _ in arms:
                    a = rivals[name]
                    first = i % 2 == 0
                    for a_white in (first, not first):
                        result.setdefault(name, {})["white" if a_white else "black"] = play(
                            a if a_white else opponent, opponent if a_white else a,
                            fen, args.movetime / 1000, args.nodes, args.max_plies)
                with db:
                    db.execute("INSERT INTO pairs VALUES (?, ?, ?)", (foe[0], i, json.dumps(result)))
                print(f"{foe[0]}: completed opening pair {i + 1}/{len(openings)}", flush=True)


def score_ci(values, lo=0.0, hi=1.0):
    if not values:
        raise ValueError("confidence interval needs observations")
    mean = math.fsum(values) / len(values)
    radius = (hi - lo) * math.sqrt(math.log(2 / 0.05) / (2 * len(values)))
    return mean, [max(lo, mean - radius), min(hi, mean + radius)]


def elo(score):
    if 0 < score < 1:
        return 400 * math.log10(score / (1 - score))
    return None


def results(path, foes, arms, n_pairs):
    with closing(sqlite3.connect(path)) as db:
        rows = {(name, i): json.loads(row) for name, i, row in db.execute("SELECT opponent, opening, value FROM pairs")}
    if len(rows) != len(foes) * n_pairs:
        raise ValueError("incomplete benchmark; no result published")
    scores = {name: [] for name in arms}
    panel = []
    labels = ("wins", "draws", "losses")
    for opponent in foes:
        table = {"opponent": opponent}
        for name in arms:
            pairs = []
            counts = [0, 0, 0]
            ply_limits = 0
            for i in range(n_pairs):
                games = rows[opponent, i][name]
                points = [a_points(games[side], side == "white") for side in ("white", "black")]
                for points_i in points:
                    counts[2 - int(points_i * 2)] += 1
                pairs.append(sum(points) / 2)
                ply_limits += sum(game["reason"] == "PLY_LIMIT" for game in games.values())
            scores[name].append(pairs)
            s, ci = score_ci(pairs)
            table[name] = {**dict(zip(labels, counts)), "score": s, "score_95_ci": ci,
                           "elo": elo(s), "elo_95_ci": list(map(elo, ci)), "ply_limit_draws": ply_limits}
        panel.append(table)
    summary = {}
    if len(arms) == 2:
        delta = [math.fsum(a[i] - b[i] for a, b in zip(scores[arms[0]], scores[arms[1]])) / len(foes) for i in range(n_pairs)]
        mean, ci = score_ci(delta, -1.0, 1.0)
        summary = {"mean_candidate_minus_incumbent": mean, "score_delta_95_ci": ci}
    return {"ci": "95% Hoeffding bound across unique color-reversed opening pairs; null Elo endpoint means unbounded",
            "openings": n_pairs, "opponents": panel, "comparison": summary}


def atomic_json(path, data):
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            json.dump(data, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)


def describe(spec):
    name, executable, options = spec
    artifacts = {str(executable): sha256(executable)}
    wrapper_target = executable.parent.parent / "real" / executable.name
    if wrapper_target.is_file():
        artifacts[str(wrapper_target)] = sha256(wrapper_target)
    for value in options.values():
        if isinstance(value, str) and Path(value).is_absolute():
            artifacts[value] = sha256(Path(value))
    return {"name": name, "options": options, "sha256": artifacts}


def run(args):
    exe = args.engine.resolve(strict=True)
    candidate = nx_player("candidate", exe, args.candidate.resolve(strict=True))
    gen4 = nx_player("gen4", exe, args.incumbent.resolve(strict=True))
    own = [candidate] if args.direct else [candidate, gen4]
    foes = [gen4] if args.direct else opponents(args.panel)
    if not args.direct and len(foes) != args.expect:
        raise ValueError(f"expected {args.expect} panel entries, got {len(foes)}")
    names = [spec[0] for spec in foes]
    labels = [spec[0] for spec in own]
    if set(names) & set(labels):
        raise ValueError("opponent and contender names collide")
    cpus = sorted(os.sched_getaffinity(0))
    concurrency = min(args.concurrency, len(cpus), len(foes))
    openings = opening_pairs(args.book, args.pairs, args.seed)
    topology = Path("/proc/cpuinfo").read_text(encoding="utf-8")
    cpu_name = next((line.split(":", 1)[1].strip() for line in topology.splitlines() if line.startswith("model name")), platform.machine())
    design = {"movetime_ms": args.movetime, "nodes": args.nodes, "seed": args.seed, "max_plies": args.max_plies,
              "timeout_seconds": args.timeout, "pairs": args.pairs, "cpus": cpus[:concurrency], "cpu_model": cpu_name,
              "system": platform.platform(), "python": platform.python_version(), "chess": chess.__version__,
              "book_sha256": sha256(args.book), "opponents": [describe(x) for x in foes], "arms": [describe(x) for x in own],
              "openings_sha256": hashlib.sha256("\n".join(openings).encode()).hexdigest()}
    args.out.mkdir(parents=True, exist_ok=True)
    db = args.out / "matches.sqlite3"
    configure_db(db, design)
    atomic_json(args.out / "design.json", design)

    def work(worker):
        for foe in foes[worker::concurrency]:
            matchup(db, foe, own, openings, args, cpus[worker])

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(work, range(concurrency)))
    report = results(db, names, labels, args.pairs)
    atomic_json(args.out / "results.json", report)
    print(f"Verified {len(foes)} opponents, {args.pairs} opening pairs per arm; results: {args.out / 'results.json'}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--engine", type=Path, default=Path("engine/nexarch"))
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--incumbent", type=Path, required=True)
    p.add_argument("--panel", type=Path, default=Path("nets/graders.json"))
    p.add_argument("--book", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--pairs", type=int, default=24)
    p.add_argument("--movetime", type=int, default=200)
    p.add_argument("--nodes", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--seed", type=int, default=20261124)
    p.add_argument("--max-plies", type=int, default=600)
    p.add_argument("--timeout", type=float, default=15)
    p.add_argument("--expect", type=int, default=33)
    p.add_argument("--direct", action="store_true")
    args = p.parse_args()
    if min(args.movetime, args.pairs, args.concurrency, args.max_plies, args.timeout, args.expect) <= 0 or args.nodes < 0:
        p.error("positive parameters required; nodes may be zero for timed play")
    run(args)


if __name__ == "__main__":
    main()
