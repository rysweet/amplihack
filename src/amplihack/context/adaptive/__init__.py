"""Adaptive context system for detecting and handling different launchers.

This module provides launcher detection and context injection strategies
for both Claude Code (pull model) and Copilot CLI (push model).

Philosophy:
- Single responsibility: Detect launcher, inject context appropriately
- Strategy pattern for launcher-specific behavior
- Simple file-based detection (launcher_context.json)
- Self-contained and regeneratable

Public API:
    LauncherDetector: Main detector class
    HookStrategy: Base strategy class
    ClaudeStrategy: Direct injection for Claude Code
    CopilotStrategy: AGENTS.md workaround for Copilot CLI
"""

from .detector import LauncherDetector
from .strategies import ClaudeStrategy, CopilotStrategy, HookStrategy

__all__ = ["LauncherDetector", "HookStrategy", "ClaudeStrategy", "CopilotStrategy"]
