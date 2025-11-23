#!/usr/bin/env python3
"""
Power-Steering Progress Visibility Module

Provides real-time progress updates during power-steering analysis with
pirate mode support and verbosity control.

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
from typing import Dict, List, Optional


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
    details: Optional[Dict] = None


class ProgressTracker:
    """Track and display power-steering analysis progress.

    Features:
    - Three verbosity modes: OFF, SUMMARY, DETAILED
    - Pirate-style message transformation
    - Preference reading from USER_PREFERENCES.md
    - Fail-safe design (exceptions never break checker)

    Design:
    - Callback-based progress (checker calls tracker.emit)
    - Synchronous operation (no async complexity)
    - Simple stderr output (no fancy libraries)
    """

    def __init__(
        self,
        verbosity: Optional[str] = None,
        project_root: Optional[Path] = None,
        pirate_mode: Optional[bool] = None,
    ):
        """Initialize progress tracker.

        Args:
            verbosity: Verbosity level (off/summary/detailed) or None to auto-detect
            project_root: Project root directory (auto-detected if None)
            pirate_mode: Enable pirate mode or None to auto-detect from preferences
        """
        self.project_root = project_root or self._detect_project_root()
        self.events: List[ProgressEvent] = []

        # Auto-detect settings from preferences if not provided
        if verbosity is None or pirate_mode is None:
            prefs = self._read_preferences()
            if verbosity is None:
                verbosity = prefs.get("verbosity", "summary")
            if pirate_mode is None:
                pirate_mode = prefs.get("communication_style") == "pirate"

        # Set verbosity mode
        try:
            self.verbosity = VerbosityMode(verbosity)
        except ValueError:
            self.verbosity = VerbosityMode.SUMMARY

        self.pirate_mode = pirate_mode

        # Counters for summary
        self.total_considerations = 0
        self.checked_considerations = 0
        self.categories_processed: List[str] = []

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

    def _read_preferences(self) -> Dict:
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
                        # Look for "pirate" in the line
                        if "pirate" in line.lower():
                            prefs["communication_style"] = "pirate"
                        break

            return prefs

        except Exception:
            # Fail-safe: Return empty dict on any error
            return {}

    def emit(self, event_type: str, message: str, details: Optional[Dict] = None) -> None:
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

            # Apply pirate transformation if enabled
            if self.pirate_mode:
                msg = self._piratify(msg)

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

    def _piratify(self, message: str) -> str:
        """Transform message to pirate speak.

        Args:
            message: Original message

        Returns:
            Pirate-ified message
        """
        # Simple pirate transformations
        replacements = {
            "Analyzing": "Analyzin'",
            "Checking": "Checkin'",
            "Running": "Runnin'",
            "Starting": "Startin'",
            "Completing": "Completin'",
            "power-steering": "power-steerin'",
            "considerations": "considerations (arr!)",
            "Complete": "Complete, matey!",
            "Done": "Done, ye scallywag!",
            "Testing": "Testin'",
            "Verifying": "Verifyin'",
        }

        result = message
        for old, new in replacements.items():
            result = result.replace(old, new)

        return result

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


# Module interface for easy import
__all__ = ["ProgressTracker", "VerbosityMode", "ProgressEvent"]
