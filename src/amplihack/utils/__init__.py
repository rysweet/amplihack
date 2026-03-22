"""Utility functions for amplihack."""

import contextlib
import logging
import os
from collections.abc import Generator

from .defensive import (
    DefensiveError,
    FileOperationError,
    JSONExtractionError,
    RetryExhaustedError,
    isolate_prompt,
    parse_llm_json,
    read_file_with_retry,
    retry_with_feedback,
    validate_json_schema,
    write_file_with_retry,
)
from .hello_world import hello_world
from .paths import FrameworkPathResolver
from .process import ProcessManager
from .string_utils import slugify
from .uvx_staging import stage_uvx_framework

_logger = logging.getLogger(__name__)


def get_agent_binary() -> str:
    """Return the active agent binary name from AMPLIHACK_AGENT_BINARY.

    This env var is set by the amplihack CLI dispatcher (cli.py) when the user
    runs ``amplihack claude``, ``amplihack copilot``, etc.  Every subprocess
    that needs to launch a coding agent should call this function instead of
    hard-coding ``"claude"``.

    Returns:
        The agent binary name (e.g. ``"claude"``, ``"copilot"``, ``"codex"``).
        Falls back to ``"claude"`` with a warning if the env var is unset.
    """
    binary = os.environ.get("AMPLIHACK_AGENT_BINARY")
    if not binary:
        _logger.warning(
            "AMPLIHACK_AGENT_BINARY not set — defaulting to 'claude'. "
            "This usually means a subprocess was launched outside the "
            "amplihack CLI dispatcher."
        )
        binary = "claude"
    return binary


@contextlib.contextmanager
def _agent_binary_context(agent_binary: str | None) -> Generator[None, None, None]:
    """Temporarily set AMPLIHACK_AGENT_BINARY and restore the original value on exit.

    Args:
        agent_binary: Binary name to set, or ``None`` to leave the env var unchanged.
    """
    if agent_binary is None:
        yield
        return

    original = os.environ.get("AMPLIHACK_AGENT_BINARY")
    os.environ["AMPLIHACK_AGENT_BINARY"] = agent_binary
    try:
        yield
    finally:
        if original is None:
            os.environ.pop("AMPLIHACK_AGENT_BINARY", None)
        else:
            os.environ["AMPLIHACK_AGENT_BINARY"] = original


def is_uvx_deployment() -> bool:
    """Simple UVX detection based on sys.executable location."""
    import sys

    # Check if running from UV cache (primary indicator)
    return ".cache/uv/" in sys.executable or "\\cache\\uv\\" in sys.executable


__all__ = [
    # Agent binary
    "get_agent_binary",
    "_agent_binary_context",
    # Path utilities
    "FrameworkPathResolver",
    # Process utilities
    "ProcessManager",
    # Hello world
    "hello_world",
    # String utilities
    "slugify",
    # UVX utilities
    "is_uvx_deployment",
    "stage_uvx_framework",
    # Defensive utilities
    "DefensiveError",
    "JSONExtractionError",
    "RetryExhaustedError",
    "FileOperationError",
    "parse_llm_json",
    "retry_with_feedback",
    "isolate_prompt",
    "read_file_with_retry",
    "write_file_with_retry",
    "validate_json_schema",
]
