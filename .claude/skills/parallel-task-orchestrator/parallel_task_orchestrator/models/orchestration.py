"""Orchestration configuration model.

Configuration for parallel task orchestration settings.

Philosophy:
- Validation at construction time
- Sensible defaults for common cases
- Immutable configuration

Public API:
    OrchestrationConfig: Main configuration model
    SubIssue: Sub-issue metadata
"""

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class SubIssue:
    """Metadata for a sub-issue.

    Args:
        number: GitHub issue number
        title: Issue title (optional)
        labels: Issue labels (optional) - stored as tuple for hashability
        assignee: Assigned user (optional)

    Note: frozen=True makes instances hashable for deduplication
    """

    number: int
    title: Optional[str] = None
    labels: tuple = field(default_factory=tuple)
    assignee: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass(frozen=True)
class OrchestrationConfig:
    """Configuration for parallel task orchestration.

    Args:
        parent_issue: Parent issue number
        sub_issues: List of sub-issue numbers
        parallel_degree: Max parallel agents (default: 3, range: 1-100)
        timeout_minutes: Timeout per issue in minutes (default: 120, min: 1)
        recovery_strategy: How to handle failures (default: continue_on_failure)
        worktree_base: Base directory for worktrees (default: ./worktrees)
        status_poll_interval: Status check interval in seconds (default: 30)

    Raises:
        ValueError: If validation fails
    """

    parent_issue: int
    sub_issues: List[int]
    parallel_degree: int = 3
    timeout_minutes: int = 120
    recovery_strategy: str = "continue_on_failure"
    worktree_base: str = "./worktrees"
    status_poll_interval: int = 30

    # Valid recovery strategies
    VALID_STRATEGIES = {"fail_fast", "continue_on_failure", "retry_failed"}

    @staticmethod
    def _deduplicate_issues(issues: List[int], exclude: Optional[int] = None) -> List[int]:
        """Remove duplicates from issue list while preserving order.

        Args:
            issues: List of issue numbers
            exclude: Optional issue number to exclude

        Returns:
            Deduplicated list
        """
        seen = set()
        unique = []
        for issue in issues:
            if issue not in seen and issue != exclude:
                seen.add(issue)
                unique.append(issue)
        return unique

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Validate sub_issues not empty
        if not self.sub_issues:
            raise ValueError("sub_issues cannot be empty")

        # Deduplicate sub-issues (use object.__setattr__ for frozen dataclass)
        if len(self.sub_issues) != len(set(self.sub_issues)):
            unique_issues = self._deduplicate_issues(self.sub_issues)
            object.__setattr__(self, "sub_issues", unique_issues)

        # Validate parallel_degree bounds
        if not (1 <= self.parallel_degree <= 100):
            raise ValueError(
                f"parallel_degree must be between 1 and 100, got {self.parallel_degree}"
            )

        # Validate timeout
        if self.timeout_minutes < 1:
            raise ValueError(
                f"timeout_minutes must be at least 1, got {self.timeout_minutes}"
            )

        # Validate recovery strategy
        if self.recovery_strategy not in self.VALID_STRATEGIES:
            raise ValueError(
                f"Invalid recovery_strategy '{self.recovery_strategy}'. "
                f"Must be one of: {self.VALID_STRATEGIES}"
            )

        # Validate status_poll_interval
        if self.status_poll_interval < 10:
            raise ValueError(
                f"status_poll_interval must be at least 10 seconds, "
                f"got {self.status_poll_interval}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        data = asdict(self)
        # Remove class variable from dict
        data.pop("VALID_STRATEGIES", None)
        return data

    def to_json(self) -> str:
        """Serialize to JSON string.

        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_issue_body(cls, parent_issue: int, issue_body: str, **kwargs) -> "OrchestrationConfig":
        """Create config from GitHub issue body by parsing sub-issue references.

        Parses various formats of issue references:
        - #123
        - GH-123
        - issue #123
        - https://github.com/owner/repo/issues/123

        Args:
            parent_issue: Parent issue number
            issue_body: GitHub issue body text
            **kwargs: Additional config parameters

        Returns:
            OrchestrationConfig instance with parsed sub-issues

        Example:
            >>> config = OrchestrationConfig.from_issue_body(
            ...     parent_issue=1783,
            ...     issue_body="Sub-tasks: #101, #102, GH-103"
            ... )
            >>> config.sub_issues
            [101, 102, 103]
        """
        # Parse issue references from body
        # Patterns: #123, GH-123, issue #123, https://github.com/.../issues/123
        patterns = [
            r'#(\d+)',  # #123
            r'GH-(\d+)',  # GH-123
            r'issue[s]?\s+#?(\d+)',  # issue #123 or issues 123
            r'github\.com/[\w-]+/[\w-]+/issues/(\d+)',  # Full URL
        ]

        sub_issues = []
        for pattern in patterns:
            matches = re.findall(pattern, issue_body, re.IGNORECASE)
            sub_issues.extend(int(m) for m in matches)

        # Remove duplicates while preserving order, excluding parent issue
        unique_issues = cls._deduplicate_issues(sub_issues, exclude=parent_issue)

        return cls(
            parent_issue=parent_issue,
            sub_issues=unique_issues,
            **kwargs
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrchestrationConfig":
        """Deserialize from dictionary.

        Args:
            data: Dictionary with config fields

        Returns:
            OrchestrationConfig instance
        """
        # Filter out any extra keys
        valid_fields = {
            "parent_issue",
            "sub_issues",
            "parallel_degree",
            "timeout_minutes",
            "recovery_strategy",
            "worktree_base",
            "status_poll_interval",
        }
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)


__all__ = ["OrchestrationConfig", "SubIssue"]
