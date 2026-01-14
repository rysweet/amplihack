"""
Power Steering Hook for Amplifier.

Integrates power steering verification into Amplifier's hook system,
blocking session termination when work is incomplete.
"""

import logging
from pathlib import Path
from typing import Any

from .checker import PowerSteeringChecker, PowerSteeringResult

logger = logging.getLogger(__name__)


class PowerSteeringHook:
    """Amplifier hook that verifies session completion before allowing stop.

    This hook intercepts session end events and runs power steering analysis
    to ensure work is truly complete. If incomplete, it blocks the stop and
    provides actionable continuation prompts.

    Philosophy:
    - Fail-Open: Never block users due to bugs
    - Zero-BS: No stubs, everything works
    - Modular: Self-contained, pluggable into any Amplifier session
    """

    # Hook event types this responds to
    EVENTS = ["session:end", "session:stop"]

    def __init__(
        self,
        project_root: Path | None = None,
        enabled: bool = True,
        verbose: bool = False,
    ) -> None:
        """Initialize the power steering hook.

        Args:
            project_root: Root directory of the project (auto-detected if None)
            enabled: Whether power steering is active
            verbose: Enable verbose logging
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.enabled = enabled
        self.verbose = verbose
        self._checker: PowerSteeringChecker | None = None

    @property
    def checker(self) -> PowerSteeringChecker:
        """Lazy-load the checker."""
        if self._checker is None:
            self._checker = PowerSteeringChecker(self.project_root)
        return self._checker

    def __call__(self, event: str, data: dict[str, Any]) -> dict[str, Any]:
        """Process a hook event.

        Args:
            event: Event type (e.g., "session:end")
            data: Event data including transcript, session_id, etc.

        Returns:
            Hook result with decision to approve or block
        """
        if not self.enabled:
            return self._approve("Power steering disabled")

        if event not in self.EVENTS:
            return self._approve(f"Event {event} not handled by power steering")

        try:
            return self._handle_stop(data)
        except Exception as e:
            # Fail-open: never block due to errors
            logger.exception("Power steering error, approving stop: %s", e)
            return self._approve(f"Error in power steering: {e}")

    def _handle_stop(self, data: dict[str, Any]) -> dict[str, Any]:
        """Handle session stop event.

        Args:
            data: Event data with transcript and session info

        Returns:
            Decision to approve or block with reason
        """
        transcript = data.get("transcript", "")
        session_id = data.get("session_id", "unknown")

        if not transcript:
            return self._approve("No transcript available for analysis")

        # Check for shutdown signal (don't block during forced shutdown)
        if data.get("force_stop") or data.get("shutdown"):
            return self._approve("Forced stop requested")

        # Run power steering analysis
        if self.verbose:
            logger.info("Running power steering analysis for session %s", session_id)

        result = self.checker.check(
            transcript=transcript,
            session_id=session_id,
            progress_callback=self._log_progress if self.verbose else None,
        )

        if result.auto_approved:
            return self._approve(
                f"Auto-approved after {result.consecutive_blocks} consecutive blocks"
            )

        if result.should_block:
            return self._block(result)

        return self._approve(result.summary())

    def _approve(self, reason: str) -> dict[str, Any]:
        """Return approval decision."""
        if self.verbose:
            logger.info("Power steering: APPROVE - %s", reason)
        return {
            "decision": "approve",
            "reason": reason,
            "hook": "power_steering",
        }

    def _block(self, result: PowerSteeringResult) -> dict[str, Any]:
        """Return block decision with continuation prompt."""
        if self.verbose:
            logger.info("Power steering: BLOCK - %s", result.summary())

        return {
            "decision": "block",
            "reason": result.continuation_prompt,
            "hook": "power_steering",
            "details": {
                "failed_blockers": [r.consideration_id for r in result.failed_blockers],
                "warnings": [r.consideration_id for r in result.warnings],
                "consecutive_blocks": result.consecutive_blocks,
                "session_type": result.session_type.value,
            },
        }

    def _log_progress(self, message: str) -> None:
        """Log progress updates."""
        logger.info("Power steering: %s", message)


def create_hook(config: dict | None = None) -> PowerSteeringHook:
    """Factory function to create a power steering hook from config.

    Args:
        config: Optional configuration dict with keys:
            - project_root: Path to project root
            - enabled: Whether to enable power steering
            - verbose: Enable verbose logging

    Returns:
        Configured PowerSteeringHook instance
    """
    config = config or {}
    return PowerSteeringHook(
        project_root=config.get("project_root"),
        enabled=config.get("enabled", True),
        verbose=config.get("verbose", False),
    )
