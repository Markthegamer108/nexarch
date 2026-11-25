#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Mark Ivanovskyy
"""Small HTTP relay for anonymous human-vs-human Nexarch games.

Run on the OCI server:
    python gui/relay_server.py --host 0.0.0.0 --port 8080

The Arena client talks to /api/room, /api/join, /api/state and /api/move.
Rooms are in memory and disappear after 24 hours. No accounts, emails or hardware IDs.
"""
import argparse
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import chess

ROOMS = {}
LOCK = threading.RLock()
MAX_AGE = 24 * 3600
GAMES = None


class Room:
    def __init__(self, name, color):
        self.id = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))
        self.board = chess.Board()
        self.tokens = {}
        self.names = {"w": "", "b": ""}
        self.created = time.time()
        self.last = time.time()
        self.result = ""
        self.reason = ""
        self.tokens[color] = secrets.token_urlsafe(18)
        self.names[color] = name[:32]
        self.colors = {self.tokens[color]: color}

    def join(self, name):
        color = "b" if self.names["w"] else "w"
        if self.names[color]:
            raise ValueError("room is full")
        token = secrets.token_urlsafe(18)
        self.tokens[color] = token
        self.names[color] = (name or "Player")[:32]
        self.colors[token] = color
        return token, color

    def snapshot(self, since=0):
        moves = [m.uci() for m in self.board.move_stack]
        outcome = self.board.outcome(claim_draw=True)
        status = "playing"
        if outcome:
            status = "finished"
            self.result = outcome.result()
            self.reason = outcome.termination.name.lower()
        if self.result and not outcome:
            status = "finished"
            self.reason = self.reason or "agreed"
        return {
            "room": self.id,
            "fen": self.board.fen(),
            "turn": "w" if self.board.turn == chess.WHITE else "b",
            "moves": moves[since:],
            "count": len(moves),
            "white": self.names["w"],
            "black": self.names["b"],
            "status": status,
            "result": self.result,
            "reason": self.reason,
            "check": self.board.is_check(),
        }

    def move(self, token, uci):
        color = self.colors.get(token)
        if not color:
            raise ValueError("bad token")
        if self.names["w"] and self.names["b"] and color != ("w" if self.board.turn == chess.WHITE else "b"):
            raise ValueError("not your turn")
        try:
            mv = chess.Move.from_uci(uci)
        except Exception:
            raise ValueError("bad move")
        if mv not in self.board.legal_moves:
            raise ValueError("illegal move")
        self.board.push(mv)
        self.last = time.time()
        return self.snapshot()


def cleanup():
    now = time.time()
    with LOCK:
        for key in [k for k, r in ROOMS.items() if now - r.last > MAX_AGE]:
            del ROOMS[key]


class Handler(BaseHTTPRequestHandler):
    server_version = "NexarchRelay/0.1"

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw or b"{}")
        except Exception:
            return {}

    def json(self, data, code=200):
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.cors()
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/health"):
            self.json({"ok": True, "rooms": len(ROOMS)})
            return
        if self.path.startswith("/api/state"):
            from urllib.parse import parse_qs, urlparse
            q = parse_qs(urlparse(self.path).query)
            rid = (q.get("room") or [""])[0].upper()
            since = int((q.get("since") or ["0"])[0] or 0)
            with LOCK:
                room = ROOMS.get(rid)
                if not room:
                    self.json({"error": "room not found"}, 404)
                    return
                room.last = time.time()
                self.json(room.snapshot(since))
            return
        self.json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path.startswith("/api/room"):
            body = self.body()
            color = "b" if body.get("color") == "b" else "w"
            with LOCK:
                cleanup()
                room = Room(body.get("name") or "Player", color)
                ROOMS[room.id] = room
                self.json({"room": room.id, "token": room.tokens[color], "color": color, "state": room.snapshot()})
            return
        if self.path.startswith("/api/join"):
            body = self.body()
            rid = (body.get("room") or "").upper()
            with LOCK:
                room = ROOMS.get(rid)
                if not room:
                    self.json({"error": "room not found"}, 404)
                    return
                try:
                    token, color = room.join(body.get("name") or "Player")
                except ValueError as exc:
                    self.json({"error": str(exc)}, 409)
                    return
                self.json({"room": room.id, "token": token, "color": color, "state": room.snapshot()})
            return
        if self.path.startswith("/collect"):
            body = self.body()
            if not isinstance(body, dict) or "pgn" not in body:
                self.json({"error": "expected a game object"}, 400)
                return
            line = json.dumps({"received": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "game": body}) + "\n"
            try:
                if GAMES:
                    with open(GAMES, "a") as f:
                        f.write(line)
                else:
                    print(line, end="")
            except Exception as exc:
                self.json({"error": str(exc)}, 500)
                return
            self.json({"ok": True})
            return
        if self.path.startswith("/api/end"):
            body = self.body()
            with LOCK:
                room = ROOMS.get((body.get("room") or "").upper())
                if not room:
                    self.json({"error": "room not found"}, 404)
                    return
                if room.colors.get(body.get("token") or "") is None:
                    self.json({"error": "bad token"}, 400)
                    return
                room.result = (body.get("result") or "*")[:8]
                room.last = time.time()
                self.json({"ok": True, "room": room.id, "result": room.result})
            return
        if self.path.startswith("/api/move"):
            body = self.body()
            with LOCK:
                room = ROOMS.get((body.get("room") or "").upper())
                if not room:
                    self.json({"error": "room not found"}, 404)
                    return
                try:
                    state = room.move(body.get("token") or "", body.get("uci") or "")
                except ValueError as exc:
                    self.json({"error": str(exc)}, 400)
                    return
                self.json(state)
            return
        self.json({"error": "not found"}, 404)

    def log_message(self, *args):
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--data", default="", help="append anonymous games to this file")
    args = ap.parse_args()
    global GAMES
    GAMES = args.data
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Nexarch relay on http://{args.host}:{args.port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
