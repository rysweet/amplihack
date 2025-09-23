"""Data models for the Agent Memory System."""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


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
    metadata: Dict[str, Any]

    # Timestamps
    created_at: datetime
    accessed_at: datetime

    # Optional fields
    tags: Optional["list[str]"] = None
    importance: Optional[int] = None  # 1-10 scale
    expires_at: Optional[datetime] = None
    parent_id: Optional[str] = None  # For hierarchical memories

    def to_dict(self) -> Dict[str, Any]:
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
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
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
    agent_ids: "list[str]"
    memory_count: int
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
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

    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    memory_type: Optional[MemoryType] = None
    tags: Optional["list[str]"] = None
    content_search: Optional[str] = None
    min_importance: Optional[int] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    include_expired: bool = False

    def to_sql_where(self) -> "tuple[str, list[Any]]":
        """Convert to SQL WHERE clause and parameters."""
        conditions = []
        params: "list[Any]" = []

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
