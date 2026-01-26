"""Agent Memory Hook - Amplifier wrapper for Claude Code memory system.

Delegates to Claude Code agent_memory_hook for:
- Detecting agent references in prompts
- Injecting relevant memory context before agent execution
- Extracting and storing learnings after session completion
"""

import logging
import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code hooks to path for imports
# Path: __init__.py -> amplifier_hook_memory/ -> hook-memory/ -> modules/ -> amplifier-bundle/ -> amplifier-amplihack/
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_CLAUDE_HOOKS = _PROJECT_ROOT / ".claude" / "tools" / "amplihack" / "hooks"

_DELEGATION_AVAILABLE = False
_IMPORT_ERROR: str | None = None

if _CLAUDE_HOOKS.exists():
    if str(_CLAUDE_HOOKS) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS))
    if str(_CLAUDE_HOOKS.parent) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS.parent))

    # Verify imports work
    try:
        import agent_memory_hook  # noqa: F401

        _DELEGATION_AVAILABLE = True
        logger.info(f"AgentMemoryHook: Delegation available from {_CLAUDE_HOOKS}")
    except ImportError as e:
        _IMPORT_ERROR = str(e)
        logger.warning(f"AgentMemoryHook: Import failed - {e}")
else:
    _IMPORT_ERROR = f"Claude hooks directory not found: {_CLAUDE_HOOKS}"
    logger.warning(_IMPORT_ERROR)


class AgentMemoryHook(Hook):
    """Injects and extracts agent memory across sessions."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._delegation_verified = False

    def _verify_delegation(self) -> bool:
        """Verify delegation is available."""
        if not self._delegation_verified:
            self._delegation_verified = True
            if _DELEGATION_AVAILABLE:
                logger.info("AgentMemoryHook: Delegation verified")
            else:
                logger.info(f"AgentMemoryHook: Delegation not available ({_IMPORT_ERROR})")
        return _DELEGATION_AVAILABLE

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle prompt:submit and session:end for memory operations."""
        if not self.enabled:
            return None

        if not self._verify_delegation():
            # No memory system available - fail silently
            return None

        try:
            if event == "prompt:submit":
                return await self._handle_prompt_submit(data)
            if event == "session:end":
                return await self._handle_session_end(data)
        except Exception as e:
            # Fail open - log but don't block
            logger.debug(f"Memory hook failed (continuing): {e}")

        return None

    async def _handle_prompt_submit(self, data: dict[str, Any]) -> HookResult | None:
        """Inject memory context before processing."""
        try:
            from agent_memory_hook import (
                detect_agent_references,
                detect_slash_command_agent,
                format_memory_injection_notice,
                inject_memory_for_agents,
            )

            prompt = data.get("prompt", data.get("userMessage", {}).get("text", ""))
            if not prompt:
                return None

            # Detect agent references
            agent_types = detect_agent_references(prompt)

            # Also check for slash command agents
            slash_agent = detect_slash_command_agent(prompt)
            if slash_agent:
                agent_types.append(slash_agent)

            if not agent_types:
                return None

            logger.info(f"AgentMemoryHook: Detected agents: {agent_types}")

            # Get session ID
            session_id = data.get("session_id", "hook_session")

            # Inject memory context for these agents
            enhanced_prompt, memory_metadata = await inject_memory_for_agents(
                prompt, agent_types, session_id
            )

            # Extract memory context (everything before the original prompt)
            memory_context = ""
            if enhanced_prompt != prompt:
                memory_context = enhanced_prompt.replace(prompt, "").strip()

            # Log memory injection
            notice = format_memory_injection_notice(memory_metadata)
            if notice:
                logger.info(notice)

            if memory_context:
                return HookResult(
                    modified_data={**data, "injected_context": memory_context},
                    metadata={
                        "delegation": "success",
                        "memory_injected": True,
                        "agents": agent_types,
                        "memories_count": memory_metadata.get("memories_injected", 0),
                    },
                )

        except ImportError as e:
            logger.warning(f"AgentMemoryHook: Import failed during execution - {e}")
        except Exception as e:
            logger.warning(f"AgentMemoryHook: Memory injection failed - {e}")

        return None

    async def _handle_session_end(self, data: dict[str, Any]) -> HookResult | None:
        """Extract learnings from session."""
        try:
            from agent_memory_hook import extract_learnings_from_conversation

            session_data = data.get("session_state", {})
            conversation_text = session_data.get("conversation", "")
            agent_types = session_data.get("agents", [])

            if not conversation_text or not agent_types:
                return None

            session_id = data.get("session_id", "hook_session")

            # Extract and store learnings
            learnings_metadata = await extract_learnings_from_conversation(
                conversation_text, agent_types, session_id
            )

            if learnings_metadata.get("learnings_stored", 0) > 0:
                logger.info(
                    f"AgentMemoryHook: Stored {learnings_metadata['learnings_stored']} learnings"
                )
                return HookResult(
                    modified_data=data,
                    metadata={
                        "delegation": "success",
                        "learnings_stored": learnings_metadata["learnings_stored"],
                    },
                )

        except ImportError as e:
            logger.warning(f"AgentMemoryHook: Import failed during execution - {e}")
        except Exception as e:
            logger.warning(f"AgentMemoryHook: Learning extraction failed - {e}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the agent memory hook."""
    hook = AgentMemoryHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["AgentMemoryHook", "mount"]
