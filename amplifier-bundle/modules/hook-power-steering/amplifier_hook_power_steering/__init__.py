"""Power Steering Hook - Amplifier wrapper for Claude Code power steering.

Delegates to Claude Code PowerSteeringChecker for:
- Verifying session completeness before allowing stop
- Checking against 21 considerations to ensure work is properly finished
- Providing actionable continuation prompts for incomplete work
"""

import logging
import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

logger = logging.getLogger(__name__)

# Add Claude Code hooks to path for imports
# Path: __init__.py -> amplifier_hook_power_steering/ -> hook-power-steering/ -> modules/ -> amplifier-bundle/ -> amplifier-amplihack/
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
        import power_steering_checker  # noqa: F401

        _DELEGATION_AVAILABLE = True
        logger.info(f"PowerSteeringHook: Delegation available from {_CLAUDE_HOOKS}")
    except ImportError as e:
        _IMPORT_ERROR = str(e)
        logger.warning(f"PowerSteeringHook: Import failed - {e}")
else:
    _IMPORT_ERROR = f"Claude hooks directory not found: {_CLAUDE_HOOKS}"
    logger.warning(_IMPORT_ERROR)


class PowerSteeringHook(Hook):
    """Verifies session completeness using power steering checks."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._checker = None
        self._delegation_attempted = False

    def _get_checker(self):
        """Lazy load checker to avoid import errors if not available."""
        if not self._delegation_attempted:
            self._delegation_attempted = True
            if _DELEGATION_AVAILABLE:
                try:
                    from power_steering_checker import PowerSteeringChecker

                    self._checker = PowerSteeringChecker()
                    logger.info("PowerSteeringHook: Delegating to PowerSteeringChecker")
                except ImportError as e:
                    logger.warning(f"PowerSteeringHook: Delegation failed - {e}")
                    self._checker = None
            else:
                logger.info(f"PowerSteeringHook: Checker not available ({_IMPORT_ERROR})")
        return self._checker

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle session:end events to verify completion."""
        if not self.enabled:
            return None

        if event != "session:end":
            return None

        checker = self._get_checker()
        if not checker:
            # Fail open - don't block if checker unavailable
            logger.debug("PowerSteeringHook: Checker not available, allowing stop")
            return HookResult(
                modified_data=data,
                metadata={"delegation": "unavailable", "power_steering": {"skipped": True}},
            )

        try:
            # Get session transcript/state from data
            session_state = data.get("session_state", {})

            # The checker has multiple methods - try check_completion first
            if hasattr(checker, "check_completion"):
                result = checker.check_completion(session_state)
            elif hasattr(checker, "analyze"):
                result = checker.analyze(session_state)
            else:
                # Try to call it directly
                result = checker(session_state)

            if not result:
                return HookResult(
                    modified_data=data,
                    metadata={"delegation": "success", "power_steering": {"complete": True}},
                )

            # Check if result indicates incomplete work
            is_complete = result.get("complete", True) if isinstance(result, dict) else True

            if not is_complete:
                incomplete_items = result.get("incomplete", []) if isinstance(result, dict) else []
                logger.info(
                    f"PowerSteeringHook: Session may have incomplete work: {incomplete_items}"
                )

                # Return warning but don't block
                return HookResult(
                    modified_data=data,
                    metadata={
                        "delegation": "success",
                        "power_steering": {
                            "complete": False,
                            "incomplete_considerations": incomplete_items,
                            "message": "Session may have incomplete work",
                        },
                    },
                )

            return HookResult(
                modified_data=data,
                metadata={"delegation": "success", "power_steering": {"complete": True}},
            )

        except Exception as e:
            # Fail open - log but don't block
            logger.debug(f"Power steering check failed (continuing): {e}")
            return HookResult(
                modified_data=data,
                metadata={"delegation": "error", "power_steering": {"error": str(e)}},
            )


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the power steering hook."""
    hook = PowerSteeringHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["PowerSteeringHook", "mount"]
