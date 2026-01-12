#!/usr/bin/env python3
"""
Shutdown context detection for graceful cleanup operations.

This module provides utilities to detect when application shutdown is in
progress, allowing hooks and other components to skip blocking operations
during cleanup.

Problem:
    During atexit cleanup, hooks that read from stdin can block indefinitely
    because stdin is closed or detached. This causes hangs requiring Ctrl-C
    to terminate.

Solution:
    Multi-layered shutdown detection that checks:
    1. AMPLIHACK_SHUTDOWN_IN_PROGRESS environment variable
    2. Call stack for atexit handler presence
    3. stdin state (closed or detached)

    When shutdown is detected, hooks return immediately with safe defaults
    instead of blocking on stdin reads.

Philosophy:
- Ruthlessly Simple: Single-purpose module with clear contract
- Standard Library Only: No external dependencies
- Thread-Safe: Uses environment variables
- Fail-Open: Returns safe defaults when in doubt
- Zero-BS: Every function works, no stubs

Public API (the "studs"):
    is_shutdown_in_progress: Detect if shutdown is in progress
    mark_shutdown: Set shutdown flag (for signal handlers and atexit)
    clear_shutdown: Clear shutdown flag (for testing only)

Example:
    >>> # Signal handler marks shutdown
    >>> def signal_handler(sig, frame):
    ...     mark_shutdown()
    ...     sys.exit(0)

    >>> # Hook checks before stdin read
    >>> def read_input():
    ...     if is_shutdown_in_progress():
    ...         return {}
    ...     return json.loads(sys.stdin.read())
"""

import inspect
import io
import os
import sys

__all__ = ["is_shutdown_in_progress", "mark_shutdown", "clear_shutdown"]


def is_shutdown_in_progress() -> bool:
    """Detect if application shutdown is in progress.

    Uses multi-layered detection to determine if shutdown is happening:
    1. Check AMPLIHACK_SHUTDOWN_IN_PROGRESS environment variable
    2. Inspect call stack for atexit handler presence
    3. Check if stdin is closed or detached

    Returns:
        True if shutdown is detected, False otherwise

    Note:
        This is a best-effort detection that errs on the side of caution.
        False positives (detecting shutdown when not happening) are acceptable
        since they only cause hooks to skip processing, which is safe during
        cleanup.

    Example:
        >>> mark_shutdown()
        >>> is_shutdown_in_progress()
        True
        >>> clear_shutdown()
        >>> is_shutdown_in_progress()
        False
    """
    if os.environ.get("AMPLIHACK_SHUTDOWN_IN_PROGRESS") == "1":
        return True

    if _is_in_atexit_context():
        return True

    if _is_stdin_closed():
        return True

    return False


def mark_shutdown() -> None:
    """Mark that shutdown is in progress.

    Sets AMPLIHACK_SHUTDOWN_IN_PROGRESS environment variable to coordinate
    graceful shutdown across all hooks and components.

    This should be called:
    - In signal handlers (SIGINT, SIGTERM) before sys.exit()
    - In atexit handlers before cleanup operations
    - Before any operation that may trigger hook execution during shutdown

    Thread-safe: Uses environment variables which are process-global.

    Example:
        >>> def signal_handler(sig, frame):
        ...     mark_shutdown()  # Prevent hooks from blocking
        ...     sys.exit(0)
    """
    os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"] = "1"


def clear_shutdown() -> None:
    """Clear shutdown flag (for testing only).

    Removes AMPLIHACK_SHUTDOWN_IN_PROGRESS environment variable.
    This should ONLY be used in tests to reset state between test cases.

    Warning:
        Never call this in production code. Once shutdown begins, it should
        not be reversed.

    Example:
        >>> # In test cleanup
        >>> def teardown():
        ...     clear_shutdown()  # Reset state for next test
    """
    if "AMPLIHACK_SHUTDOWN_IN_PROGRESS" in os.environ:
        del os.environ["AMPLIHACK_SHUTDOWN_IN_PROGRESS"]


def _is_in_atexit_context() -> bool:
    """Check if we're currently executing in an atexit handler.

    Inspects the call stack to detect if we're running inside an atexit
    cleanup handler. This helps detect shutdown even when the environment
    variable isn't set yet.

    Returns:
        True if atexit handler is in call stack, False otherwise

    Note:
        This is a heuristic check that may have false negatives, but it
        provides an additional layer of shutdown detection without requiring
        explicit coordination.
    """
    try:
        # Get current call stack
        stack = inspect.stack()

        # Look for atexit module in call stack
        for frame_info in stack:
            # Check module name
            module = inspect.getmodule(frame_info.frame)
            if module and module.__name__ == "atexit":
                return True

            # Check function name for common atexit patterns
            func_name = frame_info.function
            if func_name in ("_run_exitfuncs", "_cleanup_on_exit"):
                return True

        return False
    except Exception:
        # Fail-open: If stack inspection fails, assume not in atexit
        return False


def _is_stdin_closed() -> bool:
    """Check if stdin is closed or detached.

    During atexit cleanup, stdin may be closed or detached by the Python
    interpreter. Attempting to read from closed stdin causes blocking or
    errors.

    Returns:
        True if stdin is closed or detached, False otherwise

    Note:
        This check catches cases where shutdown is happening but the
        environment variable wasn't set (e.g., in tests or unexpected
        shutdown paths).

        We prioritize the `closed` attribute over fileno() checks because:
        - closed=True is a definitive signal that stdin is unusable
        - fileno() may not be supported on mocks/StringIO (not a shutdown signal)
    """
    try:
        # Check if stdin exists
        if not hasattr(sys, "stdin") or sys.stdin is None:
            return True

        # Check if stdin is explicitly closed (most reliable signal)
        if hasattr(sys.stdin, "closed") and sys.stdin.closed:
            return True

        # Try to get file descriptor (will raise if detached)
        # Only consider this a shutdown signal if stdin also lacks basic attributes
        try:
            sys.stdin.fileno()
            # stdin has valid fileno, so it's operational
            return False
        except io.UnsupportedOperation:
            # This is a StringIO or similar mock - not a shutdown signal
            # (Real stdin always supports fileno())
            return False
        except (AttributeError, OSError, ValueError):
            # fileno() failed - but this might just be a mock/StringIO
            # Only treat as closed if stdin also lacks the closed attribute
            # (real stdin always has this attribute)
            if not hasattr(sys.stdin, "closed"):
                # This is likely a mock that doesn't support fileno()
                # Don't treat as shutdown signal
                return False
            # stdin has 'closed' attribute but fileno() fails
            # This suggests stdin is detached during shutdown
            return True

        return False
    except Exception:
        # Fail-open: If we can't determine stdin state, assume it's closed
        # This prevents blocking on potentially broken stdin
        return True
