#!/usr/bin/env python3
"""
Compaction Validator: Validates conversation compaction and data preservation.

WHY THIS EXISTS:
Defensive safeguard against regression of issue #1962 where Claude's context
window compaction could lose critical session data (TODOs, objectives, recent
work). This validator detects compaction events and verifies data preservation,
providing actionable recovery steps when loss is detected.

See: https://github.com/rysweet/amplihack/issues/1962

Detects when Claude's context window was compacted (old messages removed) and
validates that critical session data was preserved. Provides actionable
diagnostics for recovery when data is lost.

Philosophy:
- Fail-open: Default to "valid" when uncertain
- Actionable: Provide specific recovery steps, not just "data lost"
- Fast: Validation completes in < 100ms for typical transcripts
- Zero-BS: No stubs, every function works

Public API:
    CompactionValidator - Main validator class
    CompactionContext - Compaction event metadata
    ValidationResult - Validation result with recovery steps
"""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

__all__ = [
    "CompactionValidator",
    "CompactionContext",
    "ValidationResult",
]


def _parse_timestamp_age(timestamp: str) -> tuple[float, bool]:
    """Parse timestamp and calculate age in hours and staleness.

    Args:
        timestamp: ISO 8601 timestamp string (with or without timezone)

    Returns:
        Tuple of (age_hours, is_stale) where is_stale means > 24 hours old.
        Returns (0.0, False) if timestamp cannot be parsed.
    """
    try:
        # Parse timestamp
        timestamp_str = timestamp.replace("Z", "")
        if "+" in timestamp or timestamp.endswith("Z"):
            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            event_time = datetime.fromisoformat(timestamp_str)

        # Get current time in UTC
        now = datetime.now(UTC)

        # Make event_time timezone-aware if it isn't
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=UTC)

        age_delta = now - event_time
        age_hours = age_delta.total_seconds() / 3600
        is_stale = age_hours > 24
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
            object.__setattr__(self, "age_hours", age_hours)
            object.__setattr__(self, "is_stale", is_stale)

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


class CompactionValidator:
    """Validates conversation compaction and data preservation."""

    def __init__(self, project_root: Path):
        """Initialize validator with project root.

        Args:
            project_root: Project root directory path
        """
        self.project_root = Path(project_root)
        self.runtime_dir = self.project_root / ".claude" / "runtime" / "power-steering"

    def load_compaction_context(self, session_id: str) -> CompactionContext:
        """Load compaction context from runtime data.

        Must handle:
        1. Missing compaction_events.json file (fail-open)
        2. Corrupt JSON (fail-open)
        3. Missing pre-compaction transcript file (fail-open, but mark event)
        4. Path traversal attacks (set has_security_violation)
        5. Multiple events (return most recent by timestamp)
        6. Stale events (> 24 hours, set is_stale=True)

        Args:
            session_id: Session identifier to find events for

        Returns:
            CompactionContext with loaded data or safe defaults
        """
        events_file = self.runtime_dir / "compaction_events.json"

        # Fail-open: Missing file
        if not events_file.exists():
            return CompactionContext()

        # Load events
        try:
            with open(events_file) as f:
                events_data = json.load(f)
        except (json.JSONDecodeError, OSError):
            # Fail-open: Corrupt JSON
            return CompactionContext()

        # Filter events for this session
        session_events = [e for e in events_data if e.get("session_id") == session_id]

        if not session_events:
            return CompactionContext()

        # Sort by timestamp (most recent first)
        try:
            session_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        except (TypeError, AttributeError):
            # Fail-open: Can't sort timestamps
            pass

        # Use most recent event
        event_data = session_events[0]

        # Build context
        context = CompactionContext(
            has_compaction_event=True,
            turn_at_compaction=event_data.get("turn_number", 0),
            messages_removed=event_data.get("messages_removed", 0),
            timestamp=event_data.get("timestamp"),
        )

        # Calculate age
        if context.timestamp:
            age_hours, is_stale = _parse_timestamp_age(context.timestamp)
            context.age_hours = age_hours
            context.is_stale = is_stale

        # Load pre-compaction transcript
        transcript_path_str = event_data.get("pre_compaction_transcript_path")
        if transcript_path_str:
            transcript_path = Path(transcript_path_str)

            # Security: Check for path traversal
            try:
                resolved_path = transcript_path.resolve()
                if not resolved_path.is_relative_to(self.project_root.resolve()):
                    context.has_security_violation = True
                    # Don't load the transcript but continue - will use fallback
                    return context
            except (ValueError, OSError):
                # Can't resolve path - treat as missing file (will use fallback)
                pass

            # Load transcript
            try:
                if transcript_path.exists():
                    with open(transcript_path) as f:
                        context.pre_compaction_transcript = json.load(f)
            except (json.JSONDecodeError, OSError):
                # Fail-open: Can't load transcript, but event exists
                pass

        return context

    def validate(self, transcript: list[dict] | None, session_id: str) -> ValidationResult:
        """Validate entire transcript for compaction data loss.

        Must:
        1. Load compaction context for session
        2. If no compaction detected, return passed
        3. If compaction detected, validate critical data preservation
        4. Use provided transcript as fallback if pre-compaction unavailable
        5. Generate specific warnings and recovery steps

        Args:
            transcript: Current transcript (may be None)
            session_id: Session identifier

        Returns:
            ValidationResult with validation outcome
        """
        # Load compaction context
        context = self.load_compaction_context(session_id)

        # No compaction detected - pass
        if not context.has_compaction_event:
            return ValidationResult(passed=True, compaction_context=context)

        # Get pre-compaction transcript (None if security violation)
        pre_compaction = (
            context.pre_compaction_transcript if not context.has_security_violation else None
        )
        used_fallback = False

        # Check if we need to use fallback
        if pre_compaction is None:
            if transcript is not None:
                # Use provided transcript as fallback
                pre_compaction = transcript
                used_fallback = True
            else:
                # No transcript available - fail-open
                return ValidationResult(
                    passed=True,  # Fail-open
                    compaction_context=context,
                    used_fallback=False,
                )

        # Ensure we have transcript for validation
        if transcript is None:
            return ValidationResult(
                passed=True,  # Fail-open
                compaction_context=context,
                used_fallback=used_fallback,
            )

        # Run validation checks
        all_warnings = []
        all_recovery_steps = []

        # Check TODOs
        todo_result = self.validate_todos(pre_compaction, transcript)
        if not todo_result.passed:
            all_warnings.extend(todo_result.warnings)
            all_recovery_steps.extend(todo_result.recovery_steps)

        # Check objectives
        obj_result = self.validate_objectives(pre_compaction, transcript)
        if not obj_result.passed:
            all_warnings.extend(obj_result.warnings)
            all_recovery_steps.extend(obj_result.recovery_steps)

        # Check recent context
        recent_result = self.validate_recent_context(pre_compaction, transcript, context)
        if not recent_result.passed:
            all_warnings.extend(recent_result.warnings)
            all_recovery_steps.extend(recent_result.recovery_steps)

        # Build final result
        passed = len(all_warnings) == 0

        return ValidationResult(
            passed=passed,
            warnings=all_warnings,
            recovery_steps=all_recovery_steps,
            compaction_context=context,
            used_fallback=used_fallback,
        )

    def validate_todos(
        self, pre_compaction: list[dict], post_compaction: list[dict]
    ) -> ValidationResult:
        """Validate TODO items preserved after compaction.

        Must detect:
        - TODOs present in pre-compaction but missing in post-compaction
        - Provide recovery step about recreating TODO list

        Args:
            pre_compaction: Transcript before compaction
            post_compaction: Transcript after compaction

        Returns:
            ValidationResult indicating if TODOs preserved
        """

        # Extract TODOs from transcripts
        def extract_todos(transcript: list[dict]) -> set[str]:
            """Extract TODO items from transcript."""
            todos = set()
            todo_pattern = re.compile(r"TODO:\s*(.+?)(?:\n|$)", re.IGNORECASE)

            for message in transcript:
                content = message.get("content", "")
                if isinstance(content, str):
                    matches = todo_pattern.findall(content)
                    for match in matches:
                        # Normalize whitespace
                        todos.add(match.strip())

            return todos

        pre_todos = extract_todos(pre_compaction)
        post_todos = extract_todos(post_compaction)

        # Check if TODOs were lost
        # Lost = had TODOs before but significantly fewer or none after
        if pre_todos:
            # Check if we lost TODOs
            lost_todos = pre_todos - post_todos

            # If we lost more than half, or lost all, flag it
            if not post_todos or len(lost_todos) > len(pre_todos) / 2:
                return ValidationResult(
                    passed=False,
                    warnings=["TODO items lost after compaction"],
                    recovery_steps=[
                        "Review recent work in last 10-20 turns",
                        "Recreate TODO list using TodoWrite",
                        "Check git commits for completed items",
                    ],
                )

        # TODOs preserved or none existed
        return ValidationResult(passed=True)

    def validate_objectives(
        self, pre_compaction: list[dict], post_compaction: list[dict]
    ) -> ValidationResult:
        """Validate session objectives still clear after compaction.

        Must detect:
        - Original user goal unclear in post-compaction transcript
        - Provide recovery step about restating objective

        Args:
            pre_compaction: Transcript before compaction
            post_compaction: Transcript after compaction

        Returns:
            ValidationResult indicating if objectives clear
        """

        # Check if transcript has clear objectives
        def has_clear_objective(transcript: list[dict]) -> bool:
            """Check if transcript has clear user objective."""
            # Look for user messages with goal-indicating words
            goal_keywords = [
                "implement",
                "build",
                "create",
                "fix",
                "add",
                "need to",
                "want to",
                "should",
                "goal",
                "objective",
                "task",
                "working on",
                "todo",
            ]

            for message in transcript:
                content = message.get("content", "").lower()
                # Check both user and assistant messages
                # (assistant TODO lists can indicate objectives)
                if any(keyword in content for keyword in goal_keywords):
                    return True

            return False

        pre_has_objective = has_clear_objective(pre_compaction)
        post_has_objective = has_clear_objective(post_compaction)

        # If pre had objective but post doesn't, objective was lost
        if pre_has_objective and not post_has_objective:
            return ValidationResult(
                passed=False,
                warnings=["Session objectives unclear after compaction"],
                recovery_steps=[
                    "Explicitly restate your current goal in the conversation",
                    "Review recent work to understand current objective",
                ],
            )

        return ValidationResult(passed=True)

    def validate_recent_context(
        self, pre_compaction: list[dict], post_compaction: list[dict], context: CompactionContext
    ) -> ValidationResult:
        """Validate recent context (last 10 turns) preserved.

        Checks that important recent messages are preserved. Uses two strategies:
        1. For small transcripts: Check messages after the removed portion
        2. For large transcripts: Check the last 20 messages

        Args:
            pre_compaction: Transcript before compaction
            post_compaction: Transcript after compaction
            context: Compaction context with metadata

        Returns:
            ValidationResult indicating if recent context intact
        """
        messages_removed = context.messages_removed
        post_content = [msg.get("content", "") for msg in post_compaction]

        # Strategy depends on transcript size
        if len(pre_compaction) < 20:
            # Small transcript: Assume first N messages were removed
            # Check messages after index N
            if messages_removed > 0 and len(pre_compaction) > messages_removed:
                messages_to_check = pre_compaction[messages_removed:]
            else:
                messages_to_check = pre_compaction
        else:
            # Large transcript: Check last 20 messages
            # This catches cases where messages near the end were removed
            messages_to_check = pre_compaction[-20:]

        if not messages_to_check:
            return ValidationResult(passed=True)

        # Check which messages are in post
        check_content = [msg.get("content", "") for msg in messages_to_check]
        preserved_count = sum(1 for content in check_content if content in post_content)

        # Calculate preservation rate
        preservation_rate = preserved_count / len(check_content) if check_content else 1.0

        # Determine threshold based on transcript size
        # For very small transcripts, be more lenient (one message lost is OK)
        if len(check_content) <= 3:
            threshold = 0.5  # At least 50% preserved for small transcripts
        else:
            threshold = 0.85  # 85% for larger transcripts

        # If we lost more than the threshold, flag it
        if preservation_rate < threshold:
            return ValidationResult(
                passed=False,
                warnings=["Recent context incomplete after compaction"],
                recovery_steps=[
                    "Review last 10-20 turns for missing context",
                    "Check if recent code changes are still visible",
                ],
            )

        return ValidationResult(passed=True)
