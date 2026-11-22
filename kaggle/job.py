#!/usr/bin/env python3
import argparse
import base64
import io
import json
import pathlib
import subprocess
import sys
import tarfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OWNER = "markthegamer108"
INCLUDE = ["engine/Makefile", "engine/src", "trainer", "tools", "kaggle/job.py", "kaggle/setup-engines.sh", "kaggle/lc0-setup.sh", "kaggle/train-g3.sh", "kaggle/train-g4.sh", "kaggle/confirm-g4.sh", "nets"]
SKIP_SUFFIX = {".pt", ".pyc", ".bin"}

TEMPLATE = '''#!/usr/bin/env python3
import base64, io, json, os, subprocess, sys, tarfile, time

PLAN = json.loads(%(plan)r)
BUNDLE = %(bundle)r
SRC = "/tmp/nexarch"
OUT = "/kaggle/working"
LOG = open(os.path.join(OUT, "run.log"), "a", buffering=1)


def say(msg):
    line = time.strftime("%%H:%%M:%%S ") + msg
    print(line, flush=True)
    LOG.write(line + "\\n")


def sh(cmd):
    say("$ " + cmd)
    p = subprocess.Popen(cmd, shell=True, cwd=SRC, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
                         executable="/bin/bash")
    for line in p.stdout:
        print(line, end="", flush=True)
        LOG.write(line)
    if p.wait() != 0:
        say("command failed with exit code %%d" %% p.returncode)
        sys.exit(p.returncode)


os.makedirs(SRC, exist_ok=True)
archive = tarfile.open(fileobj=io.BytesIO(base64.b64decode(BUNDLE)), mode="r:gz")
try:
    archive.extractall(SRC, filter="data")
except TypeError:
    archive.extractall(SRC)
say("job: " + PLAN["name"])
sh("nproc; lscpu | grep -E 'Model name'; grep -o -m1 -w -E 'avx2|bmi2|avx512f' /proc/cpuinfo | sort -u | tr '\\\\n' ' '; echo; free -g | head -2; (nvidia-smi -L || true)")
sh("make -C engine -j4 >/dev/null && ./engine/nexarch perftsuite")
for command in PLAN["commands"]:
    sh(command.replace("{cpus}", str(os.cpu_count())).replace("{out}", OUT))
say("job finished")
'''


def bundle():
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for item in INCLUDE:
            path = ROOT / item
            files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
            for f in files:
                rel = f.relative_to(ROOT)
                if f.suffix in SKIP_SUFFIX or "__pycache__" in rel.parts or "lib" in rel.parts[:-1]:
                    continue
                if f.stat().st_size > 400_000:
                    print(f"job.py: not bundling {rel} ({f.stat().st_size // 1024} KiB)", file=sys.stderr)
                    continue
                if f.parent.name == "nets" and f.suffix == ".nnue" and not f.name.startswith("nexarch-g"):
                    continue
                tar.add(f, arcname=str(f.relative_to(ROOT)))
    return base64.b64encode(buf.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--cmd", action="append", required=True)
    ap.add_argument("--gpu", action="store_true", help="2x T4")
    ap.add_argument("--internet", action="store_true")
    ap.add_argument("--dataset", action="append", default=[])
    ap.add_argument("--source", action="append", default=[], help="kernel whose output to mount")
    ap.add_argument("--dir", default=None, help="where to write the job (default kaggle/jobs/NAME)")
    ap.add_argument("--push", action="store_true")
    args = ap.parse_args()

    out = pathlib.Path(args.dir or ROOT / "kaggle" / "jobs" / args.name)
    out.mkdir(parents=True, exist_ok=True)
    plan = json.dumps({"name": args.name, "commands": args.cmd})
    (out / f"{args.name}.py").write_text(TEMPLATE % {"plan": plan, "bundle": bundle()})
    meta = {
        "id": f"{OWNER}/{args.name}",
        "title": args.name,
        "code_file": f"{args.name}.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": args.gpu,
        "enable_tpu": False,
        "enable_internet": args.internet,
        "dataset_sources": args.dataset,
        "kernel_sources": args.source,
        "competition_sources": [],
        "model_sources": [],
    }
    if args.gpu:
        meta["machine_shape"] = "NvidiaTeslaT4"
    (out / "kernel-metadata.json").write_text(json.dumps(meta, indent=2))
    size = (out / f"{args.name}.py").stat().st_size
    print(f"wrote {out} ({size / 1024:.0f} KiB)")
    if args.push:
        kaggle = ROOT / ".venv" / "bin" / "kaggle"
        sys.exit(subprocess.call([str(kaggle), "kernels", "push", "-p", str(out)]))


if __name__ == "__main__":
    main()
