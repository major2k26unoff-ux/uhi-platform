"""One command for the whole demo.      python run_all.py      (from the repo root)

Starts three programs and opens the website:
    api     track3   uvicorn main:app --port 8000
    worker  track1   python worker.py
    website track4   python -m http.server 5500

Each track uses its own venv if it has one. Logs go to logs/, so this one window stays clean.
Press Ctrl+C once to stop everything.
"""
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
SITE = "http://localhost:5500"


def venv_python(track):
    """The track's own Python if it has a venv, else the Python running this script."""
    for rel in ("venv/Scripts/python.exe", "venv/bin/python"):
        p = ROOT / track / rel
        if p.exists():
            return str(p)
    return sys.executable


SERVICES = [
    # name, folder, command, port to wait for (None = nothing to wait for)
    ("api", "track3", [venv_python("track3"), "-m", "uvicorn", "main:app", "--port", "8000"], 8000),
    ("worker", "track1", [venv_python("track1"), "-u", "worker.py"], None),
    ("website", "track4", [sys.executable, "-m", "http.server", "5500"], 5500),
]


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    LOGS.mkdir(exist_ok=True)

    for name, folder, _cmd, port in SERVICES:
        if not (ROOT / folder).is_dir():
            sys.exit(f"Folder '{folder}' not found. Run this from the repo root.")
        if port and port_open(port):
            sys.exit(f"Port {port} is already in use. Close the old {name} terminal first, then run again.")

    procs = []
    try:
        for name, folder, cmd, port in SERVICES:
            log = open(LOGS / f"{name}.log", "w", encoding="utf-8")
            p = subprocess.Popen(cmd, cwd=ROOT / folder, stdout=log, stderr=subprocess.STDOUT)
            procs.append((name, p, port))
            print(f"  starting {name:8s} ...", end="", flush=True)
            deadline = time.time() + 30
            while True:
                if p.poll() is not None:
                    print(" FAILED")
                    sys.exit(f"{name} stopped at once. Read logs\\{name}.log for the reason.")
                if port is None or port_open(port):
                    break
                if time.time() > deadline:
                    print(" FAILED")
                    sys.exit(f"{name} did not start in 30 seconds. Read logs\\{name}.log")
                time.sleep(0.3)
            print(" ready")

        print(f"\nAll running. Website: {SITE}\nPress Ctrl+C here to stop everything.\n")
        webbrowser.open(SITE)

        while True:
            for name, p, _port in procs:
                if p.poll() is not None:
                    print(f"{name} stopped (code {p.returncode}). Read logs\\{name}.log")
                    return
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping ...")
    finally:
        for _name, p, _port in procs:
            if p.poll() is None:
                p.terminate()
        for _name, p, _port in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()