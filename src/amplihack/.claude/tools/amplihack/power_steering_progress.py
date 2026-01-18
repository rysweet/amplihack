#!/usr/bin/env python3
"""
Power-Steering Progress Visibility Module

Provides real-time progress updates during power-steering analysis with
verbosity control.

Philosophy:
- Ruthlessly Simple: Single-purpose progress tracking
- Fail-Safe: Progress display never breaks checker
- Zero-BS: No stubs, every function works
- Modular: Self-contained brick that plugs into checker

Usage:
    from power_steering_progress import ProgressTracker

    tracker = ProgressTracker(verbosity="summary")
    result = checker.check(transcript, session_id, progress_callback=tracker.emit)
    tracker.display_summary()
"""

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class VerbosityMode(Enum):
    """Progress verbosity levels."""

    OFF = "off"  # Silent - no progress output
    SUMMARY = "summary"  # Start/end only
    DETAILED = "detailed"  # All progress events


@dataclass
class ProgressEvent:
    """Progress event from power-steering checker."""

    event_type: str  # "start", "category", "consideration", "complete"
    message: str
    details: dict | None = None


class ProgressTracker:
    """Track and display power-steering analysis progress.

    Features:
    - Three verbosity modes: OFF, SUMMARY, DETAILED
    - Preference reading from USER_PREFERENCES.md
    - Fail-safe design (exceptions never break checker)

    Design:
    - Callback-based progress (checker calls tracker.emit)
    - Synchronous operation (no async complexity)
    - Simple stderr output (no fancy libraries)
    """

    def __init__(
        self,
        verbosity: str | None = None,
        project_root: Path | None = None,
    ):
        """Initialize progress tracker.

        Args:
            verbosity: Verbosity level (off/summary/detailed) or None to auto-detect
            project_root: Project root directory (auto-detected if None)
        """
        self.project_root = project_root or self._detect_project_root()
        self.events: list[ProgressEvent] = []

        # Auto-detect verbosity from preferences if not provided
        if verbosity is None:
            prefs = self._read_preferences()
            verbosity = prefs.get("verbosity", "summary")

        # Set verbosity mode
        try:
            self.verbosity = VerbosityMode(verbosity)
        except ValueError:
            self.verbosity = VerbosityMode.SUMMARY

        # Counters for summary
        self.total_considerations = 0
        self.checked_considerations = 0
        self.categories_processed: list[str] = []

    def _detect_project_root(self) -> Path:
        """Auto-detect project root by finding .claude marker.

        Returns:
            Project root path

        Raises:
            ValueError: If project root cannot be found
        """
        current = Path(__file__).resolve().parent
        for _ in range(10):  # Max 10 levels up
            if (current / ".claude").exists():
                return current
            if current == current.parent:
                break
            current = current.parent

        raise ValueError("Could not find project root with .claude marker")

    def _read_preferences(self) -> dict:
        """Read user preferences from USER_PREFERENCES.md.

        Returns:
            Dict with preferences (empty if file not found)
        """
        try:
            prefs_path = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"
            if not prefs_path.exists():
                return {}

            content = prefs_path.read_text()

            # Extract preferences using simple parsing
            prefs = {}

            # Parse verbosity
            if "### Verbosity" in content:
                section = content.split("### Verbosity")[1].split("###")[0]
                for line in section.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # First non-comment line after header is the value
                        prefs["verbosity"] = line.lower()
                        break

            # Parse communication style
            if "### Communication Style" in content:
                section = content.split("### Communication Style")[1].split("###")[0]
                for line in section.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#"):
                        break

            return prefs

        except Exception:
            # Fail-safe: Return empty dict on any error
            return {}

    def emit(self, event_type: str, message: str, details: dict | None = None) -> None:
        """Emit a progress event (called by checker).

        Args:
            event_type: Event type (start/category/consideration/complete)
            message: Progress message
            details: Optional event details
        """
        try:
            # Create event
            event = ProgressEvent(event_type=event_type, message=message, details=details)
            self.events.append(event)

            # Update counters
            if event_type == "consideration":
                self.checked_considerations += 1
            elif event_type == "category":
                if details and "category" in details:
                    cat = details["category"]
                    if cat not in self.categories_processed:
                        self.categories_processed.append(cat)

            # Display based on verbosity
            if self.verbosity == VerbosityMode.OFF:
                return
            if self.verbosity == VerbosityMode.SUMMARY:
                if event_type in ("start", "complete"):
                    self._display_event(event)
            elif self.verbosity == VerbosityMode.DETAILED:
                self._display_event(event)

        except Exception:
            # Fail-safe: Never raise exceptions that would break checker
            pass

    def _display_event(self, event: ProgressEvent) -> None:
        """Display a progress event to stderr.

        Args:
            event: Progress event to display
        """
        try:
            # Format message
            msg = event.message

            # Add progress indicator for detailed mode
            if self.verbosity == VerbosityMode.DETAILED and event.event_type == "consideration":
                if self.total_considerations > 0:
                    progress = f"[{self.checked_considerations}/{self.total_considerations}]"
                    msg = f"{progress} {msg}"

            # Print to stderr (doesn't interfere with JSON output)
            print(msg, file=sys.stderr, flush=True)

        except Exception:
            # Fail-safe: Never raise exceptions
            pass

    def set_total_considerations(self, total: int) -> None:
        """Set total number of considerations for progress tracking.

        Args:
            total: Total consideration count
        """
        self.total_considerations = total

    def display_summary(self) -> None:
        """Display final summary (called after check completes)."""
        try:
            if self.verbosity == VerbosityMode.OFF:
                return

            # Only display if we have events
            if not self.events:
                return

            # Find completion event
            complete_event = None
            for event in reversed(self.events):
                if event.event_type == "complete":
                    complete_event = event
                    break

            if complete_event and self.verbosity == VerbosityMode.SUMMARY:
                # Summary mode: Just show the completion message
                self._display_event(complete_event)

        except Exception:
            # Fail-safe: Never raise exceptions
            pass

    def display_all_results(
        self,
        analysis: Any,
        considerations: list[dict],
        is_first_stop: bool = True,
    ) -> None:
        """Display all consideration results for visibility (first stop feature).

        Shows all considerations grouped by category with ✓/✗ indicators.

        Args:
            analysis: ConsiderationAnalysis with results
            considerations: List of consideration definitions
            is_first_stop: True if this is first stop (shows "will allow next stop" message)
        """
        try:
            # Header
            print("\n" + "=" * 70, file=sys.stderr, flush=True)
            print("⚙️  POWER-STEERING ANALYSIS RESULTS", file=sys.stderr, flush=True)
            print("=" * 70 + "\n", file=sys.stderr, flush=True)

            # Group considerations by category
            by_category: dict[str, list[tuple]] = {}
            for consideration in considerations:
                category = consideration.get("category", "Unknown")
                cid = consideration["id"]
                result = analysis.results.get(cid)

                if category not in by_category:
                    by_category[category] = []

                by_category[category].append((consideration, result))

            # Display by category
            total_passed = 0
            total_failed = 0

            for category, items in sorted(by_category.items()):
                print(f"📋 {category}", file=sys.stderr, flush=True)
                print("-" * 50, file=sys.stderr, flush=True)

                for consideration, result in items:
                    if result is None:
                        # Not checked (filtered by session type)
                        indicator = "⬜"
                    elif result.satisfied:
                        indicator = "✅"
                        total_passed += 1
                    else:
                        indicator = "❌"
                        total_failed += 1

                    question = consideration.get("question", consideration["id"])
                    severity = consideration.get("severity", "warning")
                    severity_tag = "[blocker]" if severity == "blocker" else ""

                    print(f"  {indicator} {question} {severity_tag}", file=sys.stderr, flush=True)

                print("", file=sys.stderr, flush=True)

            # Summary line
            print("=" * 70, file=sys.stderr, flush=True)
            if total_failed == 0:
                print(
                    f"✅ ALL CHECKS PASSED ({total_passed} passed, {total_failed} failed)",
                    file=sys.stderr,
                    flush=True,
                )
                if is_first_stop:
                    print(
                        "\n📌 This was your first stop. Next stop will proceed without blocking.",
                        file=sys.stderr,
                        flush=True,
                    )
            else:
                print(
                    f"❌ CHECKS FAILED ({total_passed} passed, {total_failed} failed)",
                    file=sys.stderr,
                    flush=True,
                )
                print(
                    "\n📌 Address the failed checks above before stopping.",
                    file=sys.stderr,
                    flush=True,
                )
            print("=" * 70 + "\n", file=sys.stderr, flush=True)

        except Exception as e:
            # Fail-safe: Never raise exceptions that would break the stop hook
            print(f"Warning: Could not display results: {e}", file=sys.stderr, flush=True)


# Module interface for easy import
__all__ = ["ProgressTracker", "VerbosityMode", "ProgressEvent"]
