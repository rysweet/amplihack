"""Session Stop Hook - Amplifier wrapper for Claude Code session end processing.

Handles session completion including:
- Capturing learnings from the session
- Storing memories using MemoryCoordinator (SQLite or Neo4j)
- Extracting patterns, decisions, outcomes for future agent use
"""

import logging
import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code source to path for imports
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent.parent
_SRC_PATH = _PROJECT_ROOT / "src"
if _SRC_PATH.exists():
    sys.path.insert(0, str(_SRC_PATH))


class SessionStopHook(Hook):
    """Session completion and learning capture hook."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._memory_coordinator = None

    def _get_memory_coordinator(self, session_id: str):
        """Lazy load memory coordinator."""
        if self._memory_coordinator is None:
            try:
                from amplihack.memory.coordinator import MemoryCoordinator

                self._memory_coordinator = MemoryCoordinator(session_id=session_id)
            except ImportError as e:
                logger.debug(f"MemoryCoordinator not available: {e}")
                self._memory_coordinator = False
        return self._memory_coordinator if self._memory_coordinator else None

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle session:end events to capture learnings."""
        if not self.enabled:
            return None

        if event != "session:end":
            return None

        try:
            session_id = data.get("session_id", "hook_session")
            session_context = data.get("session_state", {})

            # Extract session information
            agent_type = session_context.get("agent_type", "general")
            agent_output = session_context.get("output", "")
            task_description = session_context.get("task", "")
            success = session_context.get("success", True)

            if not agent_output:
                # Nothing to learn from
                return None

            # Try to store learning using MemoryCoordinator
            coordinator = self._get_memory_coordinator(session_id)
            if coordinator:
                try:
                    from amplihack.memory.types import MemoryType

                    # Store learning as SEMANTIC memory (reusable knowledge)
                    learning_content = f"Agent {agent_type}: {agent_output[:500]}"

                    memory_id = coordinator.store(
                        content=learning_content,
                        memory_type=MemoryType.SEMANTIC,
                        agent_type=agent_type,
                        tags=["learning", "session_end"],
                        metadata={
                            "task": task_description,
                            "success": success,
                        },
                    )

                    if memory_id:
                        logger.info(f"Stored learning in memory system: {memory_id}")
                        return HookResult(
                            modified_data=data,
                            metadata={
                                "learning_stored": True,
                                "memory_id": memory_id,
                            },
                        )

                except Exception as e:
                    logger.debug(f"Memory storage failed: {e}")

            # Fallback: Log the learning even if we can't store it
            logger.info(
                f"Session ended - Agent: {agent_type}, Success: {success}, "
                f"Task: {task_description[:100] if task_description else 'N/A'}"
            )

            return HookResult(
                modified_data=data,
                metadata={"session_logged": True, "success": success},
            )

        except Exception as e:
            # Fail open - don't block session stop
            logger.debug(f"Session stop hook failed (continuing): {e}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the session stop hook."""
    hook = SessionStopHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["SessionStopHook", "mount"]
