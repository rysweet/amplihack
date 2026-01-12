"""Data models for the Agent Memory System."""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryType(Enum):
    """Types of memory entries."""

    CONVERSATION = "conversation"
    DECISION = "decision"
    PATTERN = "pattern"
    CONTEXT = "context"
    LEARNING = "learning"
    ARTIFACT = "artifact"


@dataclass
class MemoryEntry:
    """A single memory entry in the system."""

    # Core identity
    id: str
    session_id: str
    agent_id: str
    memory_type: MemoryType

    # Content
    title: str
    content: str
    metadata: dict[str, Any]

    # Timestamps
    created_at: datetime
    accessed_at: datetime

    # Optional fields
    tags: list[str] | None = None
    importance: int | None = None  # 1-10 scale
    expires_at: datetime | None = None
    parent_id: str | None = None  # For hierarchical memories

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "memory_type": self.memory_type.value,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "accessed_at": self.accessed_at.isoformat(),
            "tags": self.tags,
            "importance": self.importance,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            agent_id=data["agent_id"],
            memory_type=MemoryType(data["memory_type"]),
            title=data["title"],
            content=data["content"],
            metadata=data["metadata"],
            created_at=datetime.fromisoformat(data["created_at"]),
            accessed_at=datetime.fromisoformat(data["accessed_at"]),
            tags=data.get("tags"),
            importance=data.get("importance"),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            parent_id=data.get("parent_id"),
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "MemoryEntry":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class SessionInfo:
    """Information about a memory session."""

    session_id: str
    created_at: datetime
    last_accessed: datetime
    agent_ids: list[str]
    memory_count: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "agent_ids": self.agent_ids,
            "memory_count": self.memory_count,
            "metadata": self.metadata,
        }


@dataclass
class MemoryQuery:
    """Query parameters for memory retrieval."""

    session_id: str | None = None
    agent_id: str | None = None
    memory_type: MemoryType | None = None
    tags: list[str] | None = None
    content_search: str | None = None
    min_importance: int | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int | None = None
    offset: int | None = None
    include_expired: bool = False

    def __post_init__(self):
        """Validate query parameters to prevent SQL injection and logic errors."""
        # Validate limit
        if self.limit is not None:
            if not isinstance(self.limit, int):
                raise ValueError(f"limit must be an integer, got {type(self.limit).__name__}")
            if self.limit < 0:
                raise ValueError(f"limit must be non-negative, got {self.limit}")
            if self.limit > 10000:
                raise ValueError(f"limit must be <= 10000, got {self.limit}")

        # Validate offset
        if self.offset is not None:
            if not isinstance(self.offset, int):
                raise ValueError(f"offset must be an integer, got {type(self.offset).__name__}")
            if self.offset < 0:
                raise ValueError(f"offset must be non-negative, got {self.offset}")

        # Validate min_importance
        if self.min_importance is not None:
            if not isinstance(self.min_importance, int):
                raise ValueError(
                    f"min_importance must be an integer, got {type(self.min_importance).__name__}"
                )
            if not 1 <= self.min_importance <= 10:
                raise ValueError(f"min_importance must be 1-10, got {self.min_importance}")

        # Validate time range
        if self.created_after and self.created_before:
            if self.created_after > self.created_before:
                raise ValueError("created_after must be before created_before")

        # Validate session_id format (alphanumeric + dash/underscore only)
        if self.session_id and not self.session_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"session_id contains invalid characters: {self.session_id}")

        # Validate agent_id format (alphanumeric + dash/underscore only)
        if self.agent_id and not self.agent_id.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"agent_id contains invalid characters: {self.agent_id}")

    def to_sql_where(self) -> tuple[str, list[Any]]:
        """Convert to SQL WHERE clause and parameters."""
        conditions = []
        params: list[Any] = []

        if self.session_id:
            conditions.append("session_id = ?")
            params.append(self.session_id)

        if self.agent_id:
            conditions.append("agent_id = ?")
            params.append(self.agent_id)

        if self.memory_type:
            conditions.append("memory_type = ?")
            params.append(self.memory_type.value)

        if self.min_importance:
            conditions.append("importance >= ?")
            params.append(self.min_importance)

        if self.created_after:
            conditions.append("created_at >= ?")
            params.append(self.created_after.isoformat())

        if self.created_before:
            conditions.append("created_at <= ?")
            params.append(self.created_before.isoformat())

        if not self.include_expired:
            conditions.append("(expires_at IS NULL OR expires_at > ?)")
            params.append(datetime.now().isoformat())

        if self.content_search:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            search_term = f"%{self.content_search}%"
            params.extend([search_term, search_term])

        if self.tags:
            # Simple tag search - can be optimized with FTS if needed
            tag_conditions = []
            for tag in self.tags:
                tag_conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
            conditions.append(f"({' OR '.join(tag_conditions)})")

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        return where_clause, params


__all__ = ["MemoryType", "MemoryEntry", "SessionInfo", "MemoryQuery"]
