#!/usr/bin/env python3
"""Remove a Nexarch installation, its shortcuts and its uninstall entry."""
import argparse
import os
import shutil
import sys
from pathlib import Path


def remove(path):
    try:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
    except FileNotFoundError:
        pass
    except Exception as exc:
        print(f"could not remove {path}: {exc}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--keep-data", action="store_true")
    args = ap.parse_args()
    prefix = Path(args.prefix).expanduser()
    if not args.yes:
        answer = input(f"Remove Nexarch from {prefix}? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            print("Cancelled.")
            return
    home = Path.home()
    remove(prefix)
    if os.name == "nt":
        try:
            import winreg
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Nexarch")
        except Exception:
            pass
        for folder in (Path(os.environ.get("USERPROFILE", str(home))) / "Desktop",
                       Path(os.environ.get("APPDATA", str(home))) / "Microsoft" / "Windows" / "Start Menu" / "Programs"):
            remove(folder / "Nexarch.lnk")
    elif sys.platform == "darwin":
        remove(home / "Applications" / "Nexarch.app")
        remove(home / "Desktop" / "Nexarch.command")
    else:
        remove(home / ".local" / "share" / "applications" / "nexarch.desktop")
        remove(home / ".local" / "share" / "applications" / "nexarch-uninstall.desktop")
        remove(home / "Desktop" / "nexarch.desktop")
    if not args.keep_data:
        remove(home / ".config" / "nexarch")
        remove(home / ".local" / "share" / "nexarch" / "games.jsonl")
    print("Nexarch removed.")


if __name__ == "__main__":
    main()
