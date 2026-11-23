#!/usr/bin/env python3
import html
import os
import pathlib
import re
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
AWS = "ssh -i ~/.ssh/nexarch-lightsail.pem -o BatchMode=yes -o ConnectTimeout=8 ubuntu@51.20.43.92"
KAGGLE = str(ROOT / ".venv" / "bin" / "kaggle")


def sh(cmd, timeout=90):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ""


def aws():
    out = sh(f"{AWS} 'tail -1 ~/nexarch/kaggle-out/aws-selfplay.log; du -sb ~/nexarch/data/aws; ls ~/nexarch/data/aws | wc -l'", 40)
    lines = out.splitlines()
    log = lines[0] if lines else ""
    size = int(lines[1].split()[0]) if len(lines) > 1 and lines[1].split() else 0
    chunks = int(lines[2]) if len(lines) > 2 and lines[2].strip().isdigit() else 0
    rate = int(re.search(r"\((\d+) pos/s\)", log).group(1)) if re.search(r"\((\d+) pos/s\)", log) else 0
    games = re.search(r"games (\d+)", log)
    return {"log": log, "size": size, "chunks": chunks, "rate": rate, "games": int(games.group(1)) if games else 0,
            "up": bool(out)}


def positions(path):
    p = ROOT / path
    return p.stat().st_size // 32 if p.exists() else 0


def quota():
    out = sh(f"{KAGGLE} quota")
    m = re.search(r"^GPU\s+(\S+)\s+(\S+)", out, re.M)
    return (m.group(1), m.group(2)) if m else ("?", "?")


def kernel(name):
    out = sh(f"{KAGGLE} kernels status markthegamer108/{name}", 60)
    m = re.search(r'"KernelWorkerStatus\.([A-Z_]+)"', out)
    return m.group(1) if m else "?"


def audit():
    env = dict(os.environ, G5_INPUT=str(ROOT))
    try:
        out = subprocess.run([str(ROOT / ".venv" / "bin" / "python"), str(ROOT / "kaggle" / "audit-g5.py")],
                             capture_output=True, text=True, env=env, timeout=120).stdout
    except Exception:
        return 0, "?"
    m = re.search(r"total\s+\d+ file\(s\)\s+([\d,]+) positions", out)
    verdict = "PASS" if re.search(r"audit PASS", out) else "FAIL"
    return (int(m.group(1).replace(",", "")) if m else 0), verdict


def bar(value, target, width=220):
    pct = max(0.0, min(1.0, value / target if target else 0))
    return (f'<div class="bar"><div class="fill" style="width:{pct * 100:.1f}%"></div></div>'
            f'<div class="sub">{value:,} of {target:,}</div>')


def main():
    a = aws()
    local_day = positions("data/data-g4a-day-local.bin")
    pool, verdict = audit()
    used, left = quota()
    grades = kernel("nexarch-grade-selfplay-lc0")
    smoke = kernel("nexarch-smoke-g5")
    now = time.strftime("%a %d %b, %H:%M %Z")
    aws_today = a["size"] // 32
    per_day = a["rate"] * 86400
    rows = [
        ("Self-play, AWS Stockholm", f"{a['rate']} pos/s", f"{aws_today:,} today, {per_day / 1e6:.1f}M/day", a["up"]),
        ("Self-play, laptop", "1 chunk loop", f"{local_day:,} today", True),
        ("Self-play, 5 Kaggle CPU shards", "12 h window", "ends 19:45", True),
        ("Lc0 grading, 20M sample", grades, "finishes ~02:00", grades == "RUNNING"),
        ("Gen 5 smoke test", smoke, "45 min, both widths", smoke in ("RUNNING", "QUEUED")),
    ]
    cards = [
        ("Training pool", f"{pool / 1e9:.2f}B", "positions, audited" if verdict == "PASS" else "audit pending"),
        ("AWS output", f"{per_day / 1e6:.0f}M", f"positions/day at {a['rate']} pos/s"),
        ("Kaggle GPU", f"{left}", f"left of 30h, resets Sat"),
        ("Next milestone", "Gen 5", "h4096 + h2048 on 2.6B"),
    ]
    tr = "\n".join(
        f"<tr><td>{html.escape(n)}</td><td class=m>{html.escape(v)}</td><td class=d>{html.escape(d)}</td>"
        f"<td><span class='dot {'on' if ok else 'off'}'></span></td></tr>"
        for n, v, d, ok in rows)
    tcards = "\n".join(
        f"<div class=card><div class=k>{html.escape(k)}</div><div class=v>{html.escape(v)}</div>"
        f"<div class=sub>{html.escape(s)}</div></div>" for k, v, s in cards)
    doc = f"""<!doctype html>
<html lang=en><head><meta charset=utf-8><title>Nexarch status</title>
<style>
:root {{ color-scheme: only light; }}
body {{ font: 15px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0; padding: 48px 32px 64px;
        background: #fbfbfa; color: #16161a; }}
h1 {{ font-size: 26px; font-weight: 620; letter-spacing: -.02em; margin: 0 0 4px; }}
.when {{ color: #8b8b96; font-size: 13px; margin-bottom: 32px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin-bottom: 34px; }}
.card {{ border: 1px solid #e4e4e0; border-radius: 10px; padding: 16px 18px; background: #fff; }}
.k {{ font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #8b8b96; }}
.v {{ font-size: 30px; font-weight: 600; letter-spacing: -.02em; margin-top: 6px; font-variant-numeric: tabular-nums; }}
.sub {{ font-size: 12.5px; color: #8b8b96; margin-top: 4px; font-variant-numeric: tabular-nums; }}
h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: #8b8b96; margin: 0 0 10px; font-weight: 600; }}
.tbl {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e4e4e0; border-radius: 10px; overflow: hidden; }}
th, td {{ text-align: left; padding: 12px 16px; font-size: 14px; }}
th {{ font-size: 11.5px; text-transform: uppercase; letter-spacing: .07em; color: #8b8b96; font-weight: 600; }}
td {{ border-top: 1px solid #ecece8; }}
.m {{ font-variant-numeric: tabular-nums; font-weight: 550; }}
.d {{ color: #8b8b96; font-size: 13px; }}
.dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; }}
.on {{ background: #3aa35b; }} .off {{ background: #c9c9c2; }}
.bar {{ height: 4px; border-radius: 2px; background: #ecece8; overflow: hidden; }}
.fill {{ height: 100%; background: #16161a; }}
.note {{ margin-top: 26px; font-size: 13px; color: #8b8b96; }}
</style></head><body>
<h1>Nexarch</h1>
<div class=when>{now} &middot; Gen 4 champion, 271 Elo over Gen 3</div>
<div class=cards>{tcards}</div>
<h2>Pipeline</h2>
<table class=tbl><tr><th>Stage</th><th>Rate</th><th>Detail</th><th></th></tr>{tr}</table>
<div class=note>Pool is the audited Gen 5 input set; today's self-play is added when it merges at 19:55.</div>
</body></html>"""
    out = ROOT / "kaggle-out" / "status.html"
    out.write_text(doc)
    print(out)


if __name__ == "__main__":
    main()
