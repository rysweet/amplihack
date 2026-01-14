"""
Agent Memory Hook for Amplifier.

Automatically injects relevant memory context before agent execution
and extracts learnings after agent execution.

Features:
- Detects agent references in prompts (@agents/*.md, /slash-commands)
- Injects relevant memories before agent execution
- Extracts and stores learnings from conversations
- Works with the Memory Tool backend
"""

from .detector import detect_agent_references, detect_slash_command_agent
from .hook import AgentMemoryHook, create_hook
from .injector import extract_learnings, inject_memory_for_agents

__all__ = [
    "AgentMemoryHook",
    "create_hook",
    "detect_agent_references",
    "detect_slash_command_agent",
    "inject_memory_for_agents",
    "extract_learnings",
]
