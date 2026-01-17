"""Hook strategies for adaptive launcher support.

Philosophy:
- Strategy pattern for launcher-specific behavior
- Each launcher gets its own concrete strategy
- Public API exports all strategies

Public API:
    HookStrategy: Abstract base class
    ClaudeStrategy: Strategy for Claude Code
    CopilotStrategy: Strategy for GitHub Copilot
"""

from .base import HookStrategy
from .claude_strategy import ClaudeStrategy
from .copilot_strategy import CopilotStrategy

__all__ = ["HookStrategy", "ClaudeStrategy", "CopilotStrategy"]
