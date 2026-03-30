"""Helpers for owner-only log and state files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TextIO

PRIVATE_DIR_MODE = 0o700
PRIVATE_FILE_MODE = 0o600


def ensure_private_directory(path: Path) -> None:
    """Create a directory and keep it owner-accessible only on Unix."""
    path.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(path, PRIVATE_DIR_MODE)


def open_private_append(path: Path, *, encoding: str = "utf-8") -> TextIO:
    """Open a file in append mode with owner-only permissions on Unix."""
    ensure_private_directory(path.parent)
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, PRIVATE_FILE_MODE)
    try:
        if os.name != "nt" and hasattr(os, "fchmod"):
            os.fchmod(fd, PRIVATE_FILE_MODE)
        return os.fdopen(fd, "a", encoding=encoding)
    except Exception:
        os.close(fd)
        raise
