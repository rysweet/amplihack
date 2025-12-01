"""Data models for context management skill.

This module defines the data structures used throughout the context management
system for tracking token usage and storing context snapshots.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class UsageStats:
    """Token usage statistics.

    Attributes:
        current_tokens: Current token count in conversation
        max_tokens: Maximum context window size
        percentage: Usage percentage (0-100)
        threshold_status: One of 'ok', 'consider', 'recommended', 'urgent'
        recommendation: Human-readable recommendation message
    """

    current_tokens: int
    max_tokens: int
    percentage: float
    threshold_status: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "current_tokens": self.current_tokens,
            "max_tokens": self.max_tokens,
            "percentage": self.percentage,
            "threshold_status": self.threshold_status,
            "recommendation": self.recommendation,
        }


@dataclass
class ContextSnapshot:
    """Context snapshot metadata and content.

    Attributes:
        snapshot_id: Unique identifier (format: YYYYMMDD_HHMMSS)
        name: Optional human-readable snapshot name
        timestamp: When snapshot was created
        original_requirements: User's initial request/requirements
        key_decisions: List of decision dicts with decision/rationale/alternatives
        implementation_state: Current progress summary
        open_items: List of pending questions/blockers
        tools_used: List of tool names invoked
        token_count: Estimated tokens in snapshot
        file_path: Path to snapshot JSON file
    """

    snapshot_id: str
    name: str | None
    timestamp: datetime
    original_requirements: str
    key_decisions: list[dict[str, str]] = field(default_factory=list)
    implementation_state: str = ""
    open_items: list[str] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    token_count: int = 0
    file_path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        return {
            "snapshot_id": self.snapshot_id,
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "original_requirements": self.original_requirements,
            "key_decisions": self.key_decisions,
            "implementation_state": self.implementation_state,
            "open_items": self.open_items,
            "tools_used": self.tools_used,
            "token_count": self.token_count,
            "file_path": str(self.file_path) if self.file_path else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContextSnapshot":
        """Create ContextSnapshot from dictionary.

        Args:
            data: Dictionary with snapshot data

        Returns:
            ContextSnapshot instance
        """
        return cls(
            snapshot_id=data["snapshot_id"],
            name=data.get("name"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            original_requirements=data.get("original_requirements", ""),
            key_decisions=data.get("key_decisions", []),
            implementation_state=data.get("implementation_state", ""),
            open_items=data.get("open_items", []),
            tools_used=data.get("tools_used", []),
            token_count=data.get("token_count", 0),
            file_path=Path(data["file_path"]) if data.get("file_path") else None,
        )
