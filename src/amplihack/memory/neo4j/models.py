"""Data models for Neo4j memory system.

Provides typed dataclasses for the five memory types with Neo4j mapping.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4


@dataclass
class MemoryBase:
    """Base class for all memory types.

    Attributes:
        id: Unique identifier (UUID)
        content: Memory content (text)
        agent_type: Agent type identifier (e.g., 'architect', 'builder')
        metadata: Additional metadata dictionary
        created_at: Creation timestamp (milliseconds since epoch)
        accessed_at: Last access timestamp (milliseconds since epoch)
        access_count: Number of times accessed
    """

    content: str
    agent_type: str
    id: str = field(default_factory=lambda: str(uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    accessed_at: int = field(default_factory=lambda: int(datetime.now().timestamp() * 1000))
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j storage.

        Returns:
            Dictionary with all fields suitable for Neo4j node properties
        """
        return {
            "id": self.id,
            "content": self.content,
            "agent_type": self.agent_type,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "accessed_at": self.accessed_at,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryBase":
        """Create instance from Neo4j data.

        Args:
            data: Dictionary from Neo4j query result

        Returns:
            MemoryBase instance
        """
        return cls(
            id=data.get("id"),
            content=data.get("content"),
            agent_type=data.get("agent_type"),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at"),
            accessed_at=data.get("accessed_at"),
            access_count=data.get("access_count", 0),
        )


@dataclass
class EpisodicMemory(MemoryBase):
    """Episodic memory: Records specific events/interactions.

    Used for conversation history, user interactions, task completion records.

    Example:
        memory = EpisodicMemory(
            content="User requested authentication feature implementation",
            agent_type="architect",
            metadata={"session_id": "abc123", "task": "auth-feature"}
        )
    """

    memory_type: str = field(default="episodic", init=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with memory_type."""
        data = super().to_dict()
        data["memory_type"] = self.memory_type
        return data


@dataclass
class ShortTermMemory(MemoryBase):
    """Short-term memory: Temporary working memory for current session.

    Used for variables in scope, active context, recent decisions.

    Example:
        memory = ShortTermMemory(
            content="Current module uses async/await pattern",
            agent_type="builder",
            metadata={"file": "auth.py", "pattern": "async"}
        )
    """

    memory_type: str = field(default="short_term", init=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with memory_type."""
        data = super().to_dict()
        data["memory_type"] = self.memory_type
        return data


@dataclass
class ProceduralMemory(MemoryBase):
    """Procedural memory: How to perform tasks.

    Used for learned procedures, workflows, best practices.

    Example:
        memory = ProceduralMemory(
            content="To add new API endpoint: 1) Define route 2) Add handler 3) Write tests",
            agent_type="builder",
            metadata={"category": "api-development"}
        )
    """

    memory_type: str = field(default="procedural", init=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with memory_type."""
        data = super().to_dict()
        data["memory_type"] = self.memory_type
        return data


@dataclass
class DeclarativeMemory(MemoryBase):
    """Declarative memory: Facts and knowledge.

    Used for project facts, requirements, constraints, domain knowledge.

    Example:
        memory = DeclarativeMemory(
            content="System uses PostgreSQL 15 with UUID primary keys",
            agent_type="architect",
            metadata={"category": "database", "source": "architecture-doc"}
        )
    """

    memory_type: str = field(default="declarative", init=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with memory_type."""
        data = super().to_dict()
        data["memory_type"] = self.memory_type
        return data


@dataclass
class ProspectiveMemory(MemoryBase):
    """Prospective memory: Intentions and future actions.

    Used for TODOs, reminders, scheduled tasks, future intentions.

    Example:
        memory = ProspectiveMemory(
            content="Add rate limiting to API after authentication is complete",
            agent_type="architect",
            metadata={"status": "pending", "depends_on": "auth-feature"}
        )
    """

    memory_type: str = field(default="prospective", init=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with memory_type."""
        data = super().to_dict()
        data["memory_type"] = self.memory_type
        return data


# Type mapping for deserialization
MEMORY_TYPE_MAP = {
    "episodic": EpisodicMemory,
    "short_term": ShortTermMemory,
    "procedural": ProceduralMemory,
    "declarative": DeclarativeMemory,
    "prospective": ProspectiveMemory,
}


def memory_from_dict(data: Dict[str, Any]) -> MemoryBase:
    """Create appropriate memory instance from Neo4j data.

    Args:
        data: Dictionary from Neo4j query result

    Returns:
        Appropriate memory subclass instance

    Raises:
        ValueError: If memory_type is unknown
    """
    memory_type = data.get("memory_type")
    memory_class = MEMORY_TYPE_MAP.get(memory_type)

    if memory_class is None:
        raise ValueError(f"Unknown memory_type: {memory_type}")

    return memory_class.from_dict(data)
