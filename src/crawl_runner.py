"""Runs crawls in a background process so the Streamlit UI never freezes.

The UI calls :func:`start_crawl`, which launches ``python -m src.cli crawl``
as a subprocess. The crawler writes progress to a JSON status file that the
UI polls; :func:`stop_crawl` asks it to finish the current page and exit.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from config import settings
from src.models import utc_now_iso

STATUS_FILE = settings.CRAWL_STATUS_FILE
STOP_FILE = STATUS_FILE.with_suffix(".stop")


def write_status(data: dict, path: Path = STATUS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    os.replace(tmp, path)  # atomic, so the UI never reads half a file


def read_status(path: Path = STATUS_FILE) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    try:  # reap if it is our finished child (avoids zombies reporting alive)
        done, _ = os.waitpid(pid, os.WNOHANG)
        return done == 0
    except ChildProcessError:
        return True


def is_running() -> bool:
    status = read_status()
    return status.get("state") == "running" and _pid_alive(status.get("pid"))


def start_crawl(mode: str, companies: list[str] | None = None, max_details: int | None = None,
                headed: bool = False) -> dict:
    if is_running():
        raise RuntimeError("A crawl is already running. Wait for it to finish or stop it first.")
    STOP_FILE.unlink(missing_ok=True)
    cmd = [sys.executable, "-m", "src.cli", "crawl", "--mode", mode, "--status-file", str(STATUS_FILE)]
    if companies:
        cmd += ["--companies", ",".join(companies)]
    if max_details is not None:
        cmd += ["--max-details", str(max_details)]
    if headed:
        cmd.append("--headed")
    write_status({"state": "running", "mode": mode, "started_at": utc_now_iso(), "done": 0,
                  "total": len(companies) if companies else None, "current_company": "starting browser…"})
    log_file = open(settings.LOG_DIR / "crawl_subprocess.log", "a", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=settings.BASE_DIR, stdout=log_file, stderr=subprocess.STDOUT,
                            start_new_session=True)
    status = read_status()
    status["pid"] = proc.pid
    write_status(status)
    return status


def stop_crawl() -> None:
    """Request a graceful stop: the crawler checks for the stop file between pages."""
    STOP_FILE.write_text(utc_now_iso(), encoding="utf-8")
    pid = read_status().get("pid")
    if pid and _pid_alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
