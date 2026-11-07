"""Local, background-capable Central Bank Dashboard server.

Standard-library only. Bind to 127.0.0.1 (never the public network).
Refresh the GitHub checkout every 15 minutes via git pull --ff-only, retaining
local files if the network is unavailable or Git reports a conflict.
"""
from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = 8766
SYNC_SECONDS = 15 * 60
LOG = ROOT / "dashboard-sync.log"
STATUS_LOCK = threading.Lock()
STATUS = {"last_check_utc": None, "last_success_utc": None, "last_error": None}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sync_once() -> None:
    # Do not assume that the GitHub repository is public. The local Git
    # credential helper installed during clone handles private authentication.
    kwargs = {"cwd": str(ROOT), "capture_output": True, "text": True, "timeout": 55}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    error = None
    try:
        result = subprocess.run(["git", "pull", "--ff-only", "--no-rebase"], **kwargs)
        if result.returncode:
            error = (result.stderr or result.stdout or "Git returned a nonzero exit code").strip()[-500:]
    except (OSError, subprocess.TimeoutExpired) as exc:
        error = str(exc)[-500:]

    with STATUS_LOCK:
        STATUS["last_check_utc"] = utc_now()
        if error is None:
            STATUS["last_success_utc"] = STATUS["last_check_utc"]
            STATUS["last_error"] = None
        else:
            STATUS["last_error"] = error
    if error:
        # Only write a log on failure, so normal syncing remains quiet.
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{utc_now()} | {error}\n")


def updater() -> None:
    while True:
        sync_once()
        time.sleep(SYNC_SECONDS)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/api/local-sync":
            with STATUS_LOCK:
                data = json.dumps(dict(STATUS)).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()

    def log_message(self, fmt, *args):
        # No terminal is visible when launched through the VBS shortcut.
        pass


if __name__ == "__main__":
    threading.Thread(target=updater, daemon=True, name="github-sync").start()
    try:
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever(poll_interval=0.5)
    except OSError as exc:
        with LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{utc_now()} | Cannot bind {HOST}:{PORT}: {exc}\n")
        raise
