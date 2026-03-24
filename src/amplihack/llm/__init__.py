"""LLM client abstraction for amplihack.

Routes LLM queries to the appropriate SDK based on launcher detection:
- Claude Code → claude_agent_sdk
- GitHub Copilot CLI → copilot SDK

Public API:
    completion: Async LLM completion with auto-detected backend
"""

from amplihack.llm.client import completion

__all__ = ["completion"]
