"""Test harness fer outside-in plugin testin'.

Provides subprocess-based test harnesses fer plugin lifecycle, hooks, and LSP detection.
"""

from .subprocess_test_harness import (
    PluginTestHarness,
    HookTestHarness,
    LSPTestHarness,
    SubprocessResult,
)

__all__ = [
    "PluginTestHarness",
    "HookTestHarness",
    "LSPTestHarness",
    "SubprocessResult",
]
