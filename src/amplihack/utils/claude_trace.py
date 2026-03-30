"""Collection-safe helpers for choosing and validating the claude-trace wrapper."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

_FALSE_VALUES = {"0", "false", "no", "off"}
_TRUE_VALUES = {"1", "true", "yes", "on"}


def should_use_trace() -> bool:
    value = os.getenv("AMPLIHACK_USE_TRACE")
    if value is None:
        return True
    normalized = value.strip().lower()
    if normalized in _FALSE_VALUES:
        return False
    if normalized in _TRUE_VALUES:
        return True
    return True


def get_claude_command() -> str:
    return "claude-trace" if should_use_trace() else "claude"


def _test_claude_trace_execution(binary_path: str) -> bool:
    path = Path(binary_path)
    if path.exists() and path.is_symlink():
        try:
            resolved = path.resolve()
            if "/opt/homebrew/" in str(resolved) and "claude-trace" in resolved.name:
                return True
        except OSError:
            return False
    try:
        result = subprocess.run(
            [binary_path, "--help"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        return False
    if result.returncode != 0:
        return False
    output = f"{result.stdout}\n{result.stderr}".strip().lower()
    if not output:
        return False
    return "claude" in output and ("trace" in output or "usage" in output)


def _is_valid_claude_trace_binary(binary_path: str) -> bool:
    path = Path(binary_path)
    if not path.exists() or not path.is_file():
        return False
    if not os.access(path, os.X_OK):
        return False
    return _test_claude_trace_execution(binary_path)


__all__ = [
    "get_claude_command",
    "should_use_trace",
    "_is_valid_claude_trace_binary",
    "_test_claude_trace_execution",
]
