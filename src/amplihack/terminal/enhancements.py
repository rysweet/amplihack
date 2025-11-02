"""Core terminal enhancements: title updates and bell notifications.

This module provides cross-platform terminal manipulation including:
- Terminal title updates (ANSI escape codes + Windows API)
- Bell notifications with user configuration
- Environment-based feature toggles
"""

import os
import platform
import sys
from typing import Optional


def _str_to_bool(value: Optional[str], default: bool = True) -> bool:
    """Convert environment variable string to boolean.

    Args:
        value: Environment variable value (None, "true", "false", "1", "0")
        default: Default value if not set

    Returns:
        Boolean value
    """
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes", "on")


def is_title_enabled() -> bool:
    """Check if terminal title updates are enabled.

    Returns:
        True if title updates are enabled via AMPLIHACK_TERMINAL_TITLE
    """
    return _str_to_bool(os.environ.get("AMPLIHACK_TERMINAL_TITLE"), default=True)


def is_bell_enabled() -> bool:
    """Check if terminal bell notifications are enabled.

    Returns:
        True if bell notifications are enabled via AMPLIHACK_TERMINAL_BELL
    """
    return _str_to_bool(os.environ.get("AMPLIHACK_TERMINAL_BELL"), default=True)


def is_rich_enabled() -> bool:
    """Check if rich formatting is enabled.

    Returns:
        True if rich formatting is enabled via AMPLIHACK_TERMINAL_RICH
    """
    return _str_to_bool(os.environ.get("AMPLIHACK_TERMINAL_RICH"), default=True)


def update_title(title: str) -> None:
    """Update terminal window title with cross-platform support.

    Uses ANSI escape codes for Linux/macOS and Windows Console API
    for Windows. Respects AMPLIHACK_TERMINAL_TITLE configuration.

    Args:
        title: New terminal title to display

    Example:
        >>> update_title("Amplihack - Session 20251102_143022")
    """
    if not is_title_enabled():
        return

    if not sys.stdout.isatty():
        # Not a terminal, skip
        return

    system = platform.system()

    try:
        if system in ("Darwin", "Linux"):
            # ANSI escape code: ESC]0;title BEL
            # OSC 0 = Set icon name and window title
            print(f"\033]0;{title}\007", end="", flush=True)
        elif system == "Windows":
            # Windows Console API
            try:
                import ctypes
                ctypes.windll.kernel32.SetConsoleTitleW(title)
            except (ImportError, AttributeError, OSError):
                # Fallback to ANSI codes (works on Windows 10+)
                print(f"\033]0;{title}\007", end="", flush=True)
    except Exception:
        # Silently fail - terminal manipulation is not critical
        pass


def ring_bell() -> None:
    """Ring terminal bell to notify user of task completion.

    Sends ASCII BEL character (0x07) to terminal. Respects
    AMPLIHACK_TERMINAL_BELL configuration.

    Example:
        >>> ring_bell()  # Beep on completion
    """
    if not is_bell_enabled():
        return

    if not sys.stdout.isatty():
        # Not a terminal, skip
        return

    try:
        print("\007", end="", flush=True)
    except Exception:
        # Silently fail - bell is not critical
        pass
