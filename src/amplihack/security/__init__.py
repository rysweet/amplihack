"""
XPIA Defense Security Module

Cross-Prompt Injection Attack defense system for amplihack.
"""

from .xpia_defender import WebFetchXPIADefender, XPIADefender
from .xpia_hooks import ClaudeCodeXPIAHook, XPIAHookAdapter, register_xpia_hooks, xpia_hook
from .xpia_patterns import (
    AttackPattern,
    PatternCategory,
    PromptPatterns,
    URLPatterns,
    XPIAPatterns,
)

__all__ = [
    # Core defender classes
    "XPIADefender",
    "WebFetchXPIADefender",
    # Hook integration
    "ClaudeCodeXPIAHook",
    "XPIAHookAdapter",
    "register_xpia_hooks",
    "xpia_hook",
    # Pattern definitions
    "AttackPattern",
    "PatternCategory",
    "XPIAPatterns",
    "URLPatterns",
    "PromptPatterns",
]

# Version info
__version__ = "1.0.0"
