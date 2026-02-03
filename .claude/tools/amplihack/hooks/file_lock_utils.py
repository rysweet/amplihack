#!/usr/bin/env python3
"""
Shared file locking utilities for amplihack hooks.

Philosophy:
- Ruthlessly Simple: Single-purpose module with clear contract
- Fail-Open: Never block users due to locking errors
- Zero-BS: No stubs, every function works or doesn't exist
- Modular: Self-contained brick with standard library only

Public API (the "studs"):
    LOCKING_AVAILABLE: Boolean indicating if fcntl is available
    acquire_file_lock: Context manager for exclusive file locking
"""

import time
from contextlib import contextmanager

# Platform-specific imports (Windows compatibility)
try:
    import fcntl

    LOCKING_AVAILABLE = True
except ImportError:
    # Windows doesn't have fcntl - graceful degradation
    LOCKING_AVAILABLE = False

__all__ = [
    "LOCKING_AVAILABLE",
    "acquire_file_lock",
]

# File locking constants
LOCK_TIMEOUT_SECONDS = 2.0
LOCK_RETRY_INTERVAL = 0.05  # 50ms between retry attempts


@contextmanager
def acquire_file_lock(file_handle, timeout_seconds: float | None = None, log=None):
    """Acquire exclusive file lock with timeout (context manager pattern).

    Uses fcntl.flock() on Linux/macOS for advisory file locking.
    On Windows, gracefully degrades (no locking).

    Args:
        file_handle: Open file object to lock
        timeout_seconds: Lock acquisition timeout (default: LOCK_TIMEOUT_SECONDS)
        log: Optional logging callback

    Yields:
        True if lock acquired, False if timeout/unavailable (fail-open)

    Example:
        with open(path, 'r+') as f:
            with acquire_file_lock(f) as locked:
                if locked:
                    # Critical section with lock protection
                    pass
                else:
                    # Proceed without lock (fail-open)
                    pass
    """
    if timeout_seconds is None:
        timeout_seconds = LOCK_TIMEOUT_SECONDS

    # No-op logging if not provided
    if log is None:

        def log(msg: str, level: str = "INFO") -> None:
            """No-op log function."""

    # Windows degradation: Skip locking
    if not LOCKING_AVAILABLE:
        yield False
        return

    # Try to acquire lock with timeout
    start_time = time.time()
    lock_acquired = False

    try:
        while True:
            try:
                # Non-blocking exclusive lock
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                lock_acquired = True
                log("File lock acquired", "DEBUG")
                break

            except BlockingIOError:
                # Lock unavailable - check timeout
                elapsed = time.time() - start_time
                if timeout_seconds is not None and elapsed >= timeout_seconds:
                    log(
                        f"Lock timeout after {timeout_seconds}s - proceeding without lock",
                        "DEBUG",
                    )
                    break

                # Wait briefly before retry
                time.sleep(LOCK_RETRY_INTERVAL)

        # Yield lock status
        yield lock_acquired

    except (PermissionError, OSError) as e:
        # Fail-open: Log error and proceed without lock
        log(f"Lock error ({type(e).__name__}): {e} - proceeding without lock", "DEBUG")
        yield False

    finally:
        # Release lock if acquired
        if lock_acquired:
            try:
                fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
                log("File lock released", "DEBUG")
            except Exception as e:
                # Non-critical: Lock will be released when file closes
                log(f"Warning: Lock release failed: {e}", "DEBUG")
