#!/usr/bin/env python3
"""Nexarch installer: engine, network, GUI, shortcut and uninstall entry."""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = "Nexarch"
BANNER = r"""
      /\        N E X A R C H
     /  \       chess engine and GUI
    /____\      _____________________
   /|    |\     |_|_|_|_|_|_|_|_|_|_|
  / |    | \    |_|_|_|_|_|_|_|_|_|_|
 /__|____|__\   play, analyse, improve
"""


def colour(text, code):
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return text
    return f"\033[{code}m{text}\033[0m"


def ask(prompt, default):
    suffix = " [Y/n] " if default else " [y/N] "
    try:
        answer = input(prompt + suffix).strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in ("y", "yes")


def default_prefix():
    home = Path.home()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        return Path(base) / APP
    if sys.platform == "darwin":
        return home / "Applications" / APP
    return home / ".local" / "share" / "nexarch"


def find_engine(root, name):
    for candidate in (root / "engine" / name, root / "engine" / f"{name}.exe"):
        if candidate.is_file():
            return candidate
    return None


def cpu_supports_avx2():
    try:
        text = Path("/proc/cpuinfo").read_text()
        return " avx2 " in text or "\tavx2" in text
    except Exception:
        return False


def choose_cpu_engine(root):
    avx2 = find_engine(root, "nexarch-cpu-avx2") or find_engine(root, "nexarch-cpu")
    base = find_engine(root, "nexarch-cpu") or find_engine(root, "nexarch")
    if avx2 and (avx2.name.endswith("avx2") and cpu_supports_avx2()):
        return avx2
    return base or avx2


def copy_tree(src, dst):
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.rglob("*"):
        if item.is_dir() or "__pycache__" in item.parts:
            continue
        target = dst / item.relative_to(src)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, target)


def write_text(path, text, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    try:
        os.chmod(path, mode)
    except Exception:
        pass


def install_engines(root, prefix, net):
    engine_dir = prefix / "engine"
    engine_dir.mkdir(parents=True, exist_ok=True)
    cpu = choose_cpu_engine(root)
    if not cpu:
        raise SystemExit("No engine binary found in the release. Build it with 'make -C engine cpu' first.")
    shutil.copy2(cpu, engine_dir / (cpu.name + (".exe" if os.name == "nt" and not cpu.name.endswith(".exe") else "")))
    entries = []
    cpu_name = (engine_dir / cpu.name).name
    entries.append({
        "name": "Nexarch CPU",
        "command": str(engine_dir / cpu_name),
        "workingDirectory": str(prefix),
        "protocol": "uci",
        "options": [
            {"name": "EvalFile", "value": str(prefix / "nets" / net.name)},
            {"name": "Threads", "value": 1},
            {"name": "Hash", "value": 64},
        ],
    })
    gpu = find_engine(root, "nexarch-gpu")
    if gpu:
        gpu_name = gpu.name + (".exe" if os.name == "nt" and not gpu.name.endswith(".exe") else "")
        shutil.copy2(gpu, engine_dir / gpu_name)
        entries.append({
            "name": "Nexarch GPU (experimental)",
            "command": str(engine_dir / gpu_name),
            "workingDirectory": str(prefix),
            "protocol": "uci",
            "options": [
                {"name": "EvalFile", "value": str(prefix / "nets" / net.name)},
                {"name": "UseGPU", "value": True},
                {"name": "Threads", "value": 1},
                {"name": "Hash", "value": 64},
            ],
        })
    return entries


def install_files(root, prefix, net):
    prefix.mkdir(parents=True, exist_ok=True)
    (prefix / "nets").mkdir(parents=True, exist_ok=True)
    shutil.copy2(net, prefix / "nets" / net.name)
    entries = install_engines(root, prefix, net)
    copy_tree(root / "gui", prefix / "gui")
    (prefix / "install").mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / "install" / "uninstall.py", prefix / "install" / "uninstall.py")
    for name in ("LICENSE", "CREDITS.md", "README.md", "GPU.md", "THIRD_PARTY.md", "ENGINES.md"):
        src = root / name
        if src.exists():
            shutil.copy2(src, prefix / name)
    (prefix / "gui" / "engines.json").write_text(json.dumps(entries, indent=1) + "\n")
    launcher = prefix / "gui" / ("nexarch-gui.bat" if os.name == "nt" else "nexarch-gui")
    if os.name == "nt":
        python = sys.executable
        pythonw = Path(python).with_name("pythonw.exe")
        if pythonw.exists():
            python = str(pythonw)
        write_text(launcher, "@echo off\r\n"
                             f'"{python}" "%~dp0nexarch_gui.py" --host 127.0.0.1 --port 8765 '
                             f'--engines "%~dp0engines.json" --open %*\r\n')
    else:
        write_text(launcher, "#!/bin/sh\n"
                             "HERE=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
                             f'exec "{sys.executable}" "$HERE/nexarch_gui.py" --host 127.0.0.1 --port 8765 '
                             '--engines "$HERE/engines.json" --open "$@"\n', mode=0o755)
    return launcher


def write_settings(prefix, telemetry, endpoint):
    config = Path.home() / ".config" / "nexarch" / "gui.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    data = {"telemetry": bool(telemetry), "endpoint": endpoint.strip(),
            "anonymous_id": uuid.uuid4().hex, "threads": 1, "hash": 64, "skill": 20}
    config.write_text(json.dumps(data, indent=1) + "\n")
    return config


def find_cutechess(prefix):
    base = prefix / "gui" / "cutechess"
    if os.name == "nt":
        for candidate in (base / "cutechess-1.5.1-win64" / "cutechess.exe", base / "cutechess.exe"):
            if candidate.is_file():
                return candidate
        for candidate in base.rglob("cutechess.exe"):
            return candidate
    elif sys.platform == "darwin":
        for candidate in base.glob("*.app"):
            return candidate
    else:
        for candidate in (base / "Cute_Chess-1.5.1-x86_64.AppImage", base / "cutechess"):
            if candidate.is_file():
                return candidate
    return None


def install_cutechess(prefix):
    src = find_cutechess(prefix)
    if not src:
        return None
    config = prefix / "config" / "cutechess"
    config.mkdir(parents=True, exist_ok=True)
    entries = json.loads((prefix / "gui" / "engines.json").read_text())
    (config / "engines.json").write_text(json.dumps(entries, indent=1) + "\n")
    gui = prefix / "gui"
    if os.name == "nt":
        launcher = gui / "nexarch-cutechess.bat"
        rel = os.path.relpath(src, gui)
        write_text(launcher, "@echo off\r\n"
                             "set APPDATA=%~dp0..\\config\r\n"
                             f'start "" "%~dp0{rel}" %*\r\n')
    elif sys.platform == "darwin":
        launcher = gui / "nexarch-cutechess.command"
        write_text(launcher, "#!/bin/sh\n"
                             f'open "{src}"\n', mode=0o755)
    else:
        launcher = gui / "nexarch-cutechess"
        rel = os.path.relpath(src, gui)
        write_text(launcher, "#!/bin/sh\n"
                             "HERE=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n"
                             "export XDG_CONFIG_HOME=\"$HERE/../config\"\n"
                             "export APPIMAGE_EXTRACT_AND_RUN=1\n"
                             f'exec "$HERE/{rel}" "$@"\n', mode=0o755)
    return launcher


def install_desktop_entry(prefix, web_launcher, cc_launcher, shortcut):
    home = Path.home()
    applications = home / ".local" / "share" / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    primary = cc_launcher or web_launcher
    icon = prefix / "gui" / "assets" / "cutechess" / "cutechess_32x32.png"
    if not icon.exists():
        icon = prefix / "gui" / "pieces" / "nlt45.svg"
    entries = [("nexarch.desktop", "Nexarch", "Play chess against Nexarch", primary)]
    if cc_launcher and web_launcher:
        entries.append(("nexarch-arena.desktop", "Nexarch Arena",
                        "Online and analysis companion", web_launcher))
    for name, title, comment, exec_path in entries:
        write_text(applications / name, f"""[Desktop Entry]
Type=Application
Version=1.0
Name={title}
Comment={comment}
Exec="{exec_path}"
Icon="{icon}"
Terminal=false
Categories=Game;BoardGame;
""")
    uninstall = applications / "nexarch-uninstall.desktop"
    write_text(uninstall, f"""[Desktop Entry]
Type=Application
Version=1.0
Name=Uninstall Nexarch
Comment=Remove Nexarch from this computer
Exec=python3 "{prefix / 'install' / 'uninstall.py'}" --prefix "{prefix}"
Icon="{icon}"
Terminal=true
Categories=Game;BoardGame;
""")
    if shortcut:
        desk = home / "Desktop"
        if desk.is_dir():
            for name, *_ in entries:
                target = desk / name
                shutil.copy2(applications / name, target)
                try:
                    os.chmod(target, 0o755)
                except Exception:
                    pass
    return primary


def install_windows_shortcuts(prefix, web_launcher, cc_launcher, shortcut):
    import winreg
    if shortcut:
        desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
        start = Path(os.environ.get("APPDATA", str(Path.home()))) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        icon = prefix / "gui" / "assets" / "cutechess" / "cutechess_win.ico"
        targets = [("Nexarch.lnk", cc_launcher or web_launcher)]
        if cc_launcher and web_launcher:
            targets.append(("Nexarch Arena.lnk", web_launcher))
        for folder in (desktop, start):
            if not folder.is_dir():
                continue
            for name, target in targets:
                link = folder / name
                ps = ("$w=New-Object -ComObject WScript.Shell;"
                      f"$s=$w.CreateShortcut('{link}');"
                      f"$s.TargetPath='{target}';"
                      f"$s.WorkingDirectory='{prefix}';"
                      f"$s.IconLocation='{icon}';"
                      "$s.Save()")
                subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Nexarch"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
        winreg.SetValueEx(k, "DisplayName", 0, winreg.REG_SZ, "Nexarch")
        winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ, "0.5")
        winreg.SetValueEx(k, "Publisher", 0, winreg.REG_SZ, "Mark Ivanovskyy")
        winreg.SetValueEx(k, "InstallLocation", 0, winreg.REG_SZ, str(prefix))
        winreg.SetValueEx(k, "UninstallString", 0, winreg.REG_SZ,
                          f'python "{prefix / "install" / "uninstall.py"}" --prefix "{prefix}"')
        winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)


def install_macos_app(prefix, launcher, shortcut):
    write_text(prefix / "Uninstall Nexarch.command",
               "#!/bin/sh\n"
               f'exec "{sys.executable}" "{prefix / "install" / "uninstall.py"}" --prefix "{prefix}"\n',
               mode=0o755)
    if not shortcut:
        return
    app = Path.home() / "Applications" / "Nexarch.app"
    (app / "Contents" / "MacOS").mkdir(parents=True, exist_ok=True)
    (app / "Contents" / "Info.plist").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Nexarch</string>
<key>CFBundleDisplayName</key><string>Nexarch</string>
<key>CFBundleExecutable</key><string>Nexarch</string>
<key>CFBundleIdentifier</key><string>org.nexarch.chess</string>
<key>CFBundleVersion</key><string>0.5</string>
<key>CFBundleShortVersionString</key><string>0.5</string>
</dict></plist>
""")
    write_text(app / "Contents" / "MacOS" / "Nexarch", f"#!/bin/sh\nexec '{launcher}' \"$@\"\n", mode=0o755)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prefix", default=None)
    ap.add_argument("--net", default=None)
    ap.add_argument("--shortcut", choices=["yes", "no"], default=None)
    ap.add_argument("--telemetry", choices=["yes", "no"], default=None)
    ap.add_argument("--endpoint", default="")
    ap.add_argument("--no-prompt", action="store_true")
    args = ap.parse_args()

    print(colour(BANNER, "36"))
    print(colour("Nexarch installer", "1;36"))
    print("This installs the engine, a network, and the Nexarch Chess GUI.\n")

    prefix = Path(args.prefix).expanduser() if args.prefix else default_prefix()
    if not args.no_prompt:
        try:
            value = input(f"Install folder [{prefix}]: ").strip()
            if value:
                prefix = Path(value).expanduser()
        except EOFError:
            pass
    net = Path(args.net).expanduser() if args.net else (ROOT / "nets" / "nexarch-g5.nnue")
    if not net.is_absolute():
        net = ROOT / net
    if not net.exists():
        net = ROOT / "nets" / "nexarch-g4.nnue"
    if not net.exists():
        raise SystemExit("No .nnue network found in nets/.")

    shortcut = args.shortcut == "yes" if args.shortcut else False
    if args.shortcut is None and not args.no_prompt:
        shortcut = ask("Create a desktop shortcut?", True)

    telemetry = args.telemetry == "yes" if args.telemetry else False
    endpoint = args.endpoint
    if args.telemetry is None and not args.no_prompt:
        print("\n" + colour("Anonymous game collection (optional)", "1"))
        print("When enabled, finished games against Nexarch are sent to a server with no")
        print("account name, email address or hardware ID. It is off by default.")
        telemetry = ask("Enable anonymous game collection?", False)
        if telemetry:
            try:
                endpoint = input("Upload endpoint (blank keeps games on this computer): ").strip()
            except EOFError:
                endpoint = ""

    try:
        subprocess.run([sys.executable, "-c", "import chess"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        print(colour("The GUI needs Python 3 and the 'chess' package.", "33"))
        print(f"  {sys.executable} -m pip install --user chess")
        if not args.no_prompt and ask("Install python-chess now?", True):
            subprocess.run([sys.executable, "-m", "pip", "install", "--user", "chess"], check=False)

    print(f"\nInstalling to {colour(str(prefix), '1')}")
    print("  [1/3] copying the engine, network and GUIs ...")
    launcher = install_files(ROOT, prefix, net)
    cc_launcher = install_cutechess(prefix)
    print("  [2/3] creating the shortcut and uninstall entry ...")
    if os.name == "nt":
        install_windows_shortcuts(prefix, launcher, cc_launcher, shortcut)
    elif sys.platform == "darwin":
        install_macos_app(prefix, launcher, shortcut)
    else:
        install_desktop_entry(prefix, launcher, cc_launcher, shortcut)
    print("  [3/3] writing settings ...")
    config = write_settings(prefix, telemetry, endpoint)

    print(colour("\nDone.", "1;32"))
    print(f"Engine:  {prefix / 'engine'}")
    print(f"Cute Chess: {cc_launcher or 'not bundled'}")
    print(f"Arena:   {launcher}")
    print(f"Settings:{config}")
    if telemetry:
        print(f"Anonymous games: {'sent to ' + endpoint if endpoint else 'saved on this computer (no endpoint set)'}")
    else:
        print("Anonymous games: off")
    print("\nStart Nexarch from the shortcut, or run:")
    print(f"  {cc_launcher or launcher}")
    print("Cute Chess is preconfigured with Nexarch. Use its engine settings to add Stockfish")
    print("or any other UCI engine. The Nexarch Arena companion is a separate shortcut.")


if __name__ == "__main__":
    main()
