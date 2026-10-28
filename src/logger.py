"""Application-wide logging (console + rotating file in logs/app.log)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from config import settings

_CONFIGURED = False


def get_logger(name: str = "jobdiscovery") -> logging.Logger:
    global _CONFIGURED
    if not _CONFIGURED:
        settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
        fmt = logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
        root = logging.getLogger("jobdiscovery")
        root.setLevel(logging.INFO)
        file_handler = RotatingFileHandler(
            settings.LOG_DIR / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        root.addHandler(file_handler)
        root.addHandler(console)
        root.propagate = False
        _CONFIGURED = True
    if name == "jobdiscovery" or name.startswith("jobdiscovery."):
        return logging.getLogger(name)
    return logging.getLogger(f"jobdiscovery.{name}")
