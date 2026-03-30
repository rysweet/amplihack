"""Top-level compatibility shim for tests that import ``copilot_stop_handler`` directly."""

from amplihack.hooks.copilot_stop_handler import (
    _log_decision,
    disable_lock_files,
    get_copilot_continuation,
)

__all__ = ["get_copilot_continuation", "disable_lock_files", "_log_decision"]
