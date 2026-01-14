"""
Agent Memory Hook for Amplifier.

Integrates memory injection and learning extraction into the hook system.
"""

import logging
from pathlib import Path
from typing import Any

from .detector import get_all_detected_agents
from .injector import extract_learnings, inject_memory_for_agents

logger = logging.getLogger(__name__)


class AgentMemoryHook:
    """Amplifier hook for agent memory integration.

    Intercepts prompt submission to inject relevant memories and
    session end to extract learnings.
    """

    # Hook event types this responds to
    EVENTS = ["prompt:submit", "session:end"]

    def __init__(
        self,
        enabled: bool = True,
        token_budget: int = 2000,
        db_path: Path | None = None,
    ) -> None:
        """Initialize agent memory hook.

        Args:
            enabled: Whether memory integration is active
            token_budget: Max tokens for memory context injection
            db_path: Optional custom database path
        """
        self.enabled = enabled
        self.token_budget = token_budget
        self.db_path = db_path
        self._backend: Any = None
        self._detected_agents: list[str] = []
        self._session_transcript: str = ""

    @property
    def backend(self) -> Any:
        """Lazy-load memory backend."""
        if self._backend is None and self.enabled:
            try:
                from amplifier_tool_memory import MemoryBackend

                path = self.db_path or Path.home() / ".amplifier" / "runtime" / "memory.db"
                self._backend = MemoryBackend(path)
            except ImportError:
                logger.warning("Memory tool not installed, memory features disabled")
                self._backend = None
            except Exception as e:
                logger.warning(f"Failed to initialize memory backend: {e}")
                self._backend = None
        return self._backend

    def __call__(self, event: str, data: dict[str, Any]) -> dict[str, Any]:
        """Process a hook event.

        Args:
            event: Event type
            data: Event data

        Returns:
            Hook result
        """
        if not self.enabled:
            return {"decision": "approve", "hook": "agent_memory"}

        try:
            if event == "prompt:submit":
                return self._handle_prompt_submit(data)
            elif event == "session:end":
                return self._handle_session_end(data)
            else:
                return {"decision": "approve", "hook": "agent_memory"}
        except Exception as e:
            logger.exception("Agent memory hook error: %s", e)
            return {"decision": "approve", "hook": "agent_memory", "error": str(e)}

    def _handle_prompt_submit(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle prompt submission - inject relevant memories.

        Args:
            data: Event data with "prompt" key

        Returns:
            Hook result, potentially with modified prompt
        """
        prompt = data.get("prompt", "")
        session_id = data.get("session_id", "default")

        # Detect agents in prompt
        agents = get_all_detected_agents(prompt)
        self._detected_agents = agents

        if not agents:
            return {"decision": "approve", "hook": "agent_memory"}

        # Inject memory context
        enhanced_prompt, metadata = inject_memory_for_agents(
            prompt=prompt,
            agent_types=agents,
            memory_backend=self.backend,
            session_id=session_id,
            token_budget=self.token_budget,
        )

        result = {
            "decision": "approve",
            "hook": "agent_memory",
            "metadata": metadata,
        }

        # If memories were injected, include modified prompt
        if metadata.get("memories_injected", 0) > 0:
            result["modified_prompt"] = enhanced_prompt
            logger.info(f"Injected {metadata['memories_injected']} memories for agents: {agents}")

        return result

    def _handle_session_end(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle session end - extract and store learnings.

        Args:
            data: Event data with "transcript" key

        Returns:
            Hook result
        """
        transcript = data.get("transcript", "")
        session_id = data.get("session_id", "default")

        if not self._detected_agents:
            return {"decision": "approve", "hook": "agent_memory"}

        # Extract learnings
        metadata = extract_learnings(
            conversation_text=transcript,
            agent_types=self._detected_agents,
            memory_backend=self.backend,
            session_id=session_id,
        )

        if metadata.get("learnings_stored", 0) > 0:
            logger.info(f"Stored {metadata['learnings_stored']} learnings from session")

        return {
            "decision": "approve",
            "hook": "agent_memory",
            "metadata": metadata,
        }


def create_hook(config: dict | None = None) -> AgentMemoryHook:
    """Factory function to create an agent memory hook.

    Args:
        config: Optional configuration dict

    Returns:
        Configured AgentMemoryHook instance
    """
    config = config or {}
    return AgentMemoryHook(
        enabled=config.get("enabled", True),
        token_budget=config.get("token_budget", 2000),
        db_path=Path(config["db_path"]) if config.get("db_path") else None,
    )
