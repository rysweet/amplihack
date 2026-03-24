"""Unified async LLM routing layer for amplihack.

Re-exports the primary public API:
    completion: async callable routing to claude_agent_sdk or CopilotClient
    SDK_AVAILABLE: True when at least one SDK is importable
"""

from amplihack.llm.client import SDK_AVAILABLE, completion

__all__ = ["completion", "SDK_AVAILABLE"]
