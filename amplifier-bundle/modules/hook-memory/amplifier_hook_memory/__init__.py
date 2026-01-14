"""Agent Memory Hook - Amplifier wrapper for Claude Code memory system.

Injects relevant memory context before agent execution and extracts
learnings after session completion for persistent storage.
"""

import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

# Add Claude Code hooks to path for imports
_CLAUDE_HOOKS = Path(__file__).parent.parent.parent.parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
if _CLAUDE_HOOKS.exists():
    sys.path.insert(0, str(_CLAUDE_HOOKS.parent.parent))


class AgentMemoryHook(Hook):
    """Injects and extracts agent memory across sessions."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._memory_hook = None

    def _get_memory_hook(self):
        """Lazy load memory hook to avoid import errors."""
        if self._memory_hook is None:
            try:
                from hooks import agent_memory_hook
                self._memory_hook = agent_memory_hook
            except ImportError:
                self._memory_hook = False
        return self._memory_hook if self._memory_hook else None

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle prompt:submit and session:end for memory operations."""
        if not self.enabled:
            return None

        memory_hook = self._get_memory_hook()
        if not memory_hook:
            return None

        try:
            if event == "prompt:submit":
                # Inject memory context before processing
                prompt = data.get("prompt", "")
                agent_ref = memory_hook.detect_agent_reference(prompt)
                
                if agent_ref:
                    memories = memory_hook.get_relevant_memories(agent_ref)
                    if memories:
                        # Inject memories into context
                        injected = memory_hook.format_memory_context(memories)
                        return HookResult(
                            modified_data={**data, "injected_context": injected},
                            metadata={"memory_injected": True, "agent": agent_ref}
                        )

            elif event == "session:end":
                # Extract learnings from session
                session_data = data.get("session_state", {})
                learnings = memory_hook.extract_learnings(session_data)
                
                if learnings:
                    memory_hook.store_learnings(learnings)
                    return HookResult(
                        modified_data=data,
                        metadata={"learnings_stored": len(learnings)}
                    )

        except Exception:
            # Fail open
            pass

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the agent memory hook."""
    hook = AgentMemoryHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["AgentMemoryHook", "mount"]
