"""Terminal enhancements for Amplihack.

This module provides cross-platform terminal enhancements including:
- Terminal title updates
- Bell notifications
- Rich status indicators (progress bars, spinners)
- Color-coded output

Configuration via environment variables:
- AMPLIHACK_TERMINAL_TITLE: Enable/disable title updates (default: true)
- AMPLIHACK_TERMINAL_BELL: Enable/disable bell notifications (default: true)
- AMPLIHACK_TERMINAL_RICH: Enable/disable rich formatting (default: true)
"""

from .enhancements import (
    ring_bell,
    update_title,
    is_bell_enabled,
    is_title_enabled,
    is_rich_enabled,
)
from .rich_output import (
    progress_spinner,
    create_progress_bar,
    format_success,
    format_error,
    format_warning,
    format_info,
)

__all__ = [
    # Title and bell
    "update_title",
    "ring_bell",
    "is_bell_enabled",
    "is_title_enabled",
    "is_rich_enabled",
    # Rich formatting
    "progress_spinner",
    "create_progress_bar",
    "format_success",
    "format_error",
    "format_warning",
    "format_info",
]
