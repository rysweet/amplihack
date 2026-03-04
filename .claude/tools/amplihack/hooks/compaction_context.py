"""
Compaction context data classes and timestamp utilities.

Extracted from compaction_validator.py to keep that module under 310 lines.
"""

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

_STALENESS_THRESHOLD_HOURS = 24


def _parse_timestamp_age(timestamp: str) -> tuple[float, bool]:
    """Parse timestamp and calculate age in hours and staleness.

    Security hardening:
    - Rejects non-string input and strings longer than 35 characters
    - Clamps future timestamps (negative age) to 0.0 unconditionally
    - Rejects implausible ages older than 10 years (87600 hours)

    Args:
        timestamp: ISO 8601 timestamp string (with or without timezone)

    Returns:
        Tuple of (age_hours, is_stale) where is_stale means > 24 hours old.
        Returns (0.0, False) if timestamp cannot be parsed or fails validation.
    """
    # Security: reject non-string and oversized inputs
    if not isinstance(timestamp, str) or len(timestamp) > 35:
        return (0.0, False)

    try:
        # Parse timestamp — handle Z-suffix and offset-aware forms
        if "+" in timestamp or timestamp.endswith("Z"):
            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            event_time = datetime.fromisoformat(timestamp)

        # Get current time in UTC
        now = datetime.now(UTC)

        # Make event_time timezone-aware if it isn't
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=UTC)

        age_hours = (now - event_time).total_seconds() / 3600

        # Clamp negative ages (future timestamps / clock skew) to zero
        if age_hours < 0:
            age_hours = 0.0

        # Reject implausible ages older than 10 years
        if age_hours > 87600:
            return (0.0, False)

        is_stale = age_hours > _STALENESS_THRESHOLD_HOURS
        return (age_hours, is_stale)
    except (ValueError, AttributeError):
        # Fail-open: Can't parse timestamp
        return (0.0, False)


@dataclass
class CompactionContext:
    """Compaction event metadata and diagnostics."""

    # Required attributes
    has_compaction_event: bool = False
    turn_at_compaction: int = 0
    messages_removed: int = 0
    pre_compaction_transcript: list[dict] | None = None
    timestamp: str | None = None
    is_stale: bool = False
    age_hours: float = 0.0
    has_security_violation: bool = False

    def __post_init__(self):
        """Calculate age_hours and is_stale after initialization."""
        if self.timestamp and self.has_compaction_event:
            age_hours, is_stale = _parse_timestamp_age(self.timestamp)
            self.age_hours = age_hours
            self.is_stale = is_stale

    def get_diagnostic_summary(self) -> str:
        """Generate human-readable diagnostic summary.

        Must include:
        - Turn number where compaction occurred
        - Number of messages removed
        - Word "compaction" (case-insensitive)
        """
        if not self.has_compaction_event:
            return "No compaction detected"

        summary_parts = [
            "Compaction detected",
            f"Turn: {self.turn_at_compaction}",
            f"Messages removed: {self.messages_removed}",
        ]

        if self.is_stale:
            summary_parts.append(f"Age: {self.age_hours:.1f} hours (stale)")

        if self.has_security_violation:
            summary_parts.append("Security violation detected")

        return " | ".join(summary_parts)


@dataclass
class ValidationResult:
    """Result of compaction validation."""

    # Required attributes
    passed: bool
    warnings: list[str] = field(default_factory=list)
    recovery_steps: list[str] = field(default_factory=list)
    compaction_context: CompactionContext = field(default_factory=CompactionContext)
    used_fallback: bool = False

    def get_summary(self) -> str:
        """Generate human-readable validation summary."""
        if self.passed:
            summary = "Validation: PASSED"
            if self.compaction_context.has_compaction_event:
                summary += f" (compaction at turn {self.compaction_context.turn_at_compaction})"
            return summary

        # Failed validation
        lines = ["Validation: FAILED"]

        if self.warnings:
            lines.append("\nWarnings:")
            for warning in self.warnings:
                lines.append(f"  - {warning}")

        if self.recovery_steps:
            lines.append("\nRecovery steps:")
            for i, step in enumerate(self.recovery_steps, 1):
                lines.append(f"  {i}. {step}")

        return "\n".join(lines)
