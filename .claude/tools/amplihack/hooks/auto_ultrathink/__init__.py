"""Auto-ultrathink feature for automatically invoking UltraThink workflows.

This module provides automatic detection and invocation of UltraThink for
appropriate user requests, with configurable user preferences.
"""

from .hook_integration import auto_ultrathink_hook

__all__ = ["auto_ultrathink_hook"]
