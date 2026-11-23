#!/usr/bin/env python3
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

DATA = os.environ.get("COLAB_DATA", "/content/nexarch/data")
OUT = os.environ.get("COLAB_OUT", "/content/drive/MyDrive/nexarch")
HIDDEN = int(os.environ.get("COLAB_HIDDEN", "2048"))
BUDGET = int(os.environ.get("COLAB_BUDGET", "420"))
BATCH = int(os.environ.get("COLAB_BATCH", "8192"))
LR = os.environ.get("COLAB_LR", "0.0006")
KEEP_FREE = float(os.environ.get("COLAB_KEEP_GB", "10"))
OWNER = "markthegamer108"
REPO = "https://github.com/Markthegamer108/nexarch.git"
SOURCES = [
    ("nexarch-selfplay-2026-11-22", "selfplay-*.bin"),
    ("nexarch-graded-g3", "graded-g3-full.bin"),
    ("nexarch-fishnet-2025-01", "fishnet-*.bin"),
    ("nexarch-t80-2024-02-feb", "t80-*.bin"),
    ("nexarch-t80-2024-03-mar", "t80-*.bin"),
    ("nexarch-t80-2024-01-jan", "t80-*.bin"),
    ("nexarch-lichess-evals", "lichess-*.bin"),
]


def say(msg):
    print(time.strftime("%H:%M:%S") + " " + msg, flush=True)


def sh(cmd, cwd=None):
    say("$ " + cmd)
    if subprocess.call(cmd, shell=True, cwd=cwd):
        raise SystemExit("failed: " + cmd)


def token():
    for p in (os.path.expanduser("~/.kaggle/access_token"), "/root/.kaggle/access_token"):
        if os.path.exists(p):
            return open(p).read().strip()
    raise SystemExit("no Kaggle token: run the setup cell first")


def api(path):
    req = urllib.request.Request("https://www.kaggle.com/api/v1/" + path, headers={"Authorization": "Bearer " + token()})
    return json.load(urllib.request.urlopen(req, timeout=120))


def files_of(slug):
    meta = api(f"datasets/list/{OWNER}/{slug}")
    out = []
    for f in meta.get("datasetFiles", []):
        out.append((f["name"], int(f.get("totalBytes") or 0)))
    return out


def fetch(slug, name, path, size):
    if os.path.exists(path) and os.path.getsize(path) == size:
        return
    url = f"https://www.kaggle.com/api/v1/datasets/download/{OWNER}/{slug}/{name}"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token()})
    done = 0
    t = time.time()
    with urllib.request.urlopen(req, timeout=600) as r, open(path + ".part", "wb") as out:
        while True:
            block = r.read(1 << 23)
            if not block:
                break
            out.write(block)
            done += len(block)
            if done % (1 << 30) < (1 << 23):
                say(f"  {name}: {done / 1e9:.1f}/{size / 1e9:.1f} GB at {done / max(time.time() - t, 1e-9) / 1e6:.0f} MB/s")
    os.replace(path + ".part", path)


def prepare():
    os.makedirs(DATA, exist_ok=True)
    free = shutil.disk_usage("/content").free / 1e9 - KEEP_FREE
    say(f"free disk for data: {free:.1f} GB")
    kept, used = [], 0.0
    for slug, pattern in SOURCES:
        found = [(n, s) for n, s in files_of(slug) if fnmatch.fnmatch(n, pattern)]
        need = sum(s for _, s in found) / 1e9
        if used + need > free:
            say(f"skipping {slug} ({need:.1f} GB) to stay inside the disk budget")
            continue
        dst = os.path.join(DATA, slug)
        os.makedirs(dst, exist_ok=True)
        for name, size in found:
            say(f"{slug}/{name} ({size / 1e9:.1f} GB)")
            fetch(slug, name, os.path.join(dst, name), size)
            kept.append(os.path.join(dst, name))
        used += need
    if not kept:
        raise SystemExit("nothing downloaded")
    say(f"data ready: {used:.1f} GB in {len(kept)} file(s)")
    return kept


def main():
    say("GPU: " + subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                                 capture_output=True, text=True).stdout.strip())
    if not os.path.isdir("/content/nexarch/.git"):
        sh(f"git clone -q --depth 1 {REPO} /content/nexarch")
    else:
        sh("git fetch -q --depth 1 origin main && git reset -q --hard origin/main", cwd="/content/nexarch")
    os.chdir("/content/nexarch")
    os.makedirs(OUT, exist_ok=True)
    state = os.path.join(OUT, f"g5-h{HIDDEN}.pt")
    if not os.path.exists(state):
        src = f"/content/nexarch/nets/nexarch-g5-h{HIDDEN}-start.pt"
        if not os.path.exists(src):
            sh(f"python -m pip -q install kaggle && python -m kaggle datasets download -d {OWNER}/nexarch-g5-starts -p /content/starts --unzip -q")
            src = f"/content/starts/nexarch-g5-h{HIDDEN}-start.pt"
        shutil.copy(src, state)
        say(f"starting from {src}")
    else:
        say(f"resuming from {state}")
    data = prepare()
    cmd = ["python", "trainer/train.py"]
    for f in data:
        cmd += ["--data", f]
    cmd += ["--resume", state, "--hidden", str(HIDDEN), "--batch", str(BATCH), "--lr", LR,
            "--epochs", "8", "--wdl", "0.4", "--time-budget", str(BUDGET), "--out", os.path.join(OUT, f"g5-h{HIDDEN}.nnue")]
    t = time.time()
    say("training " + " ".join(cmd[-12:]))
    if subprocess.call(cmd):
        raise SystemExit("training failed")
    say(f"finished in {(time.time() - t) / 60:.0f} min, checkpoint at {state}")


if __name__ == "__main__":
    main()
