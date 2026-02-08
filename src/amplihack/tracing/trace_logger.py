"""
TraceLogger - Optional JSONL trace logging with token sanitization.

Philosophy:
- Opt-in by default (must explicitly enable)
- Zero overhead when disabled (<0.1ms)
- Minimal overhead when enabled (<10ms)
- Security-first: Automatic token sanitization
- Self-contained and regeneratable

Public API:
    TraceLogger: Main logging class
    from_env(): Factory method to create from environment variables
    DEFAULT_TRACE_FILE: Default trace file path constant

Created for Issue #2071: Native Binary Migration with Optional Trace Logging
"""

import json
import os
from datetime import datetime, timezone  # Python 3.10 compatibility
from pathlib import Path
from typing import Any

from ..proxy.token_sanitizer import TokenSanitizer

# Default trace file location - used by trace_logger and litellm_callbacks
DEFAULT_TRACE_FILE = Path.home() / ".amplihack" / "trace.jsonl"


class TraceLogger:
    """
    Optional JSONL trace logger with automatic token sanitization.

    Features:
    - JSONL format (one JSON object per line)
    - Automatic timestamp injection
    - Token sanitization via TokenSanitizer
    - Context manager support (sync and async)
    - Zero overhead when disabled

    Usage:
        >>> logger = TraceLogger(enabled=True, log_file=Path("trace.jsonl"))
        >>> with logger:
        ...     logger.log({"event": "api_call", "model": "claude-3"})

    Performance Requirements:
    - Disabled: <0.1ms overhead
    - Enabled: <10ms overhead per log entry
    """

    def __init__(self, enabled: bool = False, log_file: Path | None = None):
        """
        Initialize TraceLogger.

        Args:
            enabled: Whether logging is enabled (default: False, opt-in)
            log_file: Path to JSONL log file (required if enabled=True)
        """
        self.enabled = enabled
        self.log_file = log_file
        self._file_handle = None

    @classmethod
    def from_env(cls) -> "TraceLogger":
        """
        Create TraceLogger from environment variables.

        Environment Variables:
            AMPLIHACK_TRACE_LOGGING: "true" to enable logging (default: disabled)
            AMPLIHACK_TRACE_FILE: Path to log file (default: ~/.amplihack/trace.jsonl)

        Returns:
            Configured TraceLogger instance
        """
        enabled_str = os.getenv("AMPLIHACK_TRACE_LOGGING", "").lower()
        enabled = enabled_str in ("true", "1", "yes")

        log_file = None
        if enabled:
            log_file_str = os.getenv("AMPLIHACK_TRACE_FILE")
            if log_file_str:
                log_file = Path(log_file_str)
            else:
                log_file = DEFAULT_TRACE_FILE

        return cls(enabled=enabled, log_file=log_file)

    def __enter__(self):
        """Enter context manager - open log file if enabled."""
        if self.enabled and self.log_file:
            try:
                # Create parent directories if needed
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                # Open in append mode
                self._file_handle = open(self.log_file, "a", encoding="utf-8")
            except (OSError, PermissionError) as e:
                # Clean up and disable logging rather than failing
                self._file_handle = None
                self.enabled = False
                # Log to stderr since we can't log to file
                import sys

                print(
                    f"Warning: Could not open trace log file {self.log_file}: {e}", file=sys.stderr
                )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - close log file."""
        if self._file_handle:
            try:
                self._file_handle.flush()
                self._file_handle.close()
            except OSError:
                # Ignore errors on close - best effort cleanup
                pass
            finally:
                self._file_handle = None
        return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)

    def log(self, data: dict[str, Any] | None) -> None:
        """
        Log a trace event.

        Args:
            data: Dictionary to log as JSONL entry. Will be sanitized and timestamped.

        Behavior:
            - When disabled: Immediate no-op return (<0.1ms)
            - When enabled: Sanitize, timestamp, and write to JSONL file
            - Requires context manager to be active (raises error otherwise)

        Performance:
            - Disabled: <0.1ms (100μs)
            - Enabled: <10ms including sanitization and I/O
        """
        # Fast path: disabled logger is a no-op
        if not self.enabled:
            return

        # Validate context manager is active
        if self._file_handle is None:
            # Instead of raising, just return silently - logging is optional
            return

        # Handle None or empty data
        if data is None:
            data = {}

        # Create a copy to avoid mutating original
        entry = dict(data)

        # Add timestamp if not present
        if "timestamp" not in entry:
            entry["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Sanitize sensitive data
        sanitized_entry = TokenSanitizer.sanitize_dict(entry)

        # Serialize to JSON and write
        try:
            json_line = json.dumps(sanitized_entry, ensure_ascii=False, default=_json_default)
            self._file_handle.write(json_line + "\n")
            self._file_handle.flush()  # Ensure immediate write
        except (TypeError, ValueError) as e:
            # Handle non-serializable data gracefully
            try:
                error_entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "event": "trace_logger_error",
                    "error": str(e),
                    "original_event": str(entry.get("event", "unknown")),
                }
                json_line = json.dumps(error_entry, ensure_ascii=False)
                self._file_handle.write(json_line + "\n")
                self._file_handle.flush()
            except OSError:
                # If we can't even log the error, silently give up
                pass
        except OSError:
            # Handle I/O errors (disk full, permissions, etc.)
            # Trace logging is optional, so silently fail rather than break the caller
            pass


def _json_default(obj: Any) -> str:
    """
    JSON serialization fallback for non-serializable objects.

    Args:
        obj: Object that couldn't be serialized

    Returns:
        String representation of the object
    """
    # Handle Path objects
    if isinstance(obj, Path):
        return str(obj)

    # Handle datetime objects (shouldn't happen, but be defensive)
    if isinstance(obj, datetime):
        return obj.isoformat()

    # Default: convert to string
    return str(obj)


__all__ = ["TraceLogger", "DEFAULT_TRACE_FILE"]
