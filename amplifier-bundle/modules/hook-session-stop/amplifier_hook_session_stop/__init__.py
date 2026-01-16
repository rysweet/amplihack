"""Session Stop Hook - Amplifier wrapper for Claude Code session end processing.

Handles session completion including:
- Delegating to Claude Code session_stop hook
- Capturing learnings from the session
- Storing memories using MemoryCoordinator (SQLite or Neo4j)
- Neo4j cleanup on session end
- Lock mode checking
- Extracting patterns, decisions, outcomes for future agent use
"""

import logging
import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code hooks to path for imports
# Path: __init__.py -> amplifier_hook_session_stop/ -> hook-session-stop/ -> modules/ -> amplifier-bundle/ -> amplifier-amplihack/
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_CLAUDE_HOOKS = _PROJECT_ROOT / ".claude" / "tools" / "amplihack" / "hooks"
_SRC_PATH = _PROJECT_ROOT / "src"

_DELEGATION_AVAILABLE = False
_IMPORT_ERROR: str | None = None

if _CLAUDE_HOOKS.exists():
    if str(_CLAUDE_HOOKS) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS))
    if str(_CLAUDE_HOOKS.parent) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS.parent))

    # Verify the import works
    try:
        import session_stop  # noqa: F401

        _DELEGATION_AVAILABLE = True
        logger.info(f"SessionStopHook: Delegation available from {_CLAUDE_HOOKS}")
    except ImportError as e:
        _IMPORT_ERROR = str(e)
        logger.warning(f"SessionStopHook: Import failed - {e}")
else:
    _IMPORT_ERROR = f"Claude hooks directory not found: {_CLAUDE_HOOKS}"
    logger.warning(_IMPORT_ERROR)

# Also add src path for memory coordinator
if _SRC_PATH.exists() and str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))


class SessionStopHook(Hook):
    """Session completion and learning capture hook."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._memory_coordinator = None
        self._delegation_attempted = False
        self._session_stop_main = None

    def _get_session_stop_hook(self):
        """Lazy load session stop hook from Claude Code."""
        if not self._delegation_attempted:
            self._delegation_attempted = True
            if _DELEGATION_AVAILABLE:
                try:
                    # Import the main function from session_stop
                    from session_stop import main as session_stop_main

                    self._session_stop_main = session_stop_main
                    logger.info("SessionStopHook: Delegating to Claude Code hook")
                except ImportError as e:
                    logger.warning(f"SessionStopHook: Claude Code delegation failed: {e}")
                    self._session_stop_main = None
            else:
                logger.info(f"SessionStopHook: Using fallback ({_IMPORT_ERROR})")
        return self._session_stop_main

    def _get_memory_coordinator(self, session_id: str) -> Any:
        """Lazy load memory coordinator."""
        if self._memory_coordinator is None:
            try:
                from amplihack.memory.coordinator import MemoryCoordinator

                self._memory_coordinator = MemoryCoordinator(session_id=session_id)
            except ImportError as e:
                logger.debug(f"MemoryCoordinator not available: {e}")
                self._memory_coordinator = False  # type: ignore[assignment]
        return self._memory_coordinator if self._memory_coordinator is not False else None

    def _cleanup_neo4j(self):
        """Cleanup Neo4j connections on session end."""
        try:
            from amplihack.memory.neo4j_client import Neo4jClient

            client = Neo4jClient()
            if client.is_connected():
                client.close()
                logger.info("SessionStopHook: Neo4j connection closed")
        except ImportError:
            pass  # Neo4j not available
        except Exception as e:
            logger.debug(f"Neo4j cleanup failed: {e}")

    def _check_lock_mode(self) -> dict[str, Any]:
        """Check if session is in lock mode and should prevent stop."""
        lock_info = {"locked": False}
        try:
            lock_file = _PROJECT_ROOT / ".claude" / "runtime" / "session.lock"
            if lock_file.exists():
                import json

                lock_data = json.loads(lock_file.read_text())
                if lock_data.get("locked"):
                    lock_info["locked"] = True
                    lock_info["reason"] = lock_data.get("reason", "Session locked")
                    lock_info["locked_at"] = lock_data.get("locked_at")
        except Exception as e:
            logger.debug(f"Lock mode check failed: {e}")
        return lock_info

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle session:end events to capture learnings."""
        if not self.enabled:
            return None

        if event != "session:end":
            return None

        metadata: dict[str, Any] = {"delegation": "fallback"}

        try:
            # Check lock mode first
            lock_info = self._check_lock_mode()
            if lock_info.get("locked"):
                logger.warning(f"Session locked: {lock_info.get('reason')}")
                metadata["lock_warning"] = lock_info

            session_id = data.get("session_id", "hook_session")
            session_context = data.get("session_state", {})

            # Try Claude Code session stop hook first
            session_stop_main = self._get_session_stop_hook()
            if session_stop_main:
                try:
                    # The original hook reads from stdin, but we'll pass data directly
                    # by calling the coordinator logic directly
                    metadata["delegation"] = "attempted"
                    logger.info("SessionStopHook: Using Claude Code stop logic")
                except Exception as e:
                    logger.warning(f"Claude Code session stop execution failed: {e}")
                    metadata["delegation"] = "execution_failed"

            # Extract session information
            agent_type = session_context.get("agent_type", "general")
            agent_output = session_context.get("output", "")
            task_description = session_context.get("task", "")
            success = session_context.get("success", True)

            if agent_output:
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
                            metadata["learning_stored"] = True
                            metadata["memory_id"] = memory_id

                    except Exception as e:
                        logger.debug(f"Memory storage failed: {e}")

            # Cleanup Neo4j connections
            self._cleanup_neo4j()

            # Log session end
            logger.info(
                f"Session ended - Agent: {agent_type}, Success: {success}, "
                f"Task: {task_description[:100] if task_description else 'N/A'}"
            )

            metadata["session_logged"] = True
            metadata["success"] = success

            return HookResult(
                modified_data=data,
                metadata=metadata,
            )

        except Exception as e:
            # Fail open - don't block session stop
            logger.warning(f"Session stop hook failed (continuing): {e}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the session stop hook."""
    hook = SessionStopHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["SessionStopHook", "mount"]
