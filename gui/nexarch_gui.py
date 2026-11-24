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


def read_settings():
    out = {"telemetry": False, "endpoint": "", "anonymous_id": "", "threads": 1, "hash": 64, "skill": 20}
    try:
        data = json.loads(GUI_CONFIG.read_text())
        out.update({k: data[k] for k in out if k in data})
    except Exception:
        pass
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
        self.endpoint = settings["endpoint"]
        self.anonymous_id = settings["anonymous_id"]
        self.engine_settings = {"threads": int(settings.get("threads", 1)),
                                "hash": int(settings.get("hash", 64)),
                                "skill": int(settings.get("skill", 20))}
        self.engine_info = {}
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
        self.engine_handles[name] = eng
        return eng

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
.tb{border:1px solid #a8a8a8;background:linear-gradient(#fdfdfd,#e3e3e3);padding:4px 10px;font:12px "Segoe UI",Tahoma,sans-serif;color:#111;cursor:pointer;border-radius:2px}
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
.brand{display:flex;align-items:center;gap:7px}
.logo{width:18px;height:18px;display:inline-block}
.tagline{color:#666;font-size:11px;font-weight:400}
.ico{width:14px;height:14px;vertical-align:-2px;margin-right:4px}
.dest{background:#fff;border:1px solid #bdbdbd;padding:6px 8px;font-size:12px;color:#333;margin:2px 0 10px}
.rankTabs{display:flex;gap:6px;margin-bottom:8px}
.rankTabs .tb{flex:1}
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
  .tb{padding:4px 8px;font-size:11px}
  .board{max-height:calc(100vw - 12px)}
}
</style>
</head><body>
<div class="app">
  <div class="titlebar"><span class="brand"><img class="logo" src="/assets/cutechess/cutechess_32x32.png" alt="">Nexarch Arena</span><span class="tagline">online companion &middot; engines and settings</span></div>
  <div class="toolbar">
    <button class="tb default" id="newGameBtn"><img class="ico" src="/assets/cutechess/toolbutton/add_16x16.png" alt="">New Game</button>
    <button class="tb" id="restartBtn"><img class="ico" src="/assets/cutechess/toolbutton/clone_16x16.png" alt="">Restart</button>
    <button class="tb" id="stopBtn"><img class="ico" src="/assets/cutechess/toolbutton/remove_16x16.png" alt="">Stop</button>
    <button class="tb" id="undoBtn"><img class="ico" src="/assets/cutechess/toolbutton/previous_16x16.png" alt="">Undo</button>
    <span class="sep"></span>
    <button class="tb" id="settingsBtn"><img class="ico" src="/assets/cutechess/toolbutton/configure_16x16.png" alt="">Settings</button>
    <button class="tb" id="rankingsBtn">Rankings</button>
    <button class="tb" id="creditsBtn">Credits</button>
    <button class="tb" id="pgnBtn">PGN</button>
    <span class="sep"></span>
    <span class="gameinfo" id="gameInfo">No game</span>
  </div>
  <div class="main">
    <div class="boardarea">
      <div class="player"><span class="name"><span class="sw black"></span><span id="blackName">Black</span></span><span class="clock" id="blackClock">5:00.0</span></div>
      <div class="board" id="board"></div>
      <div class="player"><span class="name"><span class="sw white"></span><span id="whiteName">White</span></span><span class="clock" id="whiteClock">5:00.0</span></div>
      <div class="banner" id="endBanner"></div>
    </div>
    <div class="dock">
      <div class="tabstrip"><span class="tab active">Moves</span><span class="tab">Info</span></div>
      <div class="moves" id="moves">No moves yet.</div>
      <div class="dockinfo">
        <div><b>Status</b><span id="statusText">Idle</span></div>
        <div><b>Result</b><span id="result">-</span></div>
        <div><b>Score</b><span id="score">+0 =0 -0</span></div>
      </div>
    </div>
  </div>
  <div class="statusbar"><span class="grow" id="statusMessage">Ready</span><span id="enginesLabel">-</span><span class="credit">Engine: Nexarch (MIT) &middot; GUI: GPL-3.0 &middot; Pieces: Cburnett CC BY-SA 3.0</span></div>
</div>

<div class="modal" id="settingsModal">
  <div class="dialog">
    <div class="dialogTitle">Settings</div>
    <div class="dialogBody">
      <label class="check"><input type="checkbox" id="telemetry"><span>Anonymous game collection</span></label>
      <p class="hint">Off by default. When enabled, finished games against Nexarch are saved on this computer and sent to the endpoint below. No account name, email address or hardware ID is included.</p>
      <label><span>Upload endpoint (optional)</span><input id="endpoint" placeholder="https://example.com/nexarch-games"></label>
      <div class="dest" id="dest">Saved on this computer only</div>
      <div class="dialogRow">
        <label><span>Threads</span><input id="threads" type="number" min="1" max="64" value="1"></label>
        <label><span>Hash (MB)</span><input id="hash" type="number" min="1" max="65536" value="64"></label>
      </div>
      <label><span>Skill level (0-20)</span><input id="skill" type="number" min="0" max="20" value="20"></label>
      <div class="error" id="settingsErr" style="display:none"></div>
    </div>
    <div class="dialogButtons">
      <button class="tb" id="settingsCancel">Cancel</button>
      <button class="tb default" id="settingsSave">Save</button>
    </div>
  </div>
</div>

<div class="modal" id="creditsModal">
  <div class="dialog" style="width:620px;max-width:calc(100vw - 24px)">
    <div class="dialogTitle">Credits</div>
    <div class="dialogBody"><pre id="creditsText" style="max-height:60vh;overflow:auto;white-space:pre-wrap;font:12px/1.55 Consolas,monospace;margin:0"></pre></div>
    <div class="dialogButtons"><button class="tb" id="creditsClose">Close</button></div>
  </div>
</div>

<div class="modal" id="rankingsModal">
  <div class="dialog" style="width:560px;max-width:calc(100vw - 24px)">
    <div class="dialogTitle">Live rankings</div>
    <div class="dialogBody">
      <div class="rankTabs">
        <button class="tb on" id="rankLichess">Lichess</button>
        <button class="tb" id="rankChesscom">Chess.com</button>
      </div>
      <div class="dialogRow" style="grid-template-columns:1fr">
        <label><span>Time control</span><select id="perfSel">
          <option value="bullet">Bullet</option>
          <option value="blitz" selected>Blitz</option>
          <option value="rapid">Rapid</option>
          <option value="classical">Classical</option>
        </select></label>
      </div>
      <table class="ranks"><thead><tr><th>#</th><th>Player</th><th>Title</th><th style="text-align:right">Rating</th></tr></thead><tbody id="rankRows"><tr><td colspan="4">Loading...</td></tr></tbody></table>
      <div class="error" id="rankErr" style="display:none"></div>
    </div>
    <div class="dialogButtons"><button class="tb" id="rankClose">Close</button></div>
  </div>
</div>

<div class="modal" id="newGameModal">
  <div class="dialog">
    <div class="dialogTitle">New Game</div>
    <div class="dialogBody">
      <label><span>White</span><select id="whiteSel"></select></label>
      <label><span>Black</span><select id="blackSel"></select></label>
      <div class="dialogRow">
        <label><span>Time control</span><input id="tc" value="5+0.05"></label>
        <label><span>Nodes</span><input id="nodes" value="0"></label>
      </div>
      <label><span>Games</span><input id="games" value="1"></label>
      <div class="error" id="errRow" style="display:none"><span id="err"></span></div>
    </div>
    <div class="dialogButtons">
      <button class="tb" id="cancelBtn">Cancel</button>
      <button class="tb default" id="okBtn">OK</button>
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
  fetch(api("/move"),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({uci:uci})})
    .then(function(r){return r.json();})
    .then(function(d){if(d.error){showError(d.error);selected=null;refresh();return;}if(d.state)applyState(d.state);})
    .catch(function(){showError("Network error");});
}
function showError(msg){document.getElementById("err").textContent=msg;document.getElementById("errRow").style.display="block";}
function fmtClock(t){t=Math.max(0,t);var m=Math.floor(t/60),s=t-m*60;return m+":"+(s<10?"0":"")+s.toFixed(1);}
function fmtMoves(moves){
  if(!moves||!moves.length)return "No moves yet.";
  var out=[];
  for(var i=0;i<moves.length;i+=2)out.push((i/2+1)+". "+moves[i]+(moves[i+1]?" "+moves[i+1]:""));
  return out.join("\n");
}
function applyState(s){
  STATE=s;
  sideHuman={w:!!s.white_human,b:!!s.black_human};
  var st="Idle", cls="";
  if(s.status==="playing"){
    st=s.thinking?"Thinking...":"Playing";
    if(s.check)st+=" (check)";
  }
  if((s.status==="finished"||s.status==="between_games")&&(s.termination||s.end_reason)){
    if(s.end_reason){
      st=s.end_reason;
      cls=s.end_reason.indexOf("loses")>=0?"loss":"win";
    }else if(s.termination==="checkmate"){
      st=(s.winner==="w"?"White":"Black")+" mates";
      cls="win";
    }else if(s.termination==="stalemate"){
      st="Draw by stalemate";
    }else if(s.termination==="insufficient_material"){
      st="Draw by insufficient mating material";
    }else if(s.termination==="fifty_moves"){
      st="Draw by fifty moves rule";
    }else if(s.termination==="threefold_repetition"){
      st="Draw by 3-fold repetition";
    }else if(s.termination==="seventyfive_moves"){
      st="Draw by seventy-five moves rule";
    }else if(s.termination==="fivefold_repetition"){
      st="Draw by fivefold repetition";
    }else{
      st="Draw by "+s.termination.replace(/_/g," ");
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
  document.getElementById("whiteName").textContent=bothHuman?"White":(s.white_name||"White");
  document.getElementById("blackName").textContent=bothHuman?"Black":(s.black_name||"Black");
  document.getElementById("whiteClock").textContent=fmtClock(s.clocks.w);
  document.getElementById("blackClock").textContent=fmtClock(s.clocks.b);
  document.getElementById("score").textContent="+"+s.stats.w+" = "+s.stats.d+" - "+s.stats.l;
  document.getElementById("result").textContent=s.result?((s.winner?(s.winner==="w"?"White":"Black")+" wins · ":"Draw · ")+s.result):"-";
  document.getElementById("moves").textContent=fmtMoves(s.moves);
  document.getElementById("gameInfo").textContent=s.white_name&&s.black_name?(s.white_name+" vs "+s.black_name+(s.nodes?" ("+s.nodes+" nodes)":" ("+s.tc_base+"s+"+s.tc_inc+"s)")):"No game";
  document.getElementById("enginesLabel").textContent="Engines: "+((s.engines||[]).join(", ")||"-");
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
    var h=document.createElement("option");h.value="__human__";h.textContent="Human";
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
    .catch(function(){showError("Network error");});
}
function restartGame(){fetch(api("/restart"),{method:"POST"}).then(function(){refresh();});}
function stopGame(){fetch(api("/stop"),{method:"POST"}).then(function(){refresh();});}
var settingsModal=document.getElementById("settingsModal");
var creditsModal=document.getElementById("creditsModal");
function updateDest(){
  var on=document.getElementById("telemetry").checked;
  var ep=document.getElementById("endpoint").value.trim();
  document.getElementById("dest").textContent=!on?"Anonymous game collection is off":(ep?"Games will be sent to: "+ep:"Games will be saved on this computer only (no endpoint set)");
}
document.getElementById("telemetry").onchange=updateDest;
document.getElementById("endpoint").oninput=updateDest;
document.getElementById("settingsBtn").onclick=function(){
  fetch(api("/settings")).then(function(r){return r.json();}).then(function(s){
    document.getElementById("telemetry").checked=!!s.telemetry;
    document.getElementById("endpoint").value=s.endpoint||"";
    document.getElementById("threads").value=s.threads||1;
    document.getElementById("hash").value=s.hash||64;
    document.getElementById("skill").value=(s.skill===undefined?20:s.skill);
    updateDest();
    settingsModal.classList.add("open");
  }).catch(function(){showError("Network error");});
};
document.getElementById("settingsCancel").onclick=function(){settingsModal.classList.remove("open");};
settingsModal.onclick=function(e){if(e.target===this)settingsModal.classList.remove("open");};
document.getElementById("settingsSave").onclick=function(){
  fetch(api("/settings"),{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({telemetry:document.getElementById("telemetry").checked,
                         endpoint:document.getElementById("endpoint").value,
                         threads:document.getElementById("threads").value,
                         hash:document.getElementById("hash").value,
                         skill:document.getElementById("skill").value})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.error){document.getElementById("settingsErr").textContent=d.error;document.getElementById("settingsErr").style.display="block";return;}
      settingsModal.classList.remove("open");
    }).catch(function(){showError("Network error");});
};
document.getElementById("creditsBtn").onclick=function(){
  fetch(api("/credits")).then(function(r){return r.text();}).then(function(t){
    document.getElementById("creditsText").textContent=t;
    creditsModal.classList.add("open");
  }).catch(function(){showError("Network error");});
};
document.getElementById("creditsClose").onclick=function(){creditsModal.classList.remove("open");};
creditsModal.onclick=function(e){if(e.target===this)creditsModal.classList.remove("open");};
document.getElementById("pgnBtn").onclick=function(){window.location=api("/pgn");};
document.getElementById("undoBtn").onclick=function(){
  fetch(api("/undo"),{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"})
    .then(function(r){return r.json();}).then(function(d){
      if(d.error){showError(d.error);return;}
      if(d.state)applyState(d.state);
    }).catch(function(){showError("Network error");});
};
var rankSite="lichess";
var rankingsModal=document.getElementById("rankingsModal");
function loadRankings(){
  var perf=document.getElementById("perfSel").value;
  document.getElementById("rankRows").innerHTML='<tr><td colspan="4">Loading...</td></tr>';
  document.getElementById("rankErr").style.display="none";
  fetch(api("/rankings?site="+encodeURIComponent(rankSite)+"&perf="+encodeURIComponent(perf)))
    .then(function(r){return r.json();}).then(function(d){
      if(d.error){document.getElementById("rankErr").textContent=d.error;document.getElementById("rankErr").style.display="block";}
      var rows=(d.rows||[]).map(function(x,i){
        return "<tr><td>"+(i+1)+"</td><td>"+escapeHtml(x.name||"")+"</td><td>"+escapeHtml(x.title||"")+"</td><td class='num'>"+x.rating+"</td></tr>";
      }).join("");
      document.getElementById("rankRows").innerHTML=rows||'<tr><td colspan="4">No rows</td></tr>';
    }).catch(function(e){document.getElementById("rankErr").textContent="Network error";document.getElementById("rankErr").style.display="block";});
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
document.getElementById("newGameBtn").onclick=openDialog;
document.getElementById("okBtn").onclick=startGame;
document.getElementById("cancelBtn").onclick=closeDialog;
document.getElementById("restartBtn").onclick=restartGame;
document.getElementById("stopBtn").onclick=stopGame;
document.getElementById("newGameModal").onclick=function(e){if(e.target===this)closeDialog();};
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
                                   "skill": st.engine_settings["skill"]}).encode()
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
                    st.endpoint = str(body.get("endpoint", "")).strip()
                    st.anonymous_id = st.anonymous_id or uuid.uuid4().hex
                    for key in ("threads", "hash", "skill"):
                        if key in body:
                            st.engine_settings[key] = max(1, int(body[key]))
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