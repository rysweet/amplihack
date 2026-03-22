"""Test harness for outside-in plugin testin'.

Provides subprocess-based test harnesses for plugin lifecycle, hooks, and LSP detection.
"""

from .subprocess_test_harness import (
    HookTestHarness,
    LSPTestHarness,
    PluginTestHarness,
    SubprocessResult,
)

__all__ = [
    "PluginTestHarness",
    "HookTestHarness",
    "LSPTestHarness",
    "SubprocessResult",
]
