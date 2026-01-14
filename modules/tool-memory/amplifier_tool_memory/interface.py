"""
Agent Memory Interface - Clean API for agent memory operations.

Follows the API designer agent specification for minimal, clear contracts.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .backend import MemoryBackend


class MemoryType(Enum):
    """Types of agent memories."""

    CONVERSATION = "conversation"  # Chat/dialogue fragments
    DECISION = "decision"  # Design/implementation decisions
    PATTERN = "pattern"  # Learned patterns and preferences
    CONTEXT = "context"  # Session/project context
    LEARNING = "learning"  # Insights and lessons learned
    ARTIFACT = "artifact"  # Generated content references


@dataclass
class MemoryEntry:
    """A single memory entry with metadata."""

    key: str
    value: str
    memory_type: MemoryType = MemoryType.CONTEXT
    importance: int = 5  # 1-10 scale
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    accessed_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "memory_type": self.memory_type.value,
            "importance": self.importance,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "accessed_count": self.accessed_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        return cls(
            key=data["memory_key"],
            value=data["memory_value"],
            memory_type=MemoryType(data.get("memory_type", "context")),
            importance=data.get("importance", 5),
            tags=data.get("tags", []) if isinstance(data.get("tags"), list) else [],
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else None,
            accessed_count=data.get("accessed_count", 0),
        )


class AgentMemory:
    """Simple agent memory interface following bricks & studs philosophy.

    Provides persistent memory storage for agents with session management,
    optional activation, and performance guarantees.
    """

    def __init__(
        self,
        agent_name: str,
        session_id: str | None = None,
        db_path: Path | None = None,
        enabled: bool = True,
    ) -> None:
        """Initialize agent memory with session management.

        Args:
            agent_name: Name of the agent using memory
            session_id: Optional session ID (auto-generated if None)
            db_path: Optional database path (default: .amplifier/runtime/memory.db)
            enabled: Whether memory is enabled (default: True)
        """
        self.agent_name = agent_name
        self.session_id = session_id or self._generate_session_id()
        self.enabled = enabled
        self.backend: MemoryBackend | None = None

        if db_path is None:
            db_path = Path.home() / ".amplifier" / "runtime" / "memory.db"

        if self.enabled:
            try:
                self.backend = MemoryBackend(db_path)
                self.backend.ensure_session(self.session_id, self.agent_name)
            except Exception as e:
                print(f"Warning: Memory backend failed to initialize: {e}")
                self.backend = None

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{self.agent_name}_{timestamp}_{unique_id}"

    def store(
        self,
        key: str,
        value: str,
        memory_type: MemoryType = MemoryType.CONTEXT,
        importance: int = 5,
        tags: list[str] | None = None,
    ) -> bool:
        """Store memory with key-value pair.

        Args:
            key: Memory key (cannot be empty)
            value: Memory value
            memory_type: Type of memory
            importance: Importance score (1-10)
            tags: Optional list of tags

        Returns:
            True if stored successfully, False otherwise
        """
        if not key:
            raise ValueError("Key cannot be empty")
        if value is None:
            raise ValueError("Value cannot be None")

        if not self.enabled or not self.backend:
            return True  # Graceful degradation

        return self.backend.store_memory(
            session_id=self.session_id,
            key=key,
            value=value,
            memory_type=memory_type.value,
            importance=importance,
            tags=tags,
        )

    def retrieve(self, key: str) -> MemoryEntry | None:
        """Retrieve memory by key.

        Args:
            key: Memory key to retrieve

        Returns:
            MemoryEntry if found, None otherwise
        """
        if not self.enabled or not self.backend:
            return None

        data = self.backend.retrieve_memory(self.session_id, key)
        if data:
            return MemoryEntry.from_dict(data)
        return None

    def search(
        self,
        memory_type: MemoryType | None = None,
        min_importance: int | None = None,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """Search memories with filters.

        Args:
            memory_type: Filter by memory type
            min_importance: Minimum importance score
            tags: Filter by tags (any match)
            limit: Maximum results to return

        Returns:
            List of matching MemoryEntry objects
        """
        if not self.enabled or not self.backend:
            return []

        results = self.backend.search_memories(
            session_id=self.session_id,
            memory_type=memory_type.value if memory_type else None,
            min_importance=min_importance,
            tags=tags,
            limit=limit,
        )
        return [MemoryEntry.from_dict(r) for r in results]

    def delete(self, key: str) -> bool:
        """Delete memory by key.

        Args:
            key: Memory key to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self.enabled or not self.backend:
            return True

        return self.backend.delete_memory(self.session_id, key)

    def list_all(self, limit: int = 100) -> list[MemoryEntry]:
        """List all memories for this session.

        Args:
            limit: Maximum results to return

        Returns:
            List of all MemoryEntry objects
        """
        return self.search(limit=limit)

    def close(self) -> None:
        """Close memory backend."""
        if self.backend:
            self.backend.close()
