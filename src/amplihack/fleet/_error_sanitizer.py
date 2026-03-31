"""Sanitize external command details before showing them to fleet users."""

from __future__ import annotations

import re

from amplihack.utils.token_sanitizer import sanitize

__all__ = ["sanitize_external_error_detail"]

_PATH_RE = re.compile(r"(?P<path>(?:~|/)[^\s'\":;,]+)")


def sanitize_external_error_detail(detail: str | None, *, max_len: int = 200) -> str:
    """Sanitize user-facing subprocess and exception details."""
    sanitized = sanitize(detail or "")
    sanitized = _PATH_RE.sub("<path>", sanitized)
    sanitized = " ".join(sanitized.split())
    if not sanitized:
        return "details unavailable"
    return sanitized[:max_len]
