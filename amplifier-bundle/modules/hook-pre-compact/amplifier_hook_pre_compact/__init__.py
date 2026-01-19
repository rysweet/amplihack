"""Pre-Compact Hook - Amplifier wrapper for transcript export.

Delegates to Claude Code pre_compact hook for:
- Exporting conversation transcript before context compaction
- Preserving full session history
- Context preservation across compaction events
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code hooks to path for imports
# Path: __init__.py -> amplifier_hook_pre_compact/ -> hook-pre-compact/ -> modules/ -> amplifier-bundle/ -> amplifier-amplihack/
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
_CLAUDE_HOOKS = _PROJECT_ROOT / ".claude" / "tools" / "amplihack" / "hooks"

_DELEGATION_AVAILABLE = False
_IMPORT_ERROR: str | None = None

if _CLAUDE_HOOKS.exists():
    if str(_CLAUDE_HOOKS) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS))
    if str(_CLAUDE_HOOKS.parent) not in sys.path:
        sys.path.insert(0, str(_CLAUDE_HOOKS.parent))

    # Verify the import works
    try:
        import pre_compact  # noqa: F401

        _DELEGATION_AVAILABLE = True
        logger.info(f"PreCompactHook: Delegation available from {_CLAUDE_HOOKS}")
    except ImportError as e:
        _IMPORT_ERROR = str(e)
        logger.warning(f"PreCompactHook: Import failed - {e}")
else:
    _IMPORT_ERROR = f"Claude hooks directory not found: {_CLAUDE_HOOKS}"
    logger.warning(_IMPORT_ERROR)


class PreCompactHook(Hook):
    """Exports transcript before context compaction."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.output_dir = Path(self.config.get("output_dir", ".amplifier/transcripts"))
        self._claude_hook = None
        self._delegation_attempted = False

    def _get_claude_hook(self):
        """Lazy load pre compact hook from Claude Code."""
        if not self._delegation_attempted:
            self._delegation_attempted = True
            if _DELEGATION_AVAILABLE:
                try:
                    from pre_compact import PreCompactHook as ClaudePreCompactHook

                    self._claude_hook = ClaudePreCompactHook()
                    logger.info("PreCompactHook: Delegating to Claude Code hook")
                except ImportError as e:
                    logger.warning(f"PreCompactHook: Claude Code delegation failed: {e}")
                    self._claude_hook = None
            else:
                logger.info(f"PreCompactHook: Using fallback ({_IMPORT_ERROR})")
        return self._claude_hook

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle context:compact events to export transcript."""
        if not self.enabled:
            return None

        if event != "context:compact":
            return None

        try:
            # Try to delegate to Claude Code hook first
            claude_hook = self._get_claude_hook()
            if claude_hook:
                try:
                    result = claude_hook.process(data)
                    if result:
                        logger.info("PreCompactHook: Delegation successful")
                        return HookResult(
                            modified_data=data,
                            metadata={
                                "delegation": "success",
                                "transcript_exported": result.get("status") == "success",
                                "transcript_path": result.get("transcript_path"),
                            },
                        )
                except Exception as e:
                    logger.warning(f"Claude Code pre compact hook failed: {e}")
                    # Fall through to fallback

            # Fallback implementation
            logger.info("PreCompactHook: Using fallback implementation")

            # Get messages before compaction
            messages = data.get("messages", [])
            session_id = data.get("session_id", "unknown")

            if not messages:
                return HookResult(
                    modified_data=data,
                    metadata={
                        "delegation": "fallback",
                        "transcript_exported": False,
                        "reason": "no_messages",
                    },
                )

            # Create output directory
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # Generate transcript filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            transcript_file = self.output_dir / f"transcript_{session_id}_{timestamp}.json"

            # Export transcript
            transcript = {
                "session_id": session_id,
                "exported_at": datetime.now().isoformat(),
                "message_count": len(messages),
                "messages": messages,
                "compaction_reason": data.get("reason", "unknown"),
            }

            transcript_file.write_text(json.dumps(transcript, indent=2, default=str))
            logger.info(f"PreCompactHook: Exported transcript to {transcript_file}")

            return HookResult(
                modified_data=data,
                metadata={
                    "delegation": "fallback",
                    "transcript_exported": True,
                    "transcript_file": str(transcript_file),
                    "message_count": len(messages),
                },
            )

        except Exception as e:
            # Fail open - log but don't block
            logger.debug(f"Pre-compact transcript export failed (continuing): {e}")

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the pre-compact hook."""
    hook = PreCompactHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["PreCompactHook", "mount"]
