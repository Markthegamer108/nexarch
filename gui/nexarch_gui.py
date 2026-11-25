#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Mark Ivanovskyy
"""Interactive web chess: play vs Nexarch/any engine, or watch engine matches.

Usage:
  python gui/nexarch_gui.py [--port 8765] [--host 127.0.0.1] [--engines gui/engines.json] [--open]
Open http://HOST:PORT in a browser. The default binds to localhost. Binding to 0.0.0.0
exposes the board on the LAN; do that only on a network you trust.
"""
import argparse
import http.server
import json
import mimetypes
import os
import pathlib
import random
import shlex
import shutil
import socket
import socketserver
import sys
import threading
import time
import urllib.parse
import uuid
import urllib.request

import chess
import chess.engine
import chess.pgn
import chess.svg

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_ENGINES = str(HERE / "engines.json")
CUTECHESS_ENGINES = os.path.expanduser("~/.config/cutechess/engines.json")
PIECE_DIR = HERE / "pieces"
CONFIG_DIR = pathlib.Path(os.path.expanduser("~/.config/nexarch"))
DATA_DIR = pathlib.Path(os.path.expanduser("~/.local/share/nexarch"))
GUI_CONFIG = CONFIG_DIR / "gui.json"
GAMES_FILE = DATA_DIR / "games.jsonl"
TELEMETRY_URL = "http://158.180.55.245:8090/collect"
PIECE_FILES = {"klt45.svg", "qlt45.svg", "rlt45.svg", "blt45.svg", "nlt45.svg", "plt45.svg",
               "kdt45.svg", "qdt45.svg", "rdt45.svg", "bdt45.svg", "ndt45.svg", "pdt45.svg"}
OPENINGS = [
    "e2e4 e7e5 g1f3 b8c6 f1b5 a7a6", "d2d4 d7d5 c2c4 e7e6 b1c3 g8f6",
    "e2e4 c7c5 g1f3 d7d6 d2d4 c5d4", "g1f3 d7d5 g2g3 g8f6 f1g2 e7e6",
]


def load_engines(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        return []
    base = pathlib.Path(path).resolve().parent
    out = []
    for e in data:
        opts = {}
        for o in e.get("options", []):
            opts[o["name"]] = o.get("value")
        command = str(e.get("command", ""))
        parts = shlex.split(command)
        if parts and not os.path.isabs(parts[0]):
            parts[0] = str(base / parts[0])
        command = shlex.join(parts) if parts else command
        wd = str(e.get("workingDirectory", ""))
        if wd and not os.path.isabs(wd):
            wd = str(base / wd)
        out.append({
            "name": e.get("name", "Engine"),
            "command": command,
            "workingDirectory": wd,
            "protocol": e.get("protocol", "uci"),
            "options": opts,
        })
    return out


MIN_ELO = 1320
MAX_ELO = 3190
MIN_STRENGTH = 10
MAX_STRENGTH = 100


def clamp_strength(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = MAX_STRENGTH
    return max(MIN_STRENGTH, min(MAX_STRENGTH, value))


def strength_for_elo(elo):
    try:
        elo = max(MIN_ELO, min(MAX_ELO, int(elo)))
    except (TypeError, ValueError):
        return MAX_STRENGTH
    return clamp_strength(round(MIN_STRENGTH + (elo - MIN_ELO) * (MAX_STRENGTH - MIN_STRENGTH) / (MAX_ELO - MIN_ELO)))


def elo_for_strength(percent):
    percent = clamp_strength(percent)
    return round(MIN_ELO + (percent - MIN_STRENGTH) * (MAX_ELO - MIN_ELO) / (MAX_STRENGTH - MIN_STRENGTH))


def skill_for_strength(percent):
    return max(0, min(20, round(clamp_strength(percent) / 5)))


def read_settings():
    out = {"telemetry": False, "endpoint": "", "anonymous_id": "", "threads": 1, "hash": 64,
           "skill": 20, "strength": MAX_STRENGTH, "elo": MAX_ELO}
    try:
        data = json.loads(GUI_CONFIG.read_text())
        out.update({k: data[k] for k in out if k in data})
        if "strength" not in data and "elo" in data:
            out["strength"] = strength_for_elo(data["elo"])
    except Exception:
        pass
    out["endpoint"] = TELEMETRY_URL
    if not out["anonymous_id"]:
        out["anonymous_id"] = uuid.uuid4().hex
        save_settings(out)
    return out


def save_settings(data):
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        tmp = GUI_CONFIG.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1) + "\n")
        os.replace(tmp, GUI_CONFIG)
    except Exception:
        pass


def pgn_text(st):
    game = chess.pgn.Game.from_board(st.board)
    game.headers["Event"] = "Nexarch Chess"
    game.headers["Site"] = "Nexarch"
    game.headers["Date"] = time.strftime("%Y.%m.%d")
    game.headers["White"] = st.white_name or "Human"
    game.headers["Black"] = st.black_name or "Human"
    game.headers["Result"] = st.result or "*"
    return str(game)


def upload_game(endpoint, line):
    try:
        req = urllib.request.Request(endpoint, data=line.encode(), headers={"Content-Type": "application/json",
                                                                           "User-Agent": "NexarchGUI"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        pass


def record_game(st):
    with st.lock:
        if st.recorded or not st.moves or st.status not in ("finished", "between_games"):
            return
        st.recorded = True
        pgn = pgn_text(st)
        result = st.result
        enabled = st.telemetry
        endpoint = st.endpoint
        anon = st.anonymous_id
    if not enabled:
        return
    line = json.dumps({"pgn": pgn, "result": result, "engine": "Nexarch", "anonymous_id": anon,
                       "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}) + "\n"
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(GAMES_FILE, "a") as f:
            f.write(line)
    except Exception:
        pass
    if endpoint:
        threading.Thread(target=upload_game, args=(endpoint, line), daemon=True).start()


class State:
    def __init__(self):
        self.lock = threading.RLock()
        self.engines = []
        self.mode = "idle"          # idle | human | match
        self.fen = chess.STARTING_FEN
        self.board = chess.Board()
        self.white_name = ""
        self.black_name = ""
        self.white_human = False
        self.black_human = False
        self.status = "idle"
        self.result = ""
        self.end_reason = ""
        self.moves = []
        self.last_uci = ""
        self.stats = {"w": 0, "d": 0, "l": 0, "done": 0}
        self.current_game = 0
        self.total_games = 1
        self.tc_base = 5.0
        self.tc_inc = 0.05
        self.nodes = 0
        self.clocks = {"w": 5.0, "b": 5.0}
        self.thinking = False
        self.stop = threading.Event()
        self.thread = None
        self.run_id = 0
        self.engine_handles = {}
        self.last_error = ""
        settings = read_settings()
        self.telemetry = bool(settings["telemetry"])
        self.endpoint = TELEMETRY_URL
        self.anonymous_id = settings["anonymous_id"]
        strength = clamp_strength(settings.get("strength", MAX_STRENGTH))
        self.engine_settings = {"threads": int(settings.get("threads", 1)),
                                "hash": int(settings.get("hash", 64)),
                                "strength": strength,
                                "elo": elo_for_strength(strength),
                                "skill": skill_for_strength(strength)}
        self.engine_info = {}
        self.online = False
        self.online_room = ""
        self.online_server = ""
        self.online_color = ""
        self.online_status = ""
        self.online_names = {"w": "", "b": ""}
        self.recorded = False

    def snapshot(self):
        with self.lock:
            return {
                "mode": self.mode,
                "fen": self.fen,
                "side_to_move": "w" if self.board.turn == chess.WHITE else "b",
                "white_name": self.white_name,
                "black_name": self.black_name,
                "white_human": self.white_human,
                "black_human": self.black_human,
                "status": self.status,
                "result": self.result,
                "moves": list(self.moves),
                "stats": dict(self.stats),
                "current_game": self.current_game,
                "total_games": self.total_games,
                "tc_base": self.tc_base,
                "tc_inc": self.tc_inc,
                "nodes": self.nodes,
                "clocks": dict(self.clocks),
                "thinking": self.thinking,
                "last_error": self.last_error,
                "last_uci": self.last_uci,
                "telemetry": self.telemetry,
                "endpoint": self.endpoint,
                "engine_info": dict(self.engine_info),
                "settings": dict(self.engine_settings),
                "online": self.online,
                "online_room": self.online_room,
                "online_color": self.online_color,
                "online_server": self.online_server,
                "online_status": self.online_status,
                "online_names": dict(self.online_names),
                "legal": self.legal_map(),
                "check": self.board.is_check(),
                "termination": self.termination(),
                "end_reason": self.end_reason,
                "winner": self.winner(),
                "engines": [e["name"] for e in self.engines],
            }

    def legal_map(self):
        human_turn = (self.board.turn == chess.WHITE and self.white_human) or \
                     (self.board.turn == chess.BLACK and self.black_human)
        if not human_turn:
            return {}
        out = {}
        for mv in self.board.legal_moves:
            out.setdefault(chess.square_name(mv.from_square), []).append(chess.square_name(mv.to_square))
        return out

    def termination(self):
        outcome = self.board.outcome(claim_draw=True)
        return outcome.termination.name.lower() if outcome else ""

    def winner(self):
        outcome = self.board.outcome(claim_draw=True)
        if outcome and outcome.winner is not None:
            return "w" if outcome.winner == chess.WHITE else "b"
        return ""

    def reset_board(self):
        self.recorded = False
        self.board = chess.Board()
        self.fen = chess.STARTING_FEN
        self.moves = []
        self.last_uci = ""
        self.result = ""
        self.end_reason = ""
        self.clocks = {"w": self.tc_base, "b": self.tc_base}

    def open_engine(self, name):
        if name in self.engine_handles:
            return self.engine_handles[name]
        cfg = next((e for e in self.engines if e["name"] == name), None)
        if cfg is None or not cfg["command"]:
            raise RuntimeError(f"unknown engine: {name}")
        parts = shlex.split(cfg["command"], posix=False)
        parts[0] = shutil.which(parts[0]) or parts[0]
        wd = cfg.get("workingDirectory") or None
        eng = chess.engine.SimpleEngine.popen_uci(parts, timeout=60, cwd=wd)
        try:
            eng.configure(cfg["options"])
        except Exception:
            pass
        try:
            eng.configure({"Threads": self.engine_settings["threads"],
                           "Hash": self.engine_settings["hash"],
                           "Skill Level": self.engine_settings["skill"]})
        except Exception:
            pass
        try:
            self.apply_strength(eng)
        except Exception:
            pass
        self.engine_handles[name] = eng
        return eng

    def apply_strength(self, engine=None):
        strength = clamp_strength(self.engine_settings.get("strength", MAX_STRENGTH))
        options = {"UCI_LimitStrength": strength < MAX_STRENGTH,
                   "UCI_Elo": elo_for_strength(strength),
                   "Skill Level": skill_for_strength(strength)}
        targets = [engine] if engine is not None else list(self.engine_handles.values())
        for eng in targets:
            try:
                eng.configure(options)
            except Exception:
                pass

    def close_engines(self):
        for name, eng in list(self.engine_handles.items()):
            try:
                eng.quit()
            except Exception:
                try:
                    eng.close()
                except Exception:
                    pass
        self.engine_handles.clear()


STATE = State()
SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
ENGINES = []


def apply_online_moves(st, moves, white="", black=""):
    board = chess.Board()
    for u in moves:
        mv = chess.Move.from_uci(u)
        if mv not in board.legal_moves:
            raise ValueError(f"illegal move {u}")
        board.push(mv)
    st.board = board
    st.fen = board.fen()
    st.last_uci = board.move_stack[-1].uci() if board.move_stack else ""
    st.moves = []
    tmp = chess.Board()
    for mv in board.move_stack:
        st.moves.append(tmp.san(mv))
        tmp.push(mv)
    if white:
        st.white_name = white
    if black:
        st.black_name = black
    outcome = board.outcome(claim_draw=True)
    if outcome:
        st.status = "finished"
        st.result = outcome.result()
        st.end_reason = outcome.termination.name.lower()
    else:
        st.status = "playing"
        st.result = ""
        st.end_reason = ""


RANKINGS = {}
RANKINGS_LOCK = threading.Lock()


def fetch_json(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def rankings(site, perf):
    key = (site, perf)
    now = time.time()
    with RANKINGS_LOCK:
        if key in RANKINGS and now - RANKINGS[key][0] < 600:
            return RANKINGS[key][1]
    ua = "NexarchArena/0.1 (https://github.com/Markthegamer108/nexarch)"
    if site == "lichess":
        data = fetch_json(f"https://lichess.org/api/player/top/10/{perf}",
                          {"Accept": "application/json", "User-Agent": ua})
        rows = []
        for u in data.get("users", [])[:10]:
            p = (u.get("perfs") or {}).get(perf) or {}
            rows.append({"name": u.get("username", ""), "rating": p.get("rating", 0), "title": u.get("title", "")})
    else:
        data = fetch_json("https://api.chess.com/pub/leaderboards", {"User-Agent": ua, "Accept": "application/json"})
        keyname = {"bullet": "live_bullet", "blitz": "live_blitz", "rapid": "live_rapid",
                   "classical": "live_classical", "daily": "daily"}.get(perf, "live_blitz")
        rows = [{"name": x.get("username", ""), "rating": x.get("score", 0), "title": x.get("title", "")}
                for x in (data.get(keyname) or [])[:10]]
    out = {"site": site, "perf": perf, "rows": rows}
    with RANKINGS_LOCK:
        RANKINGS[key] = (now, out)
    return out


def session_state(handler):
    query = urllib.parse.parse_qs(urllib.parse.urlparse(handler.path).query)
    sid = (query.get("s") or [""])[0].strip()
    if not sid:
        return STATE
    with SESSIONS_LOCK:
        st = SESSIONS.get(sid)
        if st is None:
            st = State()
            st.engines = ENGINES
            SESSIONS[sid] = st
        return st


def run_engine_move(st, eng_name, board, limit):
    eng = st.open_engine(eng_name)
    res = eng.play(board, limit, info=chess.engine.INFO_SCORE)
    info = getattr(res, "info", {}) or {}
    score = info.get("score")
    with st.lock:
        st.engine_info = {
            "depth": info.get("depth", 0),
            "nodes": info.get("nodes", 0),
            "score": str(score) if score is not None else "",
            "pv": " ".join(str(m) for m in (info.get("pv") or [])[:6]),
        }
    return res


def run_match(st, my_run):
    openings = list(OPENINGS)
    random.Random(1).shuffle(openings)
    while not st.stop.is_set() and st.current_game < st.total_games:
        with st.lock:
            if st.run_id != my_run:
                return
            st.current_game += 1
            g = st.current_game
            st.reset_board()
            try:
                b = chess.Board()
                for mv in openings[(g // 2) % len(openings)].split():
                    b.push_uci(mv)
                st.board = b
                st.fen = b.fen()
                st.moves = openings[(g // 2) % len(openings)].split()
            except Exception:
                pass
            st.status = "playing"
            st.result = ""
        while not st.stop.is_set():
            with st.lock:
                if st.run_id != my_run:
                    return
                if st.board.is_game_over(claim_draw=True) or st.board.ply() >= 500:
                    break
                turn = st.board.turn
                white_is_engine = not st.white_human
                black_is_engine = not st.black_human
                mover_engine = (turn == chess.WHITE and white_is_engine) or (turn == chess.BLACK and black_is_engine)
            if not mover_engine:
                time.sleep(0.2)
                continue
            with st.lock:
                if st.run_id != my_run:
                    return
                st.thinking = True
                if st.nodes:
                    limit = chess.engine.Limit(nodes=st.nodes)
                else:
                    limit = chess.engine.Limit(white_clock=st.clocks["w"], black_clock=st.clocks["b"],
                                               white_inc=st.tc_inc, black_inc=st.tc_inc)
                eng_name = st.white_name if turn == chess.WHITE else st.black_name
                board_copy = st.board.copy()
                t0 = time.perf_counter()
            try:
                res = run_engine_move(st, eng_name, board_copy, limit)
                spent = time.perf_counter() - t0
                with st.lock:
                    if st.run_id != my_run:
                        return
                    if not st.nodes:
                        key = "w" if turn == chess.WHITE else "b"
                        st.clocks[key] -= spent
                        if st.clocks[key] < 0:
                            st.result = "0-1" if turn == chess.WHITE else "1-0"
                            st.end_reason = ("White" if turn == chess.WHITE else "Black") + " loses on time"
                            st.status = "finished"
                            st.thinking = False
                            break
                        st.clocks[key] += st.tc_inc
                    if res.move is None:
                        st.thinking = False
                        break
                    san = st.board.san(res.move)
                    st.board.push(res.move)
                    st.last_uci = res.move.uci()
                    st.fen = st.board.fen()
                    st.moves.append(san)
                    st.moves = st.moves[-40:]
                    st.thinking = False
            except Exception as e:
                with st.lock:
                    if st.run_id == my_run:
                        st.last_error = str(e)
                        st.thinking = False
                break
            time.sleep(0.05)
        with st.lock:
            if st.run_id != my_run:
                return
            if not st.result:
                outcome = st.board.outcome(claim_draw=True)
                st.result = (outcome.result() if outcome else "1/2-1/2")
            r = st.result
            a_score = {"1-0": 1.0, "0-1": 0.0}.get(r, 0.5)
            if a_score == 1:
                st.stats["w"] += 1
            elif a_score == 0:
                st.stats["l"] += 1
            else:
                st.stats["d"] += 1
            st.stats["done"] += 1
            st.status = "between_games"
        record_game(st)
        time.sleep(1.5)
    with st.lock:
        if st.run_id == my_run:
            st.status = "finished"
            st.mode = "idle"


HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nexarch Chess</title>
<style>
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:#a8a8a8;color:#1a1a1a;font:13px "Segoe UI",Tahoma,Arial,sans-serif;display:flex;justify-content:center;align-items:flex-start;padding:18px}
.app{width:100%;max-width:920px;background:#f0f0f0;border:1px solid #777;box-shadow:0 6px 24px rgba(0,0,0,.35);display:flex;flex-direction:column;min-height:600px}
.titlebar{background:linear-gradient(#f7f7f7,#e4e4e4);border-bottom:1px solid #b5b5b5;padding:5px 10px;font-weight:600;font-size:13px;display:flex;justify-content:space-between;align-items:center}
.winbtns{display:flex;gap:4px}
.winbtns span{width:16px;height:14px;border:1px solid #999;background:linear-gradient(#fbfbfb,#dcdcdc);font-size:9px;line-height:11px;text-align:center;color:#333}
.menubar{display:flex;background:#ececec;border-bottom:1px solid #c4c4c4;padding:0 4px;user-select:none}
.menubar span{padding:4px 9px;font-size:12px;cursor:default}
.menubar span:hover{background:#dcdcdc}
.toolbar{display:flex;align-items:center;gap:4px;padding:5px 6px;background:linear-gradient(#fafafa,#e6e6e6);border-bottom:1px solid #c4c4c4}
.tb{white-space:nowrap;border:1px solid #a8a8a8;background:linear-gradient(#fdfdfd,#e3e3e3);padding:4px 10px;font:12px "Segoe UI",Tahoma,sans-serif;color:#111;cursor:pointer;border-radius:2px}
.tb:hover{background:linear-gradient(#fff,#ededed);border-color:#888}
.tb:active{background:#dcdcdc;border-color:#777}
.tb.default{font-weight:600}
.sep{width:1px;height:22px;background:#c8c8c8;margin:0 6px}
.gameinfo{margin-left:auto;font-size:11px;color:#555;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:420px}
.main{display:grid;grid-template-columns:1fr 268px;flex:1;min-height:0}
.boardarea{padding:14px;display:flex;flex-direction:column;justify-content:center;background:#f0f0f0;position:relative}
.banner{display:none;position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);background:rgba(240,240,240,.96);border:1px solid #777;box-shadow:0 4px 18px rgba(0,0,0,.3);padding:9px 18px;font-size:15px;font-weight:600;white-space:nowrap;z-index:2}
.banner.show{display:block}
.player{display:flex;justify-content:space-between;align-items:center;background:#e9e9e9;border:1px solid #bdbdbd;padding:5px 9px;font-size:13px}
.player .name{font-weight:600;display:flex;align-items:center;gap:6px}
.player .clock{font:13px "Consolas",monospace;background:#fff;border:1px solid #b5b5b5;padding:1px 7px;min-width:58px;text-align:right}
.sw{width:10px;height:10px;border:1px solid #666;display:inline-block}
.sw.black{background:#1a1a1a}
.sw.white{background:#fff}
.board{display:grid;grid-template-columns:repeat(8,1fr);grid-template-rows:repeat(8,1fr);width:100%;aspect-ratio:1/1;flex:0 0 auto;border:1px solid #8a8a8a;margin:1px 0}
.sq{position:relative;display:flex;align-items:center;justify-content:center;aspect-ratio:1/1;min-width:0;min-height:0;cursor:pointer;user-select:none;-webkit-tap-highlight-color:transparent}
.sq.light{background:#f0d9b5}.sq.dark{background:#b58863}
.sq.last{background-image:linear-gradient(rgba(255,214,102,.32),rgba(255,214,102,.32))}
.sq.sel{box-shadow:inset 0 0 0 3px #2f6fb0}
.sq.capture{box-shadow:inset 0 0 0 4px rgba(180,58,48,.62)}
.sq.check{box-shadow:inset 0 0 0 4px rgba(196,42,42,.72)}
.dot{position:absolute;width:24%;height:24%;border-radius:50%;background:rgba(30,26,22,.38);pointer-events:none}
.piece{width:88%;height:88%;object-fit:contain;pointer-events:none;display:block}
.dock{background:#f0f0f0;border-left:1px solid #bdbdbd;display:flex;flex-direction:column;min-height:0}
.tabstrip{display:flex;background:#e4e4e4;border-bottom:1px solid #bdbdbd;padding-top:3px}
.tab{padding:5px 12px;font-size:12px;border:1px solid transparent;border-bottom:none;cursor:default;color:#555}
.tab.active{background:#f7f7f7;border-color:#bdbdbd;color:#111;margin-bottom:-1px;position:relative;top:1px}
.moves{flex:1;background:#fff;margin:8px;border:1px solid #bdbdbd;overflow:auto;padding:6px;font:12px/1.7 "Consolas",monospace;white-space:pre-wrap}
.dockinfo{margin:0 8px 8px;background:#fff;border:1px solid #bdbdbd;padding:7px 9px;font-size:12px}
.dockinfo div{display:flex;justify-content:space-between;padding:2px 0}
.dockinfo b{font-weight:600;color:#555}
.strengthBox{margin:8px 8px 0;background:#fff;border:1px solid #bdbdbd;padding:7px 9px;font-size:12px}
.strengthHead{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:2px}
.strengthHead b{font-weight:600;color:#555}
#strengthValue{font:600 12px "Consolas",monospace;color:#1d4f7c}
.strengthBox input[type=range]{width:100%;accent-color:#3b6f9e;margin:1px 0 0;cursor:pointer}
.strengthScale{display:flex;justify-content:space-between;color:#777;font-size:10px;margin-top:-1px}
.strengthNote{color:#777;font-size:10px;line-height:1.35;margin-top:4px}
.brand{display:flex;align-items:center;gap:7px}
.logo{width:18px;height:18px;display:inline-block}
.tagline{color:#666;font-size:11px;font-weight:400}
.titleRight{display:flex;align-items:center;gap:9px}
.langSel{font:12px "Segoe UI",Tahoma,sans-serif;color:#111;background:#fff;border:1px solid #a8a8a8;padding:1px 3px;cursor:pointer}
.ico{width:14px;height:14px;vertical-align:-2px;margin-right:4px}
.dest{background:#fff;border:1px solid #bdbdbd;padding:6px 8px;font-size:12px;color:#333;margin:2px 0 10px}
.rankTabs{display:flex;gap:6px;margin-bottom:8px}
.rankTabs .tb{white-space:nowrap;flex:1}
.rankTabs .tb.on{background:#dcdcdc;border-color:#777;font-weight:600}
table.ranks{width:100%;border-collapse:collapse;font-size:12px}
table.ranks th,table.ranks td{text-align:left;border-bottom:1px solid #ddd;padding:4px 6px}
table.ranks th{color:#555;font-weight:600}
table.ranks td.num{text-align:right;font-family:Consolas,monospace}
.win{color:#1f7a3f}
.loss{color:#a12a2a}
.statusbar{display:flex;gap:16px;border-top:1px solid #b5b5b5;background:#ececec;padding:4px 9px;font-size:12px;color:#333}
.statusbar .grow{flex:1}
.credit{color:#777;font-size:11px}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.28);display:none;align-items:center;justify-content:center;z-index:10}
.modal.open{display:flex}
.dialog{width:360px;background:#f0f0f0;border:1px solid #777;box-shadow:0 8px 26px rgba(0,0,0,.4)}
.dialogTitle{background:linear-gradient(#f7f7f7,#e4e4e4);border-bottom:1px solid #b5b5b5;padding:6px 10px;font-weight:600;font-size:13px}
.dialogBody{padding:14px}
.dialogBody label{display:block;margin-bottom:10px;font-size:12px;color:#444}
.dialogBody label span{display:block;margin-bottom:3px}
.dialogBody select,.dialogBody input{width:100%;padding:5px;border:1px solid #a8a8a8;background:#fff;font:13px "Segoe UI",Tahoma,sans-serif}
.dialogRow{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.dialogButtons{display:flex;justify-content:flex-end;gap:8px;padding:10px 14px;border-top:1px solid #c4c4c4;background:#ececec}
.dialogButtons button{min-width:78px}
.error{color:#9b1c1c;font-size:12px;margin-top:8px}
.hint{color:#666;font-size:11px;line-height:1.45;margin:0 0 10px}
.check{display:flex;align-items:flex-start;gap:7px}
.check input{width:auto;margin-top:2px}
.dialogBody .check span{display:inline;margin:0}
.check span{display:inline;margin:0}
@media(max-width:760px){
  body{padding:0;touch-action:manipulation}
  .app{border:none;min-height:0;max-width:100%}
  .titlebar{padding:6px 10px}
  .winbtns{display:none}
  .menubar{overflow-x:auto;white-space:nowrap;-webkit-overflow-scrolling:touch}
  .menubar span{flex:0 0 auto}
  .toolbar{flex-wrap:wrap;gap:4px}
  .gameinfo{display:none}
  .main{grid-template-columns:1fr;flex:none}
  .boardarea{padding:8px;justify-content:flex-start}
  .player{padding:4px 7px;font-size:12px}
  .player .clock{min-width:50px;font-size:12px}
  .board{width:100%;max-height:calc(100vw - 16px);margin:6px auto}
  .sq{touch-action:manipulation}
  .dock{border-left:none;border-top:1px solid #bdbdbd;max-height:210px}
  .moves{margin:6px;font-size:11px}
  .dockinfo{margin:0 6px 6px}
  .statusbar{font-size:11px;gap:8px;flex-wrap:wrap}
  .credit{display:none}
  .dialog{width:calc(100vw - 24px);max-width:360px}
}
@media(max-width:420px){
  .menubar span:nth-child(n+4){display:none}
  .tb{white-space:nowrap;padding:4px 8px;font-size:11px}
  .board{max-height:calc(100vw - 12px)}
}
</style>
</head><body>
<div class="app">
  <div class="titlebar"><span class="brand"><img class="logo" src="/assets/cutechess/cutechess_32x32.png" alt="">Nexarch Arena</span><span class="titleRight"><span class="tagline" data-i18n="tagline">online companion &middot; engines and settings</span><select id="langSel" class="langSel" aria-label="Language"><option value="en">English</option><option value="de">Deutsch</option></select></span></div>
  <div class="toolbar">
    <button class="tb default" id="newGameBtn"><img class="ico" src="/assets/cutechess/toolbutton/add_16x16.png" alt=""><span data-i18n="newGame">New Game</span></button>
    <button class="tb" id="restartBtn"><img class="ico" src="/assets/cutechess/toolbutton/clone_16x16.png" alt=""><span data-i18n="restart">Restart</span></button>
    <button class="tb" id="stopBtn"><img class="ico" src="/assets/cutechess/toolbutton/remove_16x16.png" alt=""><span data-i18n="stop">Stop</span></button>
    <button class="tb" id="undoBtn"><img class="ico" src="/assets/cutechess/toolbutton/previous_16x16.png" alt=""><span data-i18n="undo">Undo</span></button>
    <span class="sep"></span>
    <button class="tb" id="settingsBtn"><img class="ico" src="/assets/cutechess/toolbutton/configure_16x16.png" alt=""><span data-i18n="settings">Settings</span></button>
    <button class="tb" id="onlineBtn" data-i18n="playOnline">Play Online</button>
    <button class="tb" id="rankingsBtn" data-i18n="rankings">Rankings</button>
    <button class="tb" id="creditsBtn" data-i18n="credits">Credits</button>
    <button class="tb" id="pgnBtn">PGN</button>
    <span class="sep"></span>
    <span class="gameinfo" id="gameInfo">No game</span>
  </div>
  <div class="main">
    <div class="boardarea">
      <div class="player"><span class="name"><span class="sw black"></span><span id="blackName" data-i18n="black">Black</span></span><span class="clock" id="blackClock">5:00.0</span></div>
      <div class="board" id="board"></div>
      <div class="player"><span class="name"><span class="sw white"></span><span id="whiteName" data-i18n="white">White</span></span><span class="clock" id="whiteClock">5:00.0</span></div>
      <div class="banner" id="endBanner"></div>
    </div>
    <div class="dock">
      <div class="tabstrip"><span class="tab active" id="tabMoves" data-i18n="moves">Moves</span><span class="tab" id="tabInfo" data-i18n="info">Info</span></div>
      <div class="strengthBox">
        <div class="strengthHead"><b data-i18n="handicap">Handicap</b><span id="strengthValue">Full strength</span></div>
        <input id="strengthSlider" type="range" min="10" max="100" step="5" value="100" aria-label="Engine strength percentage">
        <div class="strengthScale"><span>10%</span><span>100%</span></div>
        <div class="strengthNote" data-i18n="handicapNote">Handicap, not an Elo rating. Nexarch has no measured rating yet.</div>
      </div>
      <div class="moves" id="moves" data-i18n="noMoves">No moves yet.</div>
      <div class="moves" id="infoPanel" style="display:none">
        <div class="dockinfo" style="margin:0 0 8px"><div><b>FEN</b><span id="fenText">-</span></div></div>
        <div class="dockinfo" style="margin:0 0 8px"><div><b data-i18n="engine">Engine</b><span id="engineInfo">-</span></div></div>
        <button class="tb" id="copyFenBtn" data-i18n="copyFen">Copy FEN</button>
      </div>
      <div class="dockinfo">
        <div><b data-i18n="status">Status</b><span id="statusText" data-i18n="idle">Idle</span></div>
        <div><b data-i18n="result">Result</b><span id="result">-</span></div>
        <div><b data-i18n="score">Score</b><span id="score">+0 =0 -0</span></div>
      </div>
    </div>
  </div>
  <div class="statusbar"><span class="grow" id="statusMessage" data-i18n="ready">Ready</span><span id="enginesLabel">-</span><span class="credit" data-i18n="creditLine">Engine: Nexarch (MIT) &middot; GUI: GPL-3.0 &middot; Pieces: Cburnett CC BY-SA 3.0</span></div>
</div>

<div class="modal" id="settingsModal">
  <div class="dialog">
    <div class="dialogTitle" data-i18n="settingsTitle">Settings</div>
    <div class="dialogBody">
      <label class="check"><input type="checkbox" id="telemetry"><span data-i18n="anonymous">Anonymous game collection</span></label>
      <p class="hint" data-i18n="telemetryHint">Off by default. When enabled, finished games against Nexarch are saved on this computer and sent to the endpoint below. No account name, email address or hardware ID is included.</p>
      <label><span data-i18n="uploadDestination">Upload destination</span></label>
      <div class="dest" id="dest">Anonymous game collection is off</div>
      <div class="dialogRow">
        <label><span>Threads</span><input id="threads" type="number" min="1" max="64" value="1"></label>
        <label><span data-i18n="hash">Hash (MB)</span><input id="hash" type="number" min="1" max="65536" value="64"></label>
      </div>
      <label><span data-i18n="engineStrength">Engine strength (handicap)</span><input id="strengthSetting" type="range" min="10" max="100" step="5" value="100"></label>
      <div class="dest" id="strengthSettingLabel">Full strength</div>
      <p class="hint" data-i18n="handicapShort">This is a handicap, not an Elo rating. Nexarch has no measured rating yet.</p>
      <div class="error" id="settingsErr" style="display:none"></div>
    </div>
    <div class="dialogButtons">
      <button class="tb" id="settingsCancel" data-i18n="cancel">Cancel</button>
      <button class="tb default" id="settingsSave" data-i18n="save">Save</button>
    </div>
  </div>
</div>

<div class="modal" id="creditsModal">
  <div class="dialog" style="width:620px;max-width:calc(100vw - 24px)">
    <div class="dialogTitle" data-i18n="creditsTitle">Credits</div>
    <div class="dialogBody"><pre id="creditsText" style="max-height:60vh;overflow:auto;white-space:pre-wrap;font:12px/1.55 Consolas,monospace;margin:0"></pre></div>
    <div class="dialogButtons"><button class="tb" id="creditsClose" data-i18n="close">Close</button></div>
  </div>
</div>

<div class="modal" id="rankingsModal">
  <div class="dialog" style="width:560px;max-width:calc(100vw - 24px)">
    <div class="dialogTitle" data-i18n="rankingsTitle">Live rankings</div>
    <div class="dialogBody">
      <div class="rankTabs">
        <button class="tb on" id="rankLichess">Lichess</button>
        <button class="tb" id="rankChesscom">Chess.com</button>
      </div>
      <div class="dialogRow" style="grid-template-columns:1fr">
        <label><span data-i18n="timeControl">Time control</span><select id="perfSel">
          <option value="bullet" data-i18n="bullet">Bullet</option>
          <option value="blitz" selected data-i18n="blitz">Blitz</option>
          <option value="rapid" data-i18n="rapid">Rapid</option>
          <option value="classical" data-i18n="classical">Classical</option>
        </select></label>
      </div>
      <table class="ranks"><thead><tr><th>#</th><th data-i18n="player">Player</th><th data-i18n="title">Title</th><th style="text-align:right" data-i18n="rating">Rating</th></tr></thead><tbody id="rankRows"><tr><td colspan="4" data-i18n="loading">Loading...</td></tr></tbody></table>
      <div class="error" id="rankErr" style="display:none"></div>
    </div>
    <div class="dialogButtons"><button class="tb" id="rankClose" data-i18n="close">Close</button></div>
  </div>
</div>

<div class="modal" id="onlineModal">
  <div class="dialog" style="width:420px;max-width:calc(100vw - 24px)">
    <div class="dialogTitle" data-i18n="onlineTitle">Play online</div>
    <div class="dialogBody">
      <label><span data-i18n="server">Server</span><input id="mpServer" value="http://158.180.55.245:8090"></label>
      <label><span data-i18n="yourName">Your name</span><input id="mpName" value="Player"></label>
      <div class="dialogRow">
        <label><span data-i18n="color">Color</span><select id="mpColor"><option value="w" data-i18n="white">White</option><option value="b" data-i18n="black">Black</option><option value="r" data-i18n="random">Random</option></select></label>
        <label><span data-i18n="roomCode">Room code to join</span><input id="mpRoom" placeholder="ABC123"></label>
      </div>
      <div class="dialogRow">
        <button class="tb" id="mpCreate" data-i18n="createRoom">Create room</button>
        <button class="tb" id="mpJoin" data-i18n="joinRoom">Join room</button>
      </div>
      <div class="dest" id="mpStatus" data-i18n="notConnected">Not connected</div>
    </div>
    <div class="dialogButtons"><button class="tb" id="mpLeave" data-i18n="leave">Leave</button><button class="tb" id="mpClose" data-i18n="close">Close</button></div>
  </div>
</div>

<div class="modal" id="newGameModal">
  <div class="dialog">
    <div class="dialogTitle" data-i18n="newGameTitle">New Game</div>
    <div class="dialogBody">
      <label><span data-i18n="white">White</span><select id="whiteSel"></select></label>
      <label><span data-i18n="black">Black</span><select id="blackSel"></select></label>
      <div class="dialogRow">
        <label><span data-i18n="timeControl">Time control</span><input id="tc" value="5+0.05"></label>
        <label><span data-i18n="nodesLabel">Nodes</span><input id="nodes" value="0"></label>
      </div>
      <label><span data-i18n="gamesLabel">Games</span><input id="games" value="1"></label>
      <div class="error" id="errRow" style="display:none"><span id="err"></span></div>
    </div>
    <div class="dialogButtons">
      <button class="tb" id="cancelBtn" data-i18n="cancel">Cancel</button>
      <button class="tb default" id="okBtn" data-i18n="ok">OK</button>
    </div>
  </div>
</div>
<script>
var UNICODE = {K:"\u2654",Q:"\u2655",R:"\u2656",B:"\u2657",N:"\u2658",P:"\u2659",k:"\u265A",q:"\u265B",r:"\u265C",b:"\u265D",n:"\u265E",p:"\u265F"};
var PIECE_FILE = {K:"klt45",Q:"qlt45",R:"rlt45",B:"blt45",N:"nlt45",P:"plt45",k:"kdt45",q:"qdt45",r:"rdt45",b:"bdt45",n:"ndt45",p:"pdt45"};
var SID = sessionStorage.getItem("nx_sid");
if(!SID){SID=Math.random().toString(36).slice(2)+Date.now().toString(36);sessionStorage.setItem("nx_sid",SID);}
function api(path){return path+(path.indexOf("?")>=0?"&":"?")+"s="+encodeURIComponent(SID);}
var STATE = {};
var selected = null;
var selectedPiece = null;
var lastFen = "";
var sideHuman = {w:false,b:false};

var I18N = {
  en: {
    tagline: "online companion · engines and settings",
    newGame: "New Game", restart: "Restart", stop: "Stop", undo: "Undo",
    settings: "Settings", playOnline: "Play Online", rankings: "Rankings", credits: "Credits",
    moves: "Moves", info: "Info", handicap: "Handicap", noMoves: "No moves yet.",
    handicapNote: "Handicap, not an Elo rating. Nexarch has no measured rating yet.",
    engine: "Engine", copyFen: "Copy FEN", status: "Status", idle: "Idle",
    result: "Result", score: "Score", ready: "Ready", black: "Black", white: "White",
    creditLine: "Engine: Nexarch (MIT) · GUI: GPL-3.0 · Pieces: Cburnett CC BY-SA 3.0",
    settingsTitle: "Settings", anonymous: "Anonymous game collection",
    telemetryHint: "Off by default. When enabled, finished games against Nexarch are saved on this computer and sent to the endpoint below. No account name, email address or hardware ID is included.",
    uploadDestination: "Upload destination", hash: "Hash (MB)",
    engineStrength: "Engine strength (handicap)",
    handicapShort: "This is a handicap, not an Elo rating. Nexarch has no measured rating yet.",
    cancel: "Cancel", save: "Save", creditsTitle: "Credits", close: "Close",
    rankingsTitle: "Live rankings", timeControl: "Time control", bullet: "Bullet",
    blitz: "Blitz", rapid: "Rapid", classical: "Classical", player: "Player",
    title: "Title", rating: "Rating", loading: "Loading...", noRows: "No rows",
    onlineTitle: "Play online", server: "Server", yourName: "Your name", color: "Color",
    random: "Random", roomCode: "Room code to join", createRoom: "Create room",
    joinRoom: "Join room", notConnected: "Not connected", leave: "Leave",
    defaultName: "Player", shareCode: "Room {room} - share the code; waiting for opponent",
    youAreColor: "Room {room} - you are {color}",
    newGameTitle: "New Game", nodesLabel: "Nodes", gamesLabel: "Games", ok: "OK",
    human: "Human", fullStrength: "Full strength", strengthPercent: "{n}% strength",
    playing: "Playing", thinking: "Thinking...", checkSuffix: " (check)",
    whiteMates: "White mates", blackMates: "Black mates",
    drawStalemate: "Draw by stalemate",
    drawInsufficient: "Draw by insufficient mating material",
    drawFifty: "Draw by fifty moves rule",
    drawThreefold: "Draw by 3-fold repetition",
    drawSeventyfive: "Draw by seventy-five moves rule",
    drawFivefold: "Draw by fivefold repetition",
    drawBy: "Draw by {reason}", draw: "Draw",
    whiteWins: "White wins", blackWins: "Black wins",
    losesOnTime: "{side} loses on time", noGame: "No game",
    nodesSuffix: " ({n} nodes)", depth: "depth {n}", nodesCount: "{n} nodes",
    enginesLabel: "Engines: ", telemetryOff: "Anonymous game collection is off",
    telemetryOn: "Games will be sent to: {url}",
    networkError: "Network error", strengthError: "Could not change strength",
    onlineUnreachable: "Cannot reach the online server",
    waitingOpponent: "Room {room} - share the code; waiting for opponent",
    youAre: "Room {room} - you are {color}",
    waitingForOpponent: "Room {room} - waiting for opponent",
    gameOver: "Game over {result}",
    yourMove: "Room {room} - you are {color}, your move",
    theirMove: "Room {room} - you are {color}, waiting",
    rankingStatus: "Live blitz rankings from Lichess and Chess.com."
  },
  de: {
    tagline: "Online-Begleiter · Engines und Einstellungen",
    newGame: "Neues Spiel", restart: "Neustart", stop: "Stopp", undo: "Zurück",
    settings: "Einstellungen", playOnline: "Online", rankings: "Ranglisten",
    credits: "Credits", moves: "Züge", info: "Info", handicap: "Handicap",
    noMoves: "Noch keine Züge.",
    handicapNote: "Handicap, keine Elo-Zahl. Nexarch hat noch keine gemessene Wertung.",
    engine: "Engine", copyFen: "FEN kopieren", status: "Status", idle: "Bereit",
    result: "Ergebnis", score: "Stand", ready: "Bereit", black: "Schwarz", white: "Weiß",
    creditLine: "Engine: Nexarch (MIT) · GUI: GPL-3.0 · Figuren: Cburnett CC BY-SA 3.0",
    settingsTitle: "Einstellungen", anonymous: "Anonyme Partiensammlung",
    telemetryHint: "Standardmäßig aus. Wenn aktiviert, werden beendete Partien gegen Nexarch auf diesem Computer gespeichert und an die unten stehende Adresse gesendet. Es werden keine Kontonamen, E-Mail-Adressen oder Hardware-IDs übertragen.",
    uploadDestination: "Upload-Ziel", hash: "Hash (MB)",
    engineStrength: "Engine-Stärke (Handicap)",
    handicapShort: "Das ist ein Handicap, keine Elo-Zahl. Nexarch hat noch keine gemessene Wertung.",
    cancel: "Abbrechen", save: "Speichern", creditsTitle: "Danksagung", close: "Schließen",
    rankingsTitle: "Live-Ranglisten", timeControl: "Zeitkontrolle", bullet: "Bullet",
    blitz: "Blitz", rapid: "Rapid", classical: "Klassisch", player: "Spieler",
    title: "Titel", rating: "Wertung", loading: "Lädt...", noRows: "Keine Einträge",
    onlineTitle: "Online spielen", server: "Server", yourName: "Dein Name", color: "Farbe",
    random: "Zufällig", roomCode: "Raumcode zum Beitreten", createRoom: "Raum erstellen",
    joinRoom: "Raum beitreten", notConnected: "Nicht verbunden", leave: "Verlassen",
    defaultName: "Spieler", shareCode: "Raum {room} - teile den Code; warte auf Gegner",
    youAreColor: "Raum {room} - du bist {color}",
    newGameTitle: "Neues Spiel", nodesLabel: "Knoten", gamesLabel: "Partien", ok: "OK",
    human: "Mensch", fullStrength: "Volle Stärke", strengthPercent: "{n}% Stärke",
    playing: "Spielt", thinking: "Denkt nach...", checkSuffix: " (Schach)",
    whiteMates: "Weiß setzt matt", blackMates: "Schwarz setzt matt",
    drawStalemate: "Remis durch Patt",
    drawInsufficient: "Remis durch unzureichendes Material",
    drawFifty: "Remis durch die 50-Züge-Regel",
    drawThreefold: "Remis durch dreifache Stellungswiederholung",
    drawSeventyfive: "Remis durch die 75-Züge-Regel",
    drawFivefold: "Remis durch fünffache Stellungswiederholung",
    drawBy: "Remis durch {reason}", draw: "Remis",
    whiteWins: "Weiß gewinnt", blackWins: "Schwarz gewinnt",
    losesOnTime: "{side} verliert auf Zeit", noGame: "Kein Spiel",
    nodesSuffix: " ({n} Knoten)", depth: "Tiefe {n}", nodesCount: "{n} Knoten",
    enginesLabel: "Engines: ", telemetryOff: "Anonyme Partiensammlung ist aus",
    telemetryOn: "Partien werden gesendet an: {url}",
    networkError: "Netzwerkfehler", strengthError: "Stärke konnte nicht geändert werden",
    onlineUnreachable: "Der Online-Server ist nicht erreichbar",
    waitingOpponent: "Raum {room} - teile den Code; warte auf Gegner",
    youAre: "Raum {room} - du bist {color}",
    waitingForOpponent: "Raum {room} - warte auf Gegner",
    gameOver: "Partie beendet {result}",
    yourMove: "Raum {room} - du bist {color}, du bist am Zug",
    theirMove: "Raum {room} - du bist {color}, Gegner ist am Zug",
    rankingStatus: "Live-Blitztlisten von Lichess und Chess.com."
  }
};
var LANG = "en";
try {
  var savedLang = localStorage.getItem("nx_lang");
  if (savedLang === "de" || savedLang === "en") LANG = savedLang;
  else if ((navigator.language || "").toLowerCase().indexOf("de") === 0) LANG = "de";
} catch (e) {}
function tr(key, vars) {
  var table = I18N[LANG] || I18N.en;
  var text = table[key] !== undefined ? table[key] : I18N.en[key];
  if (text === undefined) return key;
  if (vars) {
    for (var k in vars) text = text.split("{" + k + "}").join(vars[k]);
  }
  return text;
}
function applyLanguage() {
  document.documentElement.lang = LANG;
  var nodes = document.querySelectorAll("[data-i18n]");
  for (var i = 0; i < nodes.length; i++) nodes[i].textContent = tr(nodes[i].getAttribute("data-i18n"));
  var sel = document.getElementById("langSel");
  if (sel) sel.value = LANG;
  var nameInput = document.getElementById("mpName");
  if (nameInput && (nameInput.value === "Player" || nameInput.value === "Spieler")) nameInput.value = tr("defaultName");
  var humanOptions = document.querySelectorAll("#whiteSel option[value='__human__'], #blackSel option[value='__human__']");
  for (var h = 0; h < humanOptions.length; h++) humanOptions[h].textContent = tr("human");
  if (typeof paintStrength === "function" && document.getElementById("strengthSlider")) paintStrength(document.getElementById("strengthSlider").value);
  if (typeof updateDest === "function") updateDest();
  if (STATE && STATE.clocks) applyState(STATE);
  else {
    document.getElementById("gameInfo").textContent = tr("noGame");
    document.getElementById("statusText").textContent = tr("idle");
    document.getElementById("statusMessage").textContent = tr("ready");
    document.getElementById("whiteName").textContent = tr("white");
    document.getElementById("blackName").textContent = tr("black");
  }
}

function parseFen(fen){
  var rows=fen.split(" ")[0].split("/"), out={};
  for(var r=0;r<8;r++){var f=0;for(var i=0;i<rows[r].length;i++){var c=rows[r][i];
    if(c>="1"&&c<="8"){f+=parseInt(c);}else{out["abcdefgh"[f]+(8-r)]=c;f++;}}}
  return out;
}
function squareName(row,col){return "abcdefgh"[col]+(8-row);}
function kingSquare(fen){var pieces=parseFen(fen),side=fen.split(" ")[1],target=side==="w"?"K":"k";for(var sq in pieces)if(pieces[sq]===target)return sq;return "";}
function renderBoard(fen){
  var board=document.getElementById("board"), pieces=parseFen(fen);
  var targets=(selected&&STATE.legal&&STATE.legal[selected])?STATE.legal[selected]:[];
  var lastFrom=STATE.last_uci?STATE.last_uci.slice(0,2):"";
  var lastTo=STATE.last_uci?STATE.last_uci.slice(2,4):"";
  var checkSq=STATE.check?kingSquare(fen):"";
  board.innerHTML="";
  for(var row=0;row<8;row++)for(var col=0;col<8;col++){
    var name=squareName(row,col), d=document.createElement("div");
    d.className="sq "+((row+col)%2===0?"light":"dark");
    d.dataset.square=name;
    if(selected&&name===selected)d.className+=" sel";
    if(name===lastFrom||name===lastTo)d.className+=" last";
    if(name===checkSq)d.className+=" check";
    var p=pieces[name], isTarget=targets.indexOf(name)>=0;
    if(isTarget&&!p){var dot=document.createElement("span");dot.className="dot";d.appendChild(dot);}
    if(isTarget&&p)d.className+=" capture";
    if(p){var s=document.createElement("img");s.className="piece";s.alt=UNICODE[p]||"";s.src="/pieces/"+(PIECE_FILE[p]||"")+".svg";d.appendChild(s);}
    d.onclick=onSquareClick;
    board.appendChild(d);
  }
  lastFen=fen;
}
function onSquareClick(ev){
  var sq=ev.currentTarget.dataset.square;
  if(!sq)return;
  if(STATE.thinking||STATE.status!=="playing"||!sideHuman[STATE.side_to_move])return;
  if(STATE.online&&STATE.side_to_move!==STATE.online_color)return;
  if(!selected){
    var pieces=parseFen(STATE.fen), p=pieces[sq];
    if(!p)return;
    var isWhite=p===p.toUpperCase();
    if((STATE.side_to_move==="w")!==isWhite)return;
    selected=sq; selectedPiece=p; renderBoard(STATE.fen);
  }else{
    var from=selected, piece=selectedPiece; selected=null; selectedPiece=null;
    var uci=from+sq;
    if((piece==="P"&&sq[1]==="8")||(piece==="p"&&sq[1]==="1"))uci+="q";
    sendMove(uci);
  }
}
function sendMove(uci){
  if(mp){mpSend(uci);return;}
  fetch(api("/move"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({uci:uci})})
    .then(function(r){return r.json();})
    .then(function(d){if(d.error){showError(d.error);selected=null;refresh();return;}if(d.state)applyState(d.state);})
    .catch(function(){showError(tr("networkError"));});
}
function showError(msg){document.getElementById("err").textContent=msg;document.getElementById("errRow").style.display="block";}
function fmtClock(t){t=Math.max(0,t);var m=Math.floor(t/60),s=t-m*60;return m+":"+(s<10?"0":"")+s.toFixed(1);}
function fmtMoves(moves){
  if(!moves||!moves.length)return tr("noMoves");
  var out=[];
  for(var i=0;i<moves.length;i+=2)out.push((i/2+1)+". "+moves[i]+(moves[i+1]?" "+moves[i+1]:""));
  return out.join("\n");
}
function terminationText(name){
  if(!name)return tr("draw");
  if(name==="checkmate")return tr(STATE.winner==="w"?"whiteMates":"blackMates");
  if(name==="stalemate")return tr("drawStalemate");
  if(name==="insufficient_material")return tr("drawInsufficient");
  if(name==="fifty_moves")return tr("drawFifty");
  if(name==="threefold_repetition")return tr("drawThreefold");
  if(name==="seventyfive_moves")return tr("drawSeventyfive");
  if(name==="fivefold_repetition")return tr("drawFivefold");
  if(name.indexOf("loses on time")>=0){
    var side=name.indexOf("White")===0?tr("white"):tr("black");
    return tr("losesOnTime",{side:side});
  }
  return tr("drawBy",{reason:name.replace(/_/g," ")});
}
function applyState(s){
  STATE=s;
  sideHuman={w:!!s.white_human,b:!!s.black_human};
  var st=tr("idle"), cls="";
  if(s.status==="playing"){
    st=s.thinking?tr("thinking"):tr("playing");
    if(s.check)st+=tr("checkSuffix");
  }
  if((s.status==="finished"||s.status==="between_games")&&(s.termination||s.end_reason)){
    if(s.end_reason){
      st=terminationText(s.end_reason);
      cls=s.end_reason.indexOf("loses")>=0?"loss":"win";
    }else if(s.termination){
      st=terminationText(s.termination);
      cls=s.termination==="checkmate"?"win":"";
    }
  }
  var stEl=document.getElementById("statusText");
  stEl.textContent=st;
  stEl.className="val "+cls;
  var banner=document.getElementById("endBanner");
  var ended=s.status==="finished"||s.status==="between_games";
  banner.textContent=st;
  banner.className=ended&&(s.termination||s.end_reason)?"banner show":"banner";
  document.getElementById("statusMessage").textContent=st;
  var bothHuman=s.white_human&&s.black_human;
  document.getElementById("whiteName").textContent=bothHuman?tr("white"):(s.white_name||tr("white"));
  document.getElementById("blackName").textContent=bothHuman?tr("black"):(s.black_name||tr("black"));
  document.getElementById("whiteClock").textContent=fmtClock(s.clocks.w);
  document.getElementById("blackClock").textContent=fmtClock(s.clocks.b);
  document.getElementById("score").textContent="+"+s.stats.w+" = "+s.stats.d+" - "+s.stats.l;
  if(s.settings&&s.settings.strength!==undefined&&Date.now()>strengthBusy&&document.activeElement!==strengthSlider){
    var pct=parseInt(s.settings.strength);
    if(parseInt(strengthSlider.value)!==pct){strengthSlider.value=pct;paintStrength(pct);}
  }
  document.getElementById("result").textContent=s.result?((s.winner?(s.winner==="w"?tr("whiteWins"):tr("blackWins"))+" · ":tr("draw")+" · ")+s.result):"-";
  document.getElementById("moves").textContent=fmtMoves(s.moves);
  var info=s.engine_info||{};
  document.getElementById("fenText").textContent=s.fen;
  var infoParts=[];
  if(info.depth)infoParts.push(tr("depth",{n:info.depth}));
  if(info.score)infoParts.push(info.score);
  if(info.nodes)infoParts.push(tr("nodesCount",{n:info.nodes}));
  document.getElementById("engineInfo").textContent=infoParts.length?infoParts.join(" · "):"-";
  var whiteLabel=s.white_name==="Human"?tr("human"):s.white_name;
  var blackLabel=s.black_name==="Human"?tr("human"):s.black_name;
  document.getElementById("gameInfo").textContent=s.white_name&&s.black_name?(whiteLabel+" vs "+blackLabel+(s.nodes?tr("nodesSuffix",{n:s.nodes}):" ("+s.tc_base+"s+"+s.tc_inc+"s)")):tr("noGame");
  document.getElementById("enginesLabel").textContent=tr("enginesLabel")+((s.engines||[]).join(", ")||"-");
  var er=document.getElementById("errRow");
  if(s.last_error){document.getElementById("err").textContent=s.last_error;er.style.display="block";}else{er.style.display="none";}
  if(s.fen!==lastFen){selected=null;selectedPiece=null;renderBoard(s.fen);}
}
var refreshSeq=0;
function refresh(){var seq=++refreshSeq;fetch(api("/state.json")+"&t="+Date.now()).then(function(r){return r.json();}).then(function(s){if(seq===refreshSeq)applyState(s);}).catch(function(){});}
function populate(){
  fetch(api("/state.json")).then(function(r){return r.json();}).then(function(s){
    var w=document.getElementById("whiteSel"),b=document.getElementById("blackSel");
    w.innerHTML="";b.innerHTML="";
    var h=document.createElement("option");h.value="__human__";h.textContent=tr("human");
    w.appendChild(h.cloneNode(true));b.appendChild(h);
    (s.engines||[]).forEach(function(n){
      var a=document.createElement("option");a.value=n;a.textContent=n;w.appendChild(a);
      var c=document.createElement("option");c.value=n;c.textContent=n;b.appendChild(c);
    });
    w.value="__human__";
    b.value=(s.engines&&s.engines.length)?s.engines[0]:"__human__";
    applyState(s);
  });
}
function openDialog(){document.getElementById("newGameModal").classList.add("open");}
function closeDialog(){document.getElementById("newGameModal").classList.remove("open");}
function startGame(){
  var body={
    white:document.getElementById("whiteSel").value,
    black:document.getElementById("blackSel").value,
    tc:document.getElementById("tc").value,
    nodes:parseInt(document.getElementById("nodes").value)||0,
    games:parseInt(document.getElementById("games").value)||1
  };
  fetch(api("/start"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)})
    .then(function(r){return r.json();})
    .then(function(d){if(d.error)showError(d.error);if(d.state)applyState(d.state);closeDialog();})
    .catch(function(){showError(tr("networkError"));});
}
function restartGame(){fetch(api("/restart"),{method:"POST"}).then(function(){refresh();});}
function stopGame(){fetch(api("/stop"),{method:"POST"}).then(function(){refresh();});}
var settingsModal=document.getElementById("settingsModal");
var creditsModal=document.getElementById("creditsModal");
var uploadUrl="";
function updateDest(){
  var on=document.getElementById("telemetry").checked;
  document.getElementById("dest").textContent=on?tr("telemetryOn",{url:(uploadUrl||tr("server"))}):tr("telemetryOff");
}
document.getElementById("telemetry").onchange=updateDest;
function strengthText(value){
  value=parseInt(value)||100;
  return value>=100?tr("fullStrength"):tr("strengthPercent",{n:value});
}
var strengthSlider=document.getElementById("strengthSlider");
var strengthBusy=0;
function paintStrength(value){
  document.getElementById("strengthValue").textContent=strengthText(value);
  var setting=document.getElementById("strengthSetting");
  if(setting)setting.value=value;
  var label=document.getElementById("strengthSettingLabel");
  if(label)label.textContent=strengthText(value);
}
function saveStrength(value){
  strengthBusy=Date.now()+1500;
  fetch(api("/strength"),{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({percent:parseInt(value)})})
    .then(function(r){return r.json();})
    .then(function(d){if(d.settings&&STATE.settings)STATE.settings=d.settings;})
    .catch(function(){showError(tr("strengthError"));});
}
strengthSlider.oninput=function(){paintStrength(this.value);};
strengthSlider.onchange=function(){saveStrength(this.value);};
document.getElementById("strengthSetting").oninput=function(){paintStrength(this.value);};
document.getElementById("strengthSetting").onchange=function(){saveStrength(this.value);};
document.getElementById("settingsBtn").onclick=function(){
  fetch(api("/settings")).then(function(r){return r.json();}).then(function(s){
    document.getElementById("telemetry").checked=!!s.telemetry;
    uploadUrl=s.endpoint||"";
    document.getElementById("threads").value=s.threads||1;
    document.getElementById("hash").value=s.hash||64;
    var pct=(s.strength===undefined?100:s.strength);
    document.getElementById("strengthSetting").value=pct;
    document.getElementById("strengthSettingLabel").textContent=strengthText(pct);
    updateDest();
    settingsModal.classList.add("open");
  }).catch(function(){showError(tr("networkError"));});
};
document.getElementById("settingsCancel").onclick=function(){settingsModal.classList.remove("open");};
settingsModal.onclick=function(e){if(e.target===this)settingsModal.classList.remove("open");};
document.getElementById("settingsSave").onclick=function(){
  fetch(api("/settings"),{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({telemetry:document.getElementById("telemetry").checked,
                         threads:document.getElementById("threads").value,
                         hash:document.getElementById("hash").value,
                         strength:document.getElementById("strengthSetting").value})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.error){document.getElementById("settingsErr").textContent=d.error;document.getElementById("settingsErr").style.display="block";return;}
      settingsModal.classList.remove("open");
    }).catch(function(){showError(tr("networkError"));});
};
document.getElementById("creditsBtn").onclick=function(){
  fetch(api("/credits")).then(function(r){return r.text();}).then(function(t){
    document.getElementById("creditsText").textContent=t;
    creditsModal.classList.add("open");
  }).catch(function(){showError(tr("networkError"));});
};
document.getElementById("creditsClose").onclick=function(){creditsModal.classList.remove("open");};
creditsModal.onclick=function(e){if(e.target===this)creditsModal.classList.remove("open");};
document.getElementById("pgnBtn").onclick=function(){window.location=api("/pgn");};
document.getElementById("undoBtn").onclick=function(){
  fetch(api("/undo"),{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})
    .then(function(r){return r.json();}).then(function(d){
      if(d.error){showError(d.error);return;}
      if(d.state)applyState(d.state);
    }).catch(function(){showError(tr("networkError"));});
};
var rankSite="lichess";
var rankingsModal=document.getElementById("rankingsModal");
function loadRankings(){
  var perf=document.getElementById("perfSel").value;
  document.getElementById("rankRows").innerHTML='<tr><td colspan="4">'+tr("loading")+'</td></tr>';
  document.getElementById("rankErr").style.display="none";
  fetch(api("/rankings?site="+encodeURIComponent(rankSite)+"&perf="+encodeURIComponent(perf)))
    .then(function(r){return r.json();}).then(function(d){
      if(d.error){document.getElementById("rankErr").textContent=d.error;document.getElementById("rankErr").style.display="block";}
      var rows=(d.rows||[]).map(function(x,i){
        return "<tr><td>"+(i+1)+"</td><td>"+escapeHtml(x.name||"")+"</td><td>"+escapeHtml(x.title||"")+"</td><td class='num'>"+x.rating+"</td></tr>";
      }).join("");
      document.getElementById("rankRows").innerHTML=rows||'<tr><td colspan="4">'+tr("noRows")+'</td></tr>';
    }).catch(function(e){document.getElementById("rankErr").textContent=tr("networkError");document.getElementById("rankErr").style.display="block";});
}
function escapeHtml(t){return String(t).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}
document.getElementById("rankingsBtn").onclick=function(){
  rankingsModal.classList.add("open"); loadRankings();
};
document.getElementById("rankClose").onclick=function(){rankingsModal.classList.remove("open");};
rankingsModal.onclick=function(e){if(e.target===this)rankingsModal.classList.remove("open");};
document.getElementById("rankLichess").onclick=function(){rankSite="lichess";this.classList.add("on");document.getElementById("rankChesscom").classList.remove("on");loadRankings();};
document.getElementById("rankChesscom").onclick=function(){rankSite="chesscom";this.classList.add("on");document.getElementById("rankLichess").classList.remove("on");loadRankings();};
document.getElementById("perfSel").onchange=loadRankings;
function showTab(name){
  document.getElementById("moves").style.display=name==="moves"?"block":"none";
  document.getElementById("infoPanel").style.display=name==="info"?"block":"none";
  document.getElementById("tabMoves").className="tab"+(name==="moves"?" active":"");
  document.getElementById("tabInfo").className="tab"+(name==="info"?" active":"");
}
document.getElementById("tabMoves").onclick=function(){showTab("moves");};
document.getElementById("tabInfo").onclick=function(){showTab("info");};
document.getElementById("copyFenBtn").onclick=function(){
  if(navigator.clipboard&&STATE.fen)navigator.clipboard.writeText(STATE.fen);
};
var onlineModal=document.getElementById("onlineModal");
var mp=null, mpTimer=null, mpCount=0;
function mpStatus(t){document.getElementById("mpStatus").textContent=t;}
function mpStartPoll(){if(mpTimer)clearInterval(mpTimer);mpTimer=setInterval(mpPoll,1000);}
async function mpCreate(){
  var server=document.getElementById("mpServer").value.trim().replace(/\/$/,"");
  var name=document.getElementById("mpName").value.trim()||tr("defaultName");
  var color=document.getElementById("mpColor").value; if(color==="r")color=Math.random()<0.5?"w":"b";
  try{
    var r=await fetch(server+"/api/room",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:name,color:color})});
    var d=await r.json(); if(d.error){showError(d.error);return;}
    mp={server:server,room:d.room,token:d.token,color:d.color}; mpCount=0;
    await fetch(api("/mp/start"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({room:d.room,server:server,color:d.color,white:d.state.white,black:d.state.black})});
    document.getElementById("mpRoom").value=d.room;
    mpStatus(tr("shareCode",{room:d.room}));
    mpStartPoll();
  }catch(e){showError(tr("onlineUnreachable"));}
}
async function mpJoin(){
  var server=document.getElementById("mpServer").value.trim().replace(/\/$/,"");
  var name=document.getElementById("mpName").value.trim()||tr("defaultName");
  var room=document.getElementById("mpRoom").value.trim().toUpperCase();
  try{
    var r=await fetch(server+"/api/join",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({room:room,name:name})});
    var d=await r.json(); if(d.error){showError(d.error);return;}
    mp={server:server,room:d.room,token:d.token,color:d.color}; mpCount=d.state.count;
    await fetch(api("/mp/start"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({room:d.room,server:server,color:d.color,white:d.state.white,black:d.state.black})});
    mpStatus(tr("youAreColor",{room:d.room,color:(d.color==="w"?tr("white"):tr("black"))}));
    mpStartPoll();
  }catch(e){showError(tr("onlineUnreachable"));}
}
async function mpPoll(){
  if(!mp)return;
  try{
    var r=await fetch(mp.server+"/api/state?room="+mp.room+"&since=0"); var d=await r.json();
    if(d.error)return;
    if(d.count!==mpCount){
      mpCount=d.count;
      var x=await fetch(api("/mp/apply"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({moves:d.moves,white:d.white,black:d.black})});
      var j=await x.json(); if(j.state)applyState(j.state);
    }
    var colour=mp.color==="w"?tr("white"):tr("black");
    if(d.status==="finished"){mpStatus(tr("gameOver",{result:d.result}));}
    else if(d.white&&d.black){mpStatus(tr(d.turn===mp.color?"yourMove":"theirMove",{room:d.room,color:colour}));}
    else{mpStatus(tr("waitingForOpponent",{room:d.room}));}
  }catch(e){}
}
async function mpSend(uci){
  if(!mp)return;
  try{
    var r=await fetch(mp.server+"/api/move",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({room:mp.room,token:mp.token,uci:uci})});
    var d=await r.json(); if(d.error){showError(d.error);return;}
    mpCount=d.count;
    var x=await fetch(api("/mp/apply"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({moves:d.moves,white:d.white,black:d.black})});
    var j=await x.json(); if(j.state)applyState(j.state);
  }catch(e){showError(tr("networkError"));}
}
function mpLeave(){if(mp){fetch(api("/mp/end"),{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"}).catch(function(){});} mp=null; if(mpTimer)clearInterval(mpTimer); mpTimer=null; mpStatus(tr("notConnected"));}
document.getElementById("onlineBtn").onclick=function(){onlineModal.classList.add("open");};
document.getElementById("mpClose").onclick=function(){onlineModal.classList.remove("open");};
onlineModal.onclick=function(e){if(e.target===this)onlineModal.classList.remove("open");};
document.getElementById("mpCreate").onclick=mpCreate;
document.getElementById("mpJoin").onclick=mpJoin;
document.getElementById("mpLeave").onclick=mpLeave;
document.getElementById("newGameBtn").onclick=openDialog;
document.getElementById("okBtn").onclick=startGame;
document.getElementById("cancelBtn").onclick=closeDialog;
document.getElementById("restartBtn").onclick=restartGame;
document.getElementById("stopBtn").onclick=stopGame;
document.getElementById("newGameModal").onclick=function(e){if(e.target===this)closeDialog();};
document.getElementById("langSel").onchange=function(){
  LANG=this.value==="de"?"de":"en";
  try{localStorage.setItem("nx_lang",LANG);}catch(e){}
  applyLanguage();
  if(STATE&&STATE.fen)applyState(STATE);
};
applyLanguage();
renderBoard("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
populate();
setInterval(refresh,800);
</script>
</body></html>
"""


def _engine_respond(st):
    with st.lock:
        turn = st.board.turn
        opp_engine = None
        if turn == chess.WHITE and not st.white_human:
            opp_engine = st.white_name
        if turn == chess.BLACK and not st.black_human:
            opp_engine = st.black_name
        game_over = st.board.is_game_over(claim_draw=True)
    if not opp_engine or game_over:
        return
    my_run = st.run_id
    st.thinking = True
    def bg():
        try:
            with st.lock:
                if st.run_id != my_run:
                    return
                if st.nodes:
                    limit = chess.engine.Limit(nodes=st.nodes)
                else:
                    limit = chess.engine.Limit(white_clock=st.clocks["w"], black_clock=st.clocks["b"],
                                               white_inc=st.tc_inc, black_inc=st.tc_inc)
                board_copy = st.board.copy()
                eng_side = st.board.turn
            t0 = time.perf_counter()
            res = run_engine_move(st, opp_engine, board_copy, limit)
            spent = time.perf_counter() - t0
            with st.lock:
                if st.run_id != my_run:
                    return
                key = "w" if eng_side == chess.WHITE else "b"
                if not st.nodes:
                    st.clocks[key] -= spent
                    if st.clocks[key] < 0:
                        st.result = "0-1" if eng_side == chess.WHITE else "1-0"
                        st.end_reason = ("White" if eng_side == chess.WHITE else "Black") + " loses on time"
                        st.status = "finished"
                        st.thinking = False
                        return
                    st.clocks[key] += st.tc_inc
                if res.move is not None and res.move in st.board.legal_moves:
                    san = st.board.san(res.move)
                    st.board.push(res.move)
                    st.last_uci = res.move.uci()
                    st.fen = st.board.fen()
                    st.moves.append(san)
                    st.moves = st.moves[-40:]
                if st.board.is_game_over(claim_draw=True):
                    outcome = st.board.outcome(claim_draw=True)
                    st.result = (outcome.result() if outcome else "1/2-1/2")
                    st.status = "finished"
        except Exception as e:
            with st.lock:
                if st.run_id == my_run:
                    st.last_error = str(e)
        finally:
            with st.lock:
                if st.run_id == my_run:
                    st.thinking = False
    threading.Thread(target=bg, daemon=True).start()


def make_handler():
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split("?", 1)[0]
            st = session_state(self)
            if path == "/" or path.startswith("/index"):
                data = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif path.startswith("/assets/"):
                rel = path[len("/assets/"):]
                base = (HERE / "assets").resolve()
                target = (base / rel).resolve()
                if str(target).startswith(str(base)) and target.is_file():
                    data = target.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(404)
                    self.end_headers()
            elif path.startswith("/pieces/"):
                name = path.rsplit("/", 1)[-1]
                if name in PIECE_FILES:
                    data = (PIECE_DIR / name).read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "image/svg+xml")
                    self.send_header("Cache-Control", "max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                else:
                    self.send_response(404)
                    self.end_headers()
            elif path.startswith("/state.json"):
                record_game(st)
                data = json.dumps(st.snapshot()).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            elif path == "/rankings":
                query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                site = (query.get("site") or ["lichess"])[0]
                perf = (query.get("perf") or ["blitz"])[0]
                try:
                    data = json.dumps(rankings(site, perf)).encode()
                except Exception as exc:
                    data = json.dumps({"error": str(exc), "site": site, "perf": perf, "rows": []}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            elif path == "/settings":
                data = json.dumps({"telemetry": st.telemetry, "endpoint": st.endpoint,
                                   "threads": st.engine_settings["threads"], "hash": st.engine_settings["hash"],
                                   "skill": st.engine_settings["skill"],
                                   "strength": st.engine_settings["strength"],
                                   "elo": st.engine_settings["elo"]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            elif path == "/credits":
                text = ""
                for candidate in (HERE.parent / "CREDITS.md", HERE / "CREDITS.md"):
                    if candidate.exists():
                        text = candidate.read_text()
                        break
                data = (text or "Nexarch is MIT licensed. See CREDITS.md for the full list.").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif path == "/pgn":
                data = pgn_text(st).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/x-chess-pgn; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="nexarch-game.pgn"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif path.startswith("/board.svg"):
                with st.lock:
                    fen = st.fen
                try:
                    svg = chess.svg.board(chess.Board(fen), size=420)
                except Exception:
                    svg = ""
                data = svg.encode()
                self.send_response(200)
                self.send_header("Content-Type", "image/svg+xml")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)
            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            st = session_state(self)
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw or b"{}")
            except Exception:
                body = {}
            if path == "/settings":
                with st.lock:
                    st.telemetry = bool(body.get("telemetry"))
                    st.endpoint = TELEMETRY_URL
                    st.anonymous_id = st.anonymous_id or uuid.uuid4().hex
                    for key in ("threads", "hash"):
                        if key in body:
                            st.engine_settings[key] = max(1, int(body[key]))
                    if "strength" in body or "percent" in body:
                        st.engine_settings["strength"] = clamp_strength(body.get("strength", body.get("percent")))
                    elif "elo" in body:
                        st.engine_settings["strength"] = strength_for_elo(body["elo"])
                    st.engine_settings["elo"] = elo_for_strength(st.engine_settings["strength"])
                    st.engine_settings["skill"] = skill_for_strength(st.engine_settings["strength"])
                    settings = {"telemetry": st.telemetry, "endpoint": st.endpoint,
                                "anonymous_id": st.anonymous_id, **st.engine_settings}
                save_settings(settings)
                st.close_engines()
                with SESSIONS_LOCK:
                    for other in SESSIONS.values():
                        other.telemetry = st.telemetry
                        other.endpoint = st.endpoint
                STATE.telemetry = st.telemetry
                STATE.endpoint = st.endpoint
                self._json({"ok": True, "telemetry": st.telemetry, "endpoint": st.endpoint,
                            **st.engine_settings})
            elif path == "/strength":
                if "strength" in body or "percent" in body:
                    strength = clamp_strength(body.get("strength", body.get("percent")))
                else:
                    strength = strength_for_elo(body.get("elo", MAX_ELO))
                with st.lock:
                    st.engine_settings["strength"] = strength
                    st.engine_settings["elo"] = elo_for_strength(strength)
                    st.engine_settings["skill"] = skill_for_strength(strength)
                    settings = {"telemetry": st.telemetry, "endpoint": st.endpoint,
                                "anonymous_id": st.anonymous_id, **st.engine_settings}
                save_settings(settings)
                st.apply_strength()
                self._json({"ok": True, "strength": strength, "elo": st.engine_settings["elo"],
                            "skill": st.engine_settings["skill"],
                            "settings": dict(st.engine_settings)})
            elif path == "/undo":
                with st.lock:
                    st.run_id += 1
                    st.stop.set()
                    st.thinking = False
                    n = 1 if (st.white_human and st.black_human) else 2
                    n = min(n, len(st.board.move_stack))
                    if n == 0:
                        self._json({"error": "nothing to undo", "state": st.snapshot()}, 400)
                        return
                    for _ in range(n):
                        st.board.pop()
                    st.fen = st.board.fen()
                    st.last_uci = st.board.move_stack[-1].uci() if st.board.move_stack else ""
                    st.moves = []
                    tmp = chess.Board()
                    for mv in st.board.move_stack:
                        st.moves.append(tmp.san(mv))
                        tmp.push(mv)
                    st.status = "playing"
                    st.result = ""
                    st.end_reason = ""
                    st.recorded = False
                    st.engine_info = {}
                    snap = st.snapshot()
                st.stop.clear()
                self._json({"ok": True, "state": snap})
            elif path == "/mp/start":
                with st.lock:
                    st.online = True
                    st.mode = "online"
                    st.online_room = str(body.get("room", ""))
                    st.online_server = str(body.get("server", "")).rstrip("/")
                    st.online_color = "b" if body.get("color") == "b" else "w"
                    st.online_names = {"w": str(body.get("white", "")), "b": str(body.get("black", ""))}
                    st.online_status = "waiting"
                    st.white_name = st.online_names["w"] or "White"
                    st.black_name = st.online_names["b"] or "Black"
                    st.board = chess.Board()
                    st.fen = st.board.fen()
                    st.moves = []
                    st.last_uci = ""
                    st.white_human = st.black_human = True
                    st.clocks = {"w": 0.0, "b": 0.0}
                    st.status = "playing"
                    st.result = ""
                    st.end_reason = ""
                    st.recorded = False
                    snap = st.snapshot()
                self._json({"ok": True, "state": snap})
            elif path == "/mp/apply":
                with st.lock:
                    if not st.online:
                        self._json({"error": "not online"}, 400)
                        return
                    try:
                        apply_online_moves(st, body.get("moves") or [],
                                           str(body.get("white", "")), str(body.get("black", "")))
                    except Exception as exc:
                        self._json({"error": str(exc)}, 400)
                        return
                    if st.online_names["w"] and st.online_names["b"]:
                        st.online_status = "finished" if st.status == "finished" else "playing"
                    else:
                        st.online_status = "waiting"
                    snap = st.snapshot()
                self._json({"ok": True, "state": snap})
            elif path == "/mp/end":
                with st.lock:
                    st.online = False
                    st.online_status = ""
                    st.mode = "idle"
                    st.status = "idle"
                    st.thinking = False
                    snap = st.snapshot()
                self._json({"ok": True, "state": snap})
            elif path == "/move":
                uci = (body.get("uci") or "").strip()
                with st.lock:
                    try:
                        mv = chess.Move.from_uci(uci)
                    except Exception:
                        mv = None
                    if mv is None or mv not in st.board.legal_moves:
                        self._json({"error": "illegal move", "state": st.snapshot()}, 400)
                        return
                    san = st.board.san(mv)
                    st.board.push(mv)
                    st.last_uci = mv.uci()
                    st.fen = st.board.fen()
                    st.moves.append(san)
                    st.moves = st.moves[-40:]
                    st.last_error = ""
                    opp_engine = None
                    turn = st.board.turn
                    if turn == chess.WHITE and not st.white_human:
                        opp_engine = st.white_name
                    if turn == chess.BLACK and not st.black_human:
                        opp_engine = st.black_name
                    game_over = st.board.is_game_over(claim_draw=True)
                if opp_engine and not game_over:
                    _engine_respond(st)
                with st.lock:
                    if st.board.is_game_over(claim_draw=True) and not st.result:
                        outcome = st.board.outcome(claim_draw=True)
                        st.result = (outcome.result() if outcome else "1/2-1/2")
                        st.status = "finished"
                    snap = st.snapshot()
                self._json({"ok": True, "state": snap})
            elif path == "/start":
                white = body.get("white")
                black = body.get("black")
                tc = body.get("tc", "5+0.05")
                nodes = int(body.get("nodes", 0) or 0)
                games = int(body.get("games", 1) or 1)
                st.run_id += 1
                my_run = st.run_id
                st.stop.set()
                if st.thread and st.thread.is_alive():
                    st.thread.join(timeout=5)
                st.close_engines()
                st.stop.clear()
                st.white_name = "Human" if white == "__human__" else white
                st.black_name = "Human" if black == "__human__" else black
                st.white_human = (white == "__human__")
                st.black_human = (black == "__human__")
                st.nodes = nodes
                st.total_games = max(1, games)
                st.current_game = 0
                st.stats = {"w": 0, "d": 0, "l": 0, "done": 0}
                base, _, inc = str(tc).partition("+")
                try:
                    st.tc_base = float(base)
                except Exception:
                    st.tc_base = 5.0
                try:
                    st.tc_inc = float(inc) if inc else 0.0
                except Exception:
                    st.tc_inc = 0.0
                st.reset_board()
                st.status = "playing"
                st.result = ""
                st.thinking = False
                st.mode = "match" if (not st.white_human or not st.black_human) and games > 1 else "human"
                if st.white_human and st.black_human:
                    st.mode = "human"
                    st.status = "playing"
                    self._json({"ok": True, "state": st.snapshot()})
                    return
                if st.white_human or st.black_human:
                    st.mode = "human"
                    st.total_games = 1
                    st.thread = None
                    if not st.white_human:
                        def first():
                            time.sleep(0.3)
                            _engine_respond(st)
                        threading.Thread(target=first, daemon=True).start()
                    self._json({"ok": True, "state": st.snapshot()})
                    return
                st.mode = "match"
                st.thread = threading.Thread(target=run_match, args=(st, my_run), daemon=True)
                st.thread.start()
                self._json({"ok": True, "state": st.snapshot()})
            elif path == "/restart":
                st.run_id += 1
                st.stop.set()
                if st.thread and st.thread.is_alive():
                    st.thread.join(timeout=5)
                st.close_engines()
                st.stop.clear()
                st.thread = None
                st.thinking = False
                st.reset_board()
                st.status = "idle"
                st.result = ""
                st.mode = "idle"
                st.current_game = 0
                self._json({"ok": True, "state": st.snapshot()})
            elif path == "/stop":
                st.run_id += 1
                st.stop.set()
                st.thinking = False
                st.status = "idle"
                st.mode = "idle"
                self._json({"ok": True, "state": st.snapshot()})
            else:
                self.send_response(404)
                self.end_headers()

        def _json(self, obj, code=200):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    return Handler


def public_ip():
    try:
        return urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--engines", default=DEFAULT_ENGINES if os.path.exists(DEFAULT_ENGINES) else CUTECHESS_ENGINES)
    ap.add_argument("--open", action="store_true", help="open the board in the default browser")
    args = ap.parse_args()

    STATE.engines = load_engines(args.engines)
    ENGINES.extend(STATE.engines)
    if not STATE.engines:
        print("No engines loaded; check --engines path", file=sys.stderr)

    Handler = make_handler()
    httpd = http.server.ThreadingHTTPServer((args.host, args.port), Handler)
    httpd.allow_reuse_address = True
    print(f"Nexarch Chess listening on http://{args.host}:{args.port}/")
    print("Engines:", ", ".join(e["name"] for e in STATE.engines) or "(none)")
    if args.open:
        import webbrowser
        threading.Timer(0.5, lambda: webbrowser.open(f"http://127.0.0.1:{args.port}/")).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        STATE.stop.set()
        STATE.close_engines()
        httpd.server_close()


if __name__ == "__main__":
    main()