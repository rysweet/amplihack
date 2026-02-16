"""Orchestration completion and error models.

Models for tracking orchestration results and error details.

Philosophy:
- Simple data models with calculated properties
- Human-readable formatting methods
- Clear error tracking with recovery suggestions

Public API:
    OrchestrationReport: Final orchestration results
    ErrorDetails: Detailed error information
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class ErrorDetails:
    """Detailed information about an error.

    Args:
        issue_number: Issue where error occurred
        error_type: Type/category of error
        message: Error message
        recoverable: Whether error is recoverable
        traceback: Full traceback (optional)
        suggested_fix: Suggested fix for the error (optional)
    """

    issue_number: int
    error_type: str
    message: str
    recoverable: bool = False
    traceback: Optional[str] = None
    suggested_fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class OrchestrationReport:
    """Final orchestration report with results and metrics.

    Args:
        parent_issue: Parent issue number that was orchestrated
        total_sub_issues: Total number of sub-issues
        completed: Number of successfully completed issues
        failed: Number of failed issues
        duration_seconds: Total orchestration duration (optional)
        pr_links: List of created PR URLs (optional)
        failures: List of failure details (optional)
    """

    parent_issue: int
    total_sub_issues: int
    completed: int
    failed: int
    duration_seconds: Optional[float] = None
    pr_links: List[str] = field(default_factory=list)
    failures: List[Dict[str, Any]] = field(default_factory=list)

    def calculate_success_rate(self) -> float:
        """Calculate success rate as percentage.

        Returns:
            Success rate as percentage (0.0 to 100.0)
        """
        if self.total_sub_issues == 0:
            return 0.0
        return (self.completed / self.total_sub_issues) * 100.0

    def format_duration(self) -> str:
        """Format duration in human-readable form.

        Returns:
            Formatted duration string (e.g., "2h 30m 15s")
        """
        if self.duration_seconds is None:
            return "unknown"

        seconds = int(self.duration_seconds)
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def generate_summary(self) -> str:
        """Generate human-readable summary.

        Returns:
            Multi-line summary text
        """
        lines = [
            f"Orchestration Report for Issue #{self.parent_issue}",
            f"=" * 50,
            f"Total sub-issues: {self.total_sub_issues}",
            f"Completed: {self.completed}",
            f"Failed: {self.failed}",
            f"Success rate: {self.calculate_success_rate():.1f}%",
        ]

        if self.duration_seconds is not None:
            lines.append(f"Duration: {self.format_duration()}")

        if self.pr_links:
            lines.append(f"\nCreated {len(self.pr_links)} PRs:")
            for link in self.pr_links:
                lines.append(f"  - {link}")

        if self.failures:
            lines.append(f"\nFailures ({len(self.failures)}):")
            for failure in self.failures:
                issue_num = failure.get("issue_number", "unknown")
                error = failure.get("error", "unknown error")
                lines.append(f"  - Issue #{issue_num}: {error}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrchestrationReport":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with report fields

        Returns:
            OrchestrationReport instance
        """
        return cls(**data)


__all__ = ["OrchestrationReport", "ErrorDetails"]
