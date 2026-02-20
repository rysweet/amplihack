"""SDK-agnostic goal-seeking agent abstraction layer.

Provides a unified interface for building goal-seeking learning agents
across multiple AI SDKs:
- Claude Agent SDK (Anthropic)
- Mini-framework (LearningAgent + litellm)

Each SDK implementation inherits from GoalSeekingAgent and provides
the same capabilities: learn, remember, teach, apply, with native
SDK tools + custom learning tools + amplihack memory.

Philosophy:
- SDK-agnostic: same interface regardless of underlying SDK
- Memory-agnostic: uses amplihack-memory-lib (Kuzu today, anything tomorrow)
- Goal-oriented: agents form evaluable goals, not just answer questions
"""

from .base import AgentResult, AgentTool, GoalSeekingAgent, SDKType

__all__ = ["GoalSeekingAgent", "AgentTool", "AgentResult", "SDKType"]
