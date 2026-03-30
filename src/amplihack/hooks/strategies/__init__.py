"""Compatibility hook strategies used by strategy tests."""

from .base import HookStrategy
from .claude_strategy import ClaudeStrategy
from .copilot_strategy import CopilotStrategy

__all__ = ["HookStrategy", "ClaudeStrategy", "CopilotStrategy"]
