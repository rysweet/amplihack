"""Compatibility shim for the Claude tools hook package."""

from amplihack.hooks._copilot_stop_handler_impl import (
    _log_decision,
    disable_lock_files,
    get_copilot_continuation,
)

__all__ = ["get_copilot_continuation", "disable_lock_files", "_log_decision"]
