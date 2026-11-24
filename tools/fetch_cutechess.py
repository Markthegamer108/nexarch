#!/usr/bin/env python3
"""Download the official Cute Chess 1.5.1 release used by the Nexarch installer."""
import argparse
import hashlib
import pathlib
import shutil
import sys
import urllib.request
import zipfile

ASSETS = {
    "Cute_Chess-1.5.1-x86_64.AppImage": (
        "https://github.com/cutechess/cutechess/releases/download/v1.5.1/Cute_Chess-1.5.1-x86_64.AppImage",
        "d9448693e45bd57f1aeb32c46e94466894cd7cc5b6937effd285a02e871387b5",
    ),
    "cutechess-1.5.1-win64.zip": (
        "https://github.com/cutechess/cutechess/releases/download/v1.5.1/cutechess-1.5.1-win64.zip",
        "048942ca3473db860cb914fe94108da37051f693f47e368688ec6ec450f924bc",
    ),
    "cutechess-1.5.1.tar.gz": (
        "https://github.com/cutechess/cutechess/archive/refs/tags/v1.5.1.tar.gz",
        "",
    ),
}


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 24), b""):
            h.update(block)
    return h.hexdigest()


def download(url, path):
    if path.exists():
        return
    print(f"downloading {url}")
    tmp = path.with_suffix(path.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as r, tmp.open("wb") as f:
        shutil.copyfileobj(r, f)
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", default=str(pathlib.Path(__file__).resolve().parent.parent / "gui" / "cutechess"))
    args = ap.parse_args()
    dest = pathlib.Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    for name, (url, expected) in ASSETS.items():
        path = dest / name
        download(url, path)
        digest = sha256(path)
        if expected and digest != expected:
            sys.exit(f"{name}: SHA-256 {digest} does not match {expected}")
        print(f"{name}: {digest}")
    zip_path = dest / "cutechess-1.5.1-win64.zip"
    folder = dest / "cutechess-1.5.1-win64"
    if not folder.exists():
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(dest)
        print(f"extracted {folder}")


if __name__ == "__main__":
    main()
