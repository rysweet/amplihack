"""Power Steering Hook - Amplifier wrapper for Claude Code power steering.

Verifies session completeness before allowing stop, checking against
21 considerations to ensure work is properly finished.
"""

import sys
from pathlib import Path
from typing import Any

from amplifier_core.protocols import Hook, HookResult

# Add Claude Code hooks to path for imports
_CLAUDE_HOOKS = Path(__file__).parent.parent.parent.parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
if _CLAUDE_HOOKS.exists():
    sys.path.insert(0, str(_CLAUDE_HOOKS.parent.parent))


class PowerSteeringHook(Hook):
    """Verifies session completeness using power steering checks."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self._checker = None

    def _get_checker(self):
        """Lazy load checker to avoid import errors if not available."""
        if self._checker is None:
            try:
                from hooks.power_steering_checker import PowerSteeringChecker
                self._checker = PowerSteeringChecker()
            except ImportError:
                self._checker = False  # Mark as unavailable
        return self._checker if self._checker else None

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult | None:
        """Handle session:end events to verify completion."""
        if not self.enabled:
            return None

        if event != "session:end":
            return None

        checker = self._get_checker()
        if not checker:
            # Fail open - don't block if checker unavailable
            return None

        try:
            # Get session transcript/state from data
            session_state = data.get("session_state", {})
            result = checker.check_completion(session_state)

            if not result.get("complete", True):
                # Return warning but don't block
                return HookResult(
                    modified_data=data,
                    metadata={
                        "power_steering": {
                            "complete": False,
                            "incomplete_considerations": result.get("incomplete", []),
                            "message": "Session may have incomplete work"
                        }
                    }
                )
        except Exception:
            # Fail open
            pass

        return None


def mount(coordinator, config: dict[str, Any] | None = None) -> None:
    """Mount the power steering hook."""
    hook = PowerSteeringHook(config)
    coordinator.mount("hooks", hook)


__all__ = ["PowerSteeringHook", "mount"]
